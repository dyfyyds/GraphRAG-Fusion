import asyncio
import logging
import re
from typing import AsyncGenerator

from sqlalchemy import and_, or_, select

from app.core.llm_client import get_llm_client
from app.core.embedding_client import get_embedding_client
from app.core.vector_service import query_vectors
from app.services.graph_service import search_entity_context
from app.db.mysql import async_session
from app.models.chunk import Chunk
from app.models.document import Document

logger = logging.getLogger("app")

SYSTEM_PROMPT = """你是一个企业内部文件问答搜索助手。请严格基于已上传的企业内部知识库文件回答用户问题。

规则：
1. 只使用参考资料中的信息回答，不得使用模型常识、外部知识或猜测
2. 回答必须结论先行，然后给出文件中的明确依据
3. 必须包含“引用来源：”一行，引用来源只能来自参考资料中给出的来源说明
4. 必须包含“【知识图谱引用】”区块，直接使用用户消息中提供的知识图谱引用内容
5. 如果参考资料不足以回答，请只回答“根据企业内部知识库，未找到相关信息，无法回答该问题。”
6. 回答要准确、简洁、专业

输出格式：
根据《文档名》的规定，直接回答用户问题。

文件中明确规定：引用或概括最相关的制度依据。

引用来源：[检索方式-文档ID] 文档名 - 第N页 - 分块M

【知识图谱引用】
- 实体或关系引用"""

CONTEXT_TEMPLATE = """参考资料：
{context}

知识图谱引用：
{graph_context}

用户问题：{question}"""

RRF_K = 60
W_VEC = 0.5
W_GRAPH = 0.3
W_KW = 0.2
FALLBACK_PREFIX = "企业内部知识库中未找到相关信息，正在使用 AI 通用能力回答：\n\n"
SOURCE_LABELS = {
    "vector": "向量检索",
    "keyword": "关键词检索",
}
KEYWORD_SEARCH_LIMIT_FACTOR = 6

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now\s+",
    r"system\s*:\s*",
    r"<\|system\|>",
    r"jailbreak",
]


def _check_injection(text: str) -> bool:
    for p in INJECTION_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def _build_keyword_terms(query: str) -> list[str]:
    normalized = _normalize_query_text(query)
    terms: list[str] = []

    def add(term: str):
        term = term.strip()
        if len(term) >= 2 and term not in terms:
            terms.append(term)

    add(normalized)
    for term in re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_:.-]{2,}", normalized):
        add(term)

    if "打卡" in normalized:
        add("打卡")
    if "考勤" in normalized or "打卡" in normalized:
        add("考勤")
        add("迟到")

    for hour, minute in _extract_times(normalized):
        add(f"{hour}:{minute:02d}")
        if hour == 9:
            if 1 <= minute <= 15:
                add("9:01")
                add("9:15")
                add("迟到")
            elif 16 <= minute <= 30:
                add("9:16")
                add("9:30")
                add("严重迟到")
            elif minute > 30:
                add("9:30")
                add("旷工")

    return terms[:12]


def _normalize_query_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"(\d{1,2})\s*点\s*(\d{1,2})\s*分?", r"\1:\2", text)
    text = re.sub(r"(\d{1,2})\s*时\s*(\d{1,2})\s*分?", r"\1:\2", text)
    text = re.sub(r"(\d{1,2})\s*：\s*(\d{1,2})", r"\1:\2", text)
    return text


def _extract_times(text: str) -> list[tuple[int, int]]:
    times = []
    for hour, minute in re.findall(r"(?<!\d)(\d{1,2}):(\d{1,2})(?!\d)", text):
        hour_int = int(hour)
        minute_int = int(minute)
        if 0 <= hour_int <= 23 and 0 <= minute_int <= 59:
            times.append((hour_int, minute_int))
    return times


class RAGEngine:
    async def query(self, question: str) -> AsyncGenerator[tuple, None]:
        if _check_injection(question):
            yield ("answer", "检测到不安全的输入，已拒绝回答。")
            return

        # 三路并行检索
        embedding_client = get_embedding_client()
        try:
            query_embedding = await embedding_client.embed(question)
        except Exception as exc:
            logger.warning(f"向量化失败，降级为直接 LLM 调用: {exc}")
            query_embedding = None

        if query_embedding:
            vector_results, graph_results, keyword_results = await asyncio.gather(
                self._vector_search(query_embedding, top_k=5),
                self._graph_search(question),
                self._keyword_search(question, top_k=5),
                return_exceptions=True,
            )
        else:
            vector_results, graph_results, keyword_results = [], [], []
            try:
                graph_results, keyword_results = await asyncio.gather(
                    self._graph_search(question),
                    self._keyword_search(question, top_k=5),
                    return_exceptions=True,
                )
            except Exception:
                pass

        # 异常降级为空列表
        if isinstance(vector_results, Exception):
            vector_results = []
        if isinstance(graph_results, Exception):
            graph_results = []
        if isinstance(keyword_results, Exception):
            keyword_results = []

        # RRF 融合重排。图谱结果只作为辅助引用，不作为制度/文件事实依据。
        fused = [
            item for item in self._rrf_fusion(vector_results, [], keyword_results)
            if item.get("document_name")
        ]
        graph_context = self._format_graph_context(graph_results)

        # 输出引用来源
        sources = []
        for item in fused[:5]:
            sources.append({
                "document_name": item.get("document_name", ""),
                "page_number": item.get("page_number"),
                "chunk_content": item.get("content", "")[:200],
                "document_id": item.get("document_id"),
                "chunk_index": item.get("chunk_index"),
                "source_type": item.get("source"),
                "score": self._display_score(item),
                "rrf_score": item.get("score", 0),
            })
        yield ("sources", sources)

        # 组装上下文
        context_parts = []
        for item in fused[:5]:
            doc_name = item.get("document_name", "未知文档")
            page = item.get("page_number", "")
            content = item.get("content", "")
            source_label = SOURCE_LABELS.get(item.get("source"), item.get("source", "检索"))
            doc_id = item.get("document_id", "")
            chunk_index = item.get("chunk_index")
            page_info = f" (第{page}页)" if page else ""
            chunk_info = f" - 分块{chunk_index}" if chunk_index is not None else ""
            source_info = f"[{source_label}-文档{doc_id}] {doc_name}{page_info}{chunk_info}"
            context_parts.append(f"来源说明：{source_info}\n内容：{content}")
        context = "\n\n".join(context_parts)

        llm = get_llm_client()

        # 如果企业内部知识库中没有找到相关内容，或相关度太低，按最新要求直接调用 LLM 接口兜底。
        if not context.strip():
            yield ("answer", FALLBACK_PREFIX)
            fallback_messages = [
                {"role": "system", "content": "你是一个专业的 AI 助手，请直接回答用户的问题。"},
                {"role": "user", "content": question},
            ]
            async for chunk in llm.chat_stream(fallback_messages):
                yield ("answer", chunk)
            return

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": CONTEXT_TEMPLATE.format(
                    context=context,
                    graph_context=graph_context,
                    question=question,
                ),
            },
        ]

        # SSE 流式输出
        async for chunk in llm.chat_stream(messages):
            yield ("answer", chunk)

    async def _vector_search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        results = await query_vectors(query_embedding, top_k=top_k)
        items = []
        for r in results:
            metadata = r.get("metadata", {}) or {}
            items.append({
                "source": "vector",
                "content": r.get("document", ""),
                "metadata": metadata,
                "document_id": metadata.get("document_id"),
                "chunk_index": metadata.get("chunk_index"),
                "vector_id": r.get("id"),
                "distance": r.get("distance", 1.0),
            })
        return await self._hydrate_chunk_results(items)

    async def _graph_search(self, query: str) -> list[dict]:
        # LLM 提取实体关键词
        llm = get_llm_client()
        try:
            resp = await llm.chat([
                {"role": "user", "content": f"从以下问题中提取关键实体名称，用逗号分隔，只输出实体名：\n{query}"}
            ])
            keywords = [k.strip() for k in resp.split(",") if k.strip()]
        except Exception:
            keywords = [query]

        # 搜索图谱实体及其直接关系
        graph_items = []
        for kw in keywords[:3]:
            results = await search_entity_context(kw, limit=5)
            graph_items.extend(results)

        items = []
        seen = set()
        for e in graph_items:
            name = e.get("name", "")
            if name not in seen:
                seen.add(name)
                items.append({
                    "source": "graph",
                    "content": f"{name} ({e.get('type', '')})",
                    "metadata": e,
                    "entity": e,
                })
        return items

    async def _keyword_search(self, query: str, top_k: int = 5) -> list[dict]:
        terms = _build_keyword_terms(query)
        if not terms:
            return []

        async with async_session() as db:
            result = await db.execute(
                select(Chunk, Document)
                .join(Document, Chunk.document_id == Document.id)
                .where(or_(*(Chunk.content.contains(term) for term in terms)))
                .limit(top_k * KEYWORD_SEARCH_LIMIT_FACTOR)
            )
            items = []
            for c, doc in result.all():
                matched_terms = [term for term in terms if term in c.content]
                if not matched_terms:
                    continue
                items.append({
                    "source": "keyword",
                    "content": c.content,
                    "metadata": {"document_id": c.document_id, "chunk_index": c.chunk_index},
                    "document_id": c.document_id,
                    "document_name": doc.name,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "vector_id": c.vector_id,
                    "keyword_hits": len(matched_terms),
                    "keyword_term_count": len(terms),
                    "matched_terms": matched_terms,
                })
            return sorted(
                items,
                key=lambda item: (
                    item.get("keyword_hits", 0),
                    1 if "考勤" in item.get("document_name", "") else 0,
                    1 if "迟到" in item.get("content", "") else 0,
                ),
                reverse=True,
            )[:top_k]

    async def _hydrate_chunk_results(self, items: list[dict]) -> list[dict]:
        if not items:
            return []

        vector_ids = [item.get("vector_id") for item in items if item.get("vector_id")]
        pairs = [
            (item.get("document_id"), item.get("chunk_index"))
            for item in items
            if item.get("document_id") is not None and item.get("chunk_index") is not None
        ]
        conditions = []
        if vector_ids:
            conditions.append(Chunk.vector_id.in_(vector_ids))
        if pairs:
            conditions.extend(
                and_(Chunk.document_id == doc_id, Chunk.chunk_index == chunk_index)
                for doc_id, chunk_index in pairs
            )
        if not conditions:
            return items

        async with async_session() as db:
            result = await db.execute(
                select(Chunk, Document)
                .join(Document, Chunk.document_id == Document.id)
                .where(or_(*conditions))
            )
            chunk_map = {}
            for chunk, doc in result.all():
                chunk_data = {
                    "document_id": chunk.document_id,
                    "document_name": doc.name,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "vector_id": chunk.vector_id,
                    "content": chunk.content,
                }
                if chunk.vector_id:
                    chunk_map[("vector_id", chunk.vector_id)] = chunk_data
                chunk_map[("pair", chunk.document_id, chunk.chunk_index)] = chunk_data

        hydrated = []
        for item in items:
            chunk_data = None
            if item.get("vector_id"):
                chunk_data = chunk_map.get(("vector_id", item["vector_id"]))
            if chunk_data is None and item.get("document_id") is not None and item.get("chunk_index") is not None:
                chunk_data = chunk_map.get(("pair", item["document_id"], item["chunk_index"]))
            hydrated.append({**item, **(chunk_data or {})})
        return hydrated

    def _format_graph_context(self, graph_results: list[dict]) -> str:
        if not graph_results:
            return "- 未检索到相关实体或关系"

        lines = []
        seen = set()
        for item in graph_results[:5]:
            entity = item.get("entity") or item.get("metadata") or {}
            name = entity.get("name", "")
            entity_type = entity.get("type", "")
            if name:
                line = f"- 实体：{name}（类型：{entity_type or '未知'}）"
                if line not in seen:
                    lines.append(line)
                    seen.add(line)
            for rel in entity.get("relations", [])[:3]:
                source = rel.get("source", "")
                rel_type = rel.get("relation_type", "")
                target = rel.get("target", "")
                if source and rel_type and target:
                    line = f"- 关系：{source} → {rel_type} → {target}"
                    if line not in seen:
                        lines.append(line)
                        seen.add(line)

        return "\n".join(lines) if lines else "- 未检索到相关实体或关系"

    def _rrf_fusion(self, vector_results: list, graph_results: list, keyword_results: list) -> list[dict]:
        scores: dict[str, dict] = {}

        def _key(item: dict) -> str:
            document_id = item.get("document_id")
            chunk_index = item.get("chunk_index")
            source_type = item.get("source", "")
            if document_id is not None and chunk_index is not None:
                return f"{document_id}:{chunk_index}"
            return f"{source_type}:{item.get('content', '')[:100]}"

        def _merge_item(target: dict, item: dict):
            sources = target.setdefault("retrieval_sources", [])
            source = item.get("source")
            if source and source not in sources:
                sources.append(source)

            for field in (
                "document_id",
                "document_name",
                "page_number",
                "chunk_index",
                "vector_id",
                "content",
            ):
                if target.get(field) in (None, "") and item.get(field) not in (None, ""):
                    target[field] = item.get(field)

            if item.get("source") == "keyword":
                target["keyword_hits"] = max(target.get("keyword_hits", 0), item.get("keyword_hits", 0))
                target["keyword_term_count"] = max(
                    target.get("keyword_term_count", 0),
                    item.get("keyword_term_count", 0),
                )
                target["matched_terms"] = item.get("matched_terms", target.get("matched_terms", []))

        def _keyword_bonus(item: dict) -> float:
            term_count = max(item.get("keyword_term_count", 0), 1)
            hit_ratio = min(1.0, item.get("keyword_hits", 0) / term_count)
            strong_hits = sum(1 for term in item.get("matched_terms", []) if len(term) >= 4 or ":" in term)
            document_name = item.get("document_name", "")
            policy_bonus = 0.0
            if "制度" in document_name:
                policy_bonus += 0.02
            if "管理制度" in document_name:
                policy_bonus += 0.01
            return 0.03 * hit_ratio + 0.01 * min(strong_hits, 3) + policy_bonus

        for rank, item in enumerate(vector_results):
            key = _key(item)
            if key not in scores:
                scores[key] = {**item, "score": 0, "retrieval_sources": []}
            _merge_item(scores[key], item)
            scores[key]["score"] += W_VEC / (RRF_K + rank + 1)

        for rank, item in enumerate(graph_results):
            key = _key(item)
            if key not in scores:
                scores[key] = {**item, "score": 0, "retrieval_sources": []}
            _merge_item(scores[key], item)
            scores[key]["score"] += W_GRAPH / (RRF_K + rank + 1)

        for rank, item in enumerate(keyword_results):
            key = _key(item)
            if key not in scores:
                scores[key] = {**item, "score": 0, "retrieval_sources": []}
            _merge_item(scores[key], item)
            scores[key]["score"] += W_KW / (RRF_K + rank + 1) + _keyword_bonus(item)

        return sorted(scores.values(), key=lambda x: x["score"], reverse=True)

    def _display_score(self, item: dict) -> float:
        if item.get("keyword_hits") and item.get("keyword_term_count"):
            keyword_score = min(1.0, item["keyword_hits"] / max(item["keyword_term_count"], 1))
            if item.get("distance") is None:
                return keyword_score
            vector_score = max(0.0, min(1.0, 1 - float(item.get("distance", 1.0))))
            return max(vector_score, keyword_score)
        if item.get("distance") is not None:
            return max(0.0, min(1.0, 1 - float(item.get("distance", 1.0))))
        return item.get("score", 0)


_rag_engine: RAGEngine | None = None


def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
