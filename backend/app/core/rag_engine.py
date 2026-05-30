import asyncio
import json
import logging
import re
from typing import AsyncGenerator

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_client import get_llm_client
from app.core.embedding_client import get_embedding_client
from app.core.vector_service import query_vectors
from app.services.graph_service import search_entities
from app.db.mysql import async_session
from app.models.chunk import Chunk

logger = logging.getLogger("app")

SYSTEM_PROMPT = """你是一个企业知识库问答助手。请严格基于参考资料回答用户问题。

规则：
1. 只使用参考资料中的信息回答，不要编造
2. 在回答中标注引用来源，格式：[来源: 文档名, 页码]
3. 如果参考资料中没有相关信息，请明确说明"根据现有知识库，未找到相关信息"
4. 回答要准确、简洁、专业"""

CONTEXT_TEMPLATE = """参考资料：
{context}

用户问题：{question}"""

RRF_K = 60
W_VEC = 0.5
W_GRAPH = 0.3
W_KW = 0.2

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

        # RRF 融合重排
        fused = self._rrf_fusion(vector_results, graph_results, keyword_results)

        # 输出引用来源
        sources = []
        for item in fused[:5]:
            sources.append({
                "document_name": item.get("document_name", ""),
                "page_number": item.get("page_number"),
                "chunk_content": item.get("content", "")[:200],
                "score": item.get("score", 0),
            })
        yield ("sources", sources)

        # 组装上下文
        context_parts = []
        for item in fused[:5]:
            doc_name = item.get("document_name", "未知文档")
            page = item.get("page_number", "")
            content = item.get("content", "")
            page_info = f" (第{page}页)" if page else ""
            context_parts.append(f"[{doc_name}{page_info}]: {content}")
        context = "\n\n".join(context_parts)

        llm = get_llm_client()

        # 如果知识库中没有找到相关内容，或相关度太低，降级为直接调用 LLM
        top_score = fused[0].get("score", 0) if fused else 0
        if not context.strip() or top_score < 0.01:
            yield ("answer", "知识库中未找到相关信息，正在使用 AI 通用能力回答...\n\n")
            fallback_messages = [
                {"role": "system", "content": "你是一个专业的 AI 助手，请根据你的知识回答用户的问题。"},
                {"role": "user", "content": question},
            ]
            async for chunk in llm.chat_stream(fallback_messages):
                yield ("answer", chunk)
            return

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": CONTEXT_TEMPLATE.format(context=context, question=question)},
        ]

        # SSE 流式输出
        async for chunk in llm.chat_stream(messages):
            yield ("answer", chunk)

    async def _vector_search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        results = await query_vectors(query_embedding, top_k=top_k)
        items = []
        for r in results:
            items.append({
                "source": "vector",
                "content": r.get("document", ""),
                "metadata": r.get("metadata", {}),
                "distance": r.get("distance", 1.0),
            })
        return items

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

        # 搜索图谱
        entities = []
        for kw in keywords[:3]:
            results = await search_entities(kw, limit=5)
            entities.extend(results)

        items = []
        seen = set()
        for e in entities:
            name = e.get("name", "")
            if name not in seen:
                seen.add(name)
                items.append({
                    "source": "graph",
                    "content": f"{name} ({e.get('type', '')})",
                    "metadata": e,
                })
        return items

    async def _keyword_search(self, query: str, top_k: int = 5) -> list[dict]:
        async with async_session() as db:
            result = await db.execute(
                select(Chunk)
                .where(Chunk.content.contains(query))
                .limit(top_k)
            )
            chunks = result.scalars().all()
            items = []
            for c in chunks:
                items.append({
                    "source": "keyword",
                    "content": c.content,
                    "metadata": {"document_id": c.document_id, "chunk_index": c.chunk_index},
                })
            return items

    def _rrf_fusion(self, vector_results: list, graph_results: list, keyword_results: list) -> list[dict]:
        scores: dict[str, dict] = {}

        def _key(item: dict) -> str:
            return item.get("content", "")[:100]

        for rank, item in enumerate(vector_results):
            key = _key(item)
            if key not in scores:
                scores[key] = {**item, "score": 0}
            scores[key]["score"] += W_VEC / (RRF_K + rank + 1)

        for rank, item in enumerate(graph_results):
            key = _key(item)
            if key not in scores:
                scores[key] = {**item, "score": 0}
            scores[key]["score"] += W_GRAPH / (RRF_K + rank + 1)

        for rank, item in enumerate(keyword_results):
            key = _key(item)
            if key not in scores:
                scores[key] = {**item, "score": 0}
            scores[key]["score"] += W_KW / (RRF_K + rank + 1)

        return sorted(scores.values(), key=lambda x: x["score"], reverse=True)


_rag_engine: RAGEngine | None = None


def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
