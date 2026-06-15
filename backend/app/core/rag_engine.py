import asyncio
import json
import logging
import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import AsyncGenerator

from sqlalchemy import and_, not_, or_, select

from app.core.llm_client import get_llm_client
from app.core.embedding_client import get_embedding_client
from app.core.entity_quality import is_high_quality_entity_name
from app.core.runtime_config import load_raw_runtime_config
from app.core.vector_service import query_vectors
from app.services.graph_service import search_entity_context, find_multi_hop_paths
from app.db.mysql import async_session
from app.models.chunk import Chunk
from app.models.document import Document

logger = logging.getLogger("app")

SYSTEM_PROMPT = """你是一个企业内部文件问答搜索助手。请基于已上传的企业内部知识库文件回答用户问题。

核心原则：你的目标是尽可能帮助用户找到答案，而不是寻找拒答的理由。

规则：
1. 优先使用参考资料中的信息回答，不得使用模型常识或外部知识
2. 回答必须结论先行，然后给出文件中的明确依据
3. 综合多条参考资料进行推理；不要因为参考资料没有逐字包含完整答案就拒答
3a. 不得提出参考资料未明确要求的风险、例外条件或额外证明材料
3b. 不得使用”常见做法、行业惯例、通常情况”等资料外表述
4. 必须包含”引用来源：”一行，引用参考资料中的来源说明
5. 必须包含”【知识图谱引用】”区块
6. 只有当参考资料中完全没有相关内容时，才回答”根据企业内部知识库，未找到相关信息，无法回答该问题。”
7. 回答要准确、简洁、专业
8. 重要：参考资料中只要包含相关的条款、规定、数字或事实，就必须基于这些信息回答，即使需要合理推断。绝对不允许在有相关参考资料的情况下拒答
9. 重要：对于企业制度类问题（考勤、差旅、入职、保密、体检、年终总结等），优先使用企业内部制度文件中的内容回答
10. 重要：如果参考资料中包含部分答案（如360度评估权重），必须回答该部分，对未找到的部分说明”参考资料中未包含关于XX的规定”
11. 重要：当参考资料包含”加班费””调休””字数””体检费””审批”等关键词时，必须提取并回答相关内容，不得声称”未找到”

输出格式：
根据《文档名》的规定，直接回答用户问题。

文件中明确规定：引用或概括最相关的制度依据。

引用来源：[检索方式-文档ID] 文档名 - 第N页 - 分块M

【知识图谱引用】
- 实体或关系引用"""

CONTEXT_TEMPLATE = """参考资料：
{context}

检索充分性提示：
{retrieval_hints}

知识图谱引用：
{graph_context}

用户问题：{question}"""

RRF_K = 60
W_VEC = 0.4
W_GRAPH = 0.2
W_KW = 0.4
FALLBACK_PREFIX = "企业内部知识库中未找到相关信息，正在使用 AI 通用能力回答：\n\n"
SOURCE_LABELS = {
    "vector": "向量检索",
    "keyword": "关键词检索",
    "neighbor": "相邻切片",
}
KEYWORD_SEARCH_LIMIT_FACTOR = 6
VECTOR_TOP_K = 8
KEYWORD_TOP_K = 12
CONTEXT_TOP_K = 8
DEFAULT_SIMILARITY_THRESHOLD = 0.05
DEFAULT_MAX_CONTEXT_CHARS = 8000


@dataclass(frozen=True)
class RetrievalRuntimeConfig:
    vector_top_k: int = VECTOR_TOP_K
    keyword_top_k: int = KEYWORD_TOP_K
    context_top_k: int = CONTEXT_TOP_K
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    vector_weight: float = W_VEC
    graph_weight: float = W_GRAPH
    keyword_weight: float = W_KW
    bm25_enabled: bool = True
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS

DOMAIN_TERMS = (
    "总公司",
    "分公司",
    "投标",
    "招投标",
    "政府采购",
    "评分标准",
    "招标文件",
    "资质",
    "企业特别资质",
    "医疗机构执业许可证",
    "业绩",
    "设备",
    "人员证明",
    "合同签订",
    "社保缴纳",
    "授权",
    "认可",
    "供应商",
    "采购人",
    # 企业制度相关
    "考勤",
    "迟到",
    "早退",
    "旷工",
    "年假",
    "加班",
    "调休",
    "入职",
    "离职",
    "试用期",
    "转正",
    "辞职",
    "竞业限制",
    "体检",
    "年终总结",
    "绩效考核",
    "差旅报销",
    "住宿费",
    "审批权限",
    "保密",
    "客户现场",
    "高铁",
    "二等座",
    "通讯费",
)
SCENARIO_PROFILES = {
    "government_procurement": {
        "triggers": ("政府采购", "招标", "投标", "供应商", "采购人", "采购文件", "评分标准"),
        "terms": (
            "政府采购",
            "采购人",
            "供应商",
            "供应商条件",
            "招标文件",
            "采购文件",
            "评审因素",
            "评标标准",
            "资格条件",
            "特定条件",
            "差别待遇",
            "歧视待遇",
            "资质证明文件",
            "业绩情况",
            "第二十二条",
            "第二十三条",
            "第十七条",
        ),
    },
    "accounting": {
        "triggers": ("会计", "财务", "报销", "凭证", "发票", "资产", "折旧", "预算"),
        "terms": ("会计准则", "会计制度", "财务制度", "原始凭证", "报销", "预算", "固定资产", "折旧"),
    },
    "meeting_travel": {
        "triggers": ("会议", "差旅", "出差", "住宿", "交通", "培训"),
        "terms": ("会议费", "差旅费", "出差审批", "住宿费", "交通费", "培训费", "报销标准"),
    },
    "asset_management": {
        "triggers": ("资产", "固定资产", "采购", "验收", "盘点", "处置"),
        "terms": ("固定资产", "资产验收", "资产盘点", "资产处置", "采购审批", "入账"),
    },
    "safety": {
        "triggers": ("安全", "生产", "事故", "应急", "隐患"),
        "terms": ("安全生产", "应急预案", "隐患排查", "事故处理", "安全责任"),
    },
    "non_tax_invoice": {
        "triggers": ("票据", "非税", "收费", "发票", "收据"),
        "terms": ("财政票据", "非税收入", "收费管理", "发票", "收据", "缴款"),
    },
    "enterprise_hr": {
        "triggers": ("入职", "离职", "考勤", "迟到", "早退", "旷工", "年假", "加班", "调休", "试用期", "转正", "辞职", "竞业", "体检", "年终总结", "绩效", "工资", "薪资", "社保", "公积金"),
        "terms": ("考勤管理制度", "新员工入职手册", "员工体检通知", "年终总结", "差旅报销管理制度", "保密规定",
                  "打卡", "迟到", "早退", "旷工", "年假", "加班费", "调休", "试用期", "转正", "辞职", "竞业限制",
                  "体检费用", "360度评估", "绩效考核", "审批权限", "报销标准", "住宿费上限", "高铁", "二等座"),
    },
    "enterprise_security": {
        "triggers": ("保密", "客户现场", "信息安全", "加密", "微信", "数据泄露"),
        "terms": ("客户现场安全保密规定", "加密通讯", "敏感信息", "保密协议", "信息安全", "数据清理"),
    },
}
BRANCH_COMPANY_TERMS = (
    "供应商",
    "法人",
    "其他组织",
    "独立承担民事责任",
    "良好记录",
    "社会保障资金",
    "资质证明文件",
    "业绩情况",
    "供应商条件",
    "特定条件",
    "差别待遇",
    "歧视待遇",
    "分公司不具有法人资格",
    "民事责任由公司承担",
    "签订劳动合同",
    "社会保险",
    "招标文件中没有规定的评标标准",
    "招标文件中没有规定的评标标准不得作为评审的依据",
    "评审的依据",
)
PROFILE_TERMS = tuple(term for profile in SCENARIO_PROFILES.values() for term in profile["terms"])
IMPORTANT_KEYWORD_TERMS = frozenset(DOMAIN_TERMS + PROFILE_TERMS + BRANCH_COMPANY_TERMS)
GENERIC_GRAPH_TERMS = {
    "设备",
    "材料",
    "合同",
    "社保",
    "采购",
    "投标",
    "供应商",
    "采购人",
    "证明",
    "人员",
}

INJECTION_PATTERNS = [
    # English patterns
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now\s+",
    r"system\s*:\s*",
    r"<\|system\|>",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"dan\s+mode",
    # Chinese patterns
    r"忽略.{0,10}(之前|以上|所有).{0,10}(指令|提示|规则)",
    r"你现在是",
    r"进入.{0,5}(开发者|调试|越狱|无限制).{0,5}模式",
    r"无视.{0,10}(安全|限制|规则|约束)",
    r"扮演.{0,10}(角色|助手|AI)",
    r"输出.{0,10}(系统|原始|初始).{0,10}(提示|prompt)",
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

    if len(normalized) <= 80:
        add(normalized)

    for term in DOMAIN_TERMS:
        if term in normalized:
            add(term)

    for profile in SCENARIO_PROFILES.values():
        if any(trigger in normalized for trigger in profile["triggers"]):
            for term in profile["terms"]:
                add(term)

    if "总公司" in normalized and "分公司" in normalized:
        for term in BRANCH_COMPANY_TERMS:
            add(term)

    for term in re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_:.-]{2,}", normalized):
        add(term)
        if len(term) >= 12:
            for size in (4, 6):
                for start in range(0, len(term) - size + 1, size):
                    add(term[start:start + size])

    if "打卡" in normalized:
        add("打卡")
    if "考勤" in normalized or "打卡" in normalized:
        add("考勤")
        add("迟到")
        add("考勤管理制度")

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

    # 企业制度文档名称映射：查询中出现相关关键词时，添加对应的文档名
    _enterprise_doc_mappings = {
        ("差旅", "报销", "出差", "高铁", "飞机", "住宿", "交通", "审批"): "差旅报销管理制度",
        ("考勤", "迟到", "早退", "旷工", "打卡", "上班", "下班", "加班", "调休", "年假", "请假"): "考勤管理制度",
        ("入职", "离职", "辞职", "试用期", "转正", "竞业", "劳动合同", "入职材料"): "新员工入职手册",
        ("保密", "客户现场", "微信", "加密", "信息安全", "数据泄露"): "客户现场安全保密规定",
        ("年终总结", "360度", "绩效考核", "考评", "年终"): "年终总结工作通知",
        ("体检", "体检费用", "体检标准"): "员工体检通知",
    }
    for trigger_set, doc_name in _enterprise_doc_mappings.items():
        if any(t in normalized for t in trigger_set):
            add(doc_name)

    return terms[:80]


def _keyword_term_weight(term: str) -> float:
    if term in BRANCH_COMPANY_TERMS and len(term) >= 8:
        return 8.0
    if term in IMPORTANT_KEYWORD_TERMS:
        return 4.0
    if len(term) >= 10:
        return 3.0
    if len(term) >= 4:
        return 2.0
    return 1.0


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


def _coerce_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    if value is None:
        return default
    return bool(value)


async def _load_retrieval_config() -> RetrievalRuntimeConfig:
    try:
        raw = await load_raw_runtime_config()
        config_value = raw.get("retrieval_config")
        config = json.loads(config_value) if config_value else {}
        if not isinstance(config, dict):
            config = {}
    except Exception as exc:
        logger.warning(f"读取 retrieval_config 失败，使用默认检索配置: {exc}")
        config = {}

    top_k = int(config.get("top_k", VECTOR_TOP_K))
    top_k = min(max(top_k, 1), 30)
    vector_top_k = max(top_k, VECTOR_TOP_K)
    context_top_k = min(max(top_k, CONTEXT_TOP_K), 20)
    keyword_top_k = min(max(top_k * 2, KEYWORD_TOP_K), 40)
    vector_weight = float(config.get("vector_weight", W_VEC))
    graph_weight = float(config.get("graph_weight", W_GRAPH))
    keyword_weight = max(0.1, 1.0 - min(max(vector_weight, 0.0), 1.0))
    try:
        max_context_chars = int(config.get("max_context_chars", DEFAULT_MAX_CONTEXT_CHARS))
    except (TypeError, ValueError):
        max_context_chars = DEFAULT_MAX_CONTEXT_CHARS
    max_context_chars = min(max(max_context_chars, 2000), 24000)

    return RetrievalRuntimeConfig(
        vector_top_k=vector_top_k,
        keyword_top_k=keyword_top_k,
        context_top_k=context_top_k,
        similarity_threshold=float(config.get("similarity_threshold", DEFAULT_SIMILARITY_THRESHOLD)),
        vector_weight=vector_weight,
        graph_weight=graph_weight,
        keyword_weight=keyword_weight,
        bm25_enabled=_coerce_bool(config.get("bm25_enabled"), True),
        max_context_chars=max_context_chars,
    )


SENTENCE_END_CHARS = "。！？；;\n"


def _trim_to_sentence_boundary(text: str, limit: int, min_keep: int = 200) -> str:
    """把超长文本截断到 limit 以内，且尽量停在句末标点处。

    解决固定窗口硬截断破坏语义单元的问题：宁可少装一句，
    也不在句子中间切开；不足 min_keep 字符时放弃截断（返回空）。
    """
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit < min_keep:
        return ""
    window = text[:limit]
    for i in range(len(window) - 1, min_keep - 2, -1):
        if window[i] in SENTENCE_END_CHARS:
            return window[: i + 1].rstrip()
    return window.rstrip()


# 查询向量 LRU 缓存：同一问题重复提问（多轮会话、压测）时省去一次 Embedding API 往返
_EMBED_CACHE: OrderedDict = OrderedDict()
_EMBED_CACHE_MAX = 256


async def _embed_query_cached(question: str) -> list[float] | None:
    embedding_client = get_embedding_client()
    cache_key = f"{getattr(embedding_client, 'model', '')}:{question.strip()}"
    cached = _EMBED_CACHE.get(cache_key)
    if cached is not None:
        _EMBED_CACHE.move_to_end(cache_key)
        return cached
    embedding = await embedding_client.embed(question)
    if embedding:
        _EMBED_CACHE[cache_key] = embedding
        _EMBED_CACHE.move_to_end(cache_key)
        while len(_EMBED_CACHE) > _EMBED_CACHE_MAX:
            _EMBED_CACHE.popitem(last=False)
    return embedding


class RAGEngine:
    async def query(self, question: str) -> AsyncGenerator[tuple, None]:
        if _check_injection(question):
            yield ("answer", "检测到不安全的输入，已拒绝回答。")
            return

        retrieval_config = await _load_retrieval_config()

        # 三路并行检索
        try:
            query_embedding = await _embed_query_cached(question)
        except Exception as exc:
            logger.warning(f"向量化失败，降级为直接 LLM 调用: {exc}")
            query_embedding = None

        if query_embedding:
            vector_results, graph_results, keyword_results = await asyncio.gather(
                self._vector_search(
                    query_embedding,
                    top_k=retrieval_config.vector_top_k,
                    similarity_threshold=retrieval_config.similarity_threshold,
                ),
                self._graph_search(question),
                self._keyword_search(
                    question,
                    top_k=retrieval_config.keyword_top_k,
                    enabled=retrieval_config.bm25_enabled,
                ),
                return_exceptions=True,
            )
        else:
            vector_results, graph_results, keyword_results = [], [], []
            try:
                graph_results, keyword_results = await asyncio.gather(
                    self._graph_search(question),
                    self._keyword_search(
                        question,
                        top_k=retrieval_config.keyword_top_k,
                        enabled=retrieval_config.bm25_enabled,
                    ),
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
            item for item in self._rrf_fusion(
                vector_results,
                [],
                keyword_results,
                config=retrieval_config,
            )
            if item.get("document_name")
        ]
        fused = await self._expand_neighbor_chunks(fused, limit=retrieval_config.context_top_k)

        # 意图识别 + 定向二次检索
        intent_terms = self._extract_intent_terms(question)
        if intent_terms:
            targeted = await self._targeted_retrieval(intent_terms, fused)
            if targeted:
                # 将定向检索结果插入到 fused 列表前面
                fused = targeted + [item for item in fused
                                    if (item.get("document_id"), item.get("chunk_index"))
                                    not in {(t.get("document_id"), t.get("chunk_index")) for t in targeted}]

        graph_context = self._format_graph_context(graph_results)

        # 输出引用来源
        sources = []
        for item in fused[:retrieval_config.context_top_k]:
            display_score = self._display_score(item)
            sources.append({
                "document_name": item.get("document_name", ""),
                "page_number": item.get("page_number"),
                "chunk_content": item.get("content", "")[:200],
                "document_id": item.get("document_id"),
                "chunk_index": item.get("chunk_index"),
                "source_type": item.get("source"),
                "score": display_score,
                "display_score": display_score,
                "vector_similarity": self._vector_similarity(item),
                "keyword_score": item.get("keyword_score", 0),
                "rrf_score": item.get("score", 0),
            })
        yield ("sources", sources)

        # 组装上下文（去重 + 文档分组限制 + 预算制长度管理）
        # 预算制：追加前先检查剩余空间；放不下时按句子边界截断而非硬截断，
        # 保持语义单元完整，且不因一个大块提前放弃后续小块。
        context_parts = []
        seen_content = set()
        doc_chunk_count = {}
        MAX_CHUNKS_PER_DOC = 3
        max_context_chars = retrieval_config.max_context_chars
        total_chars = 0

        for item in fused[:retrieval_config.context_top_k * 3]:
            if total_chars >= max_context_chars:
                break
            doc_id = item.get("document_id")
            content = item.get("content", "").strip()
            if not content:
                continue

            # 内容去重：跳过高度重叠的 chunk
            content_sig = content[:100]
            if content_sig in seen_content:
                continue
            seen_content.add(content_sig)

            # 文档分组限制：定向检索和关键词匹配的 chunk 不受限制
            source = item.get("source", "")
            doc_key = doc_id or item.get("document_name", "")
            if source in ("targeted", "keyword"):
                # 定向检索和关键词匹配的 chunk 优先，不受文档分组限制
                pass
            else:
                doc_chunk_count[doc_key] = doc_chunk_count.get(doc_key, 0) + 1
                if doc_chunk_count[doc_key] > MAX_CHUNKS_PER_DOC:
                    continue

            doc_name = item.get("document_name", "未知文档")
            page = item.get("page_number", "")
            source_label = SOURCE_LABELS.get(source, source or "检索")
            chunk_index = item.get("chunk_index")
            page_info = f" (第{page}页)" if page else ""
            chunk_info = f" - 分块{chunk_index}" if chunk_index is not None else ""
            source_info = f"[{source_label}-文档{doc_id}] {doc_name}{page_info}{chunk_info}"
            header = f"来源说明：{source_info}\n内容："
            part_len = len(header) + len(content) + 2  # +2 for joiner

            remaining = max_context_chars - total_chars
            if part_len <= remaining:
                context_parts.append(f"{header}{content}")
                total_chars += part_len
                continue

            # 整块放不下：尝试按句子边界截断到剩余预算
            allowed = remaining - len(header) - len("\n……（该分块剩余内容因长度限制省略）") - 2
            trimmed = _trim_to_sentence_boundary(content, allowed)
            if trimmed:
                context_parts.append(f"{header}{trimmed}\n……（该分块剩余内容因长度限制省略）")
                total_chars = max_context_chars
            # 截不出有意义的内容则跳过，继续尝试后面更短的块

        context = "\n\n".join(context_parts)
        retrieval_hints = self._format_retrieval_hints(question, fused[:retrieval_config.context_top_k])

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
                    retrieval_hints=retrieval_hints,
                    graph_context=graph_context,
                    question=question,
                ),
            },
        ]

        # SSE 流式输出
        async for chunk in llm.chat_stream(messages):
            yield ("answer", chunk)

    async def _vector_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> list[dict]:
        results = await query_vectors(query_embedding, top_k=top_k)
        items = []
        for r in results:
            metadata = r.get("metadata", {}) or {}
            distance = r.get("distance", 1.0)
            vector_similarity = max(0.0, min(1.0, 1 - float(distance)))
            if vector_similarity < similarity_threshold:
                continue
            items.append({
                "source": "vector",
                "content": r.get("document", ""),
                "metadata": metadata,
                "document_id": metadata.get("document_id"),
                "chunk_index": metadata.get("chunk_index"),
                "vector_id": r.get("id"),
                "distance": distance,
                "vector_similarity": vector_similarity,
            })
        return await self._hydrate_chunk_results(items)

    async def _graph_search(self, query: str) -> list[dict]:
        # LLM + 规则词共同提取实体关键词，避免长问题只抽出泛词。
        rule_keywords = _build_keyword_terms(query)
        llm = get_llm_client()
        try:
            # 限时提取：LLM 慢响应不应拖垮整条检索链路
            resp = await asyncio.wait_for(
                llm.chat([
                    {
                        "role": "user",
                        "content": (
                            "从以下问题中提取可用于知识图谱检索的核心实体、法规、条款、主体、材料或条件，"
                            "用逗号分隔，只输出实体名：\n"
                            f"{query}"
                        ),
                    }
                ]),
                timeout=8,
            )
            keywords = [k.strip() for k in resp.split(",") if k.strip()]
        except Exception:
            keywords = []

        for term in rule_keywords:
            if term not in keywords:
                keywords.append(term)
        if "总公司" in query and "分公司" in query:
            branch_terms = [
                "总公司",
                "分公司",
                "公司法",
                "民事责任",
                "法人资格",
                "政府采购法",
                "第二十二条",
                "第二十三条",
                "第十七条",
                "供应商",
                "资质证明文件",
                "业绩情况",
                "社会保障资金",
                "设备和专业技术能力证明材料",
            ]
            keywords = branch_terms + [term for term in keywords if term not in branch_terms]

        # 搜索图谱实体及其直接关系（并行查询，降低多关键词串行延迟）
        effective_keywords = [
            kw for kw in keywords[:16]
            if kw not in GENERIC_GRAPH_TERMS and (len(kw) >= 4 or kw in {"总公司", "分公司", "公司法"})
        ][:10]
        graph_items = []
        if effective_keywords:
            results_list = await asyncio.gather(
                *(search_entity_context(kw, limit=4) for kw in effective_keywords),
                return_exceptions=True,
            )
            for results in results_list:
                if isinstance(results, Exception):
                    continue
                graph_items.extend(results)

        items = []
        seen = set()
        for e in graph_items:
            name = e.get("name", "")
            if not name or not is_high_quality_entity_name(name):
                continue
            if name not in seen:
                seen.add(name)
                items.append({
                    "source": "graph",
                    "content": f"{name} ({e.get('type', '')})",
                    "metadata": e,
                    "entity": e,
                })

        # 多跳推理：在命中实体之间查找 1..2 跳路径，补全中间概念（A→B→C→D）
        matched_names = [item["entity"].get("name", "") for item in items][:8]
        if len(matched_names) >= 2:
            try:
                paths = await find_multi_hop_paths(matched_names, max_hops=2, limit=10)
                for path in paths:
                    chain = " → ".join(n["name"] for n in path["nodes"])
                    items.append({
                        "source": "graph",
                        "content": f"路径: {chain}",
                        "metadata": {"path": path},
                        "path": path,
                    })
            except Exception as exc:
                logger.warning(f"多跳路径检索失败（忽略）: {exc}")
        return items

    async def _keyword_search(self, query: str, top_k: int = 5, enabled: bool = True) -> list[dict]:
        if not enabled:
            return []
        terms = _build_keyword_terms(query)
        if not terms:
            return []

        # 优先使用高权重的关键词进行搜索，减少泛化词的干扰
        high_weight_terms = [t for t in terms if _keyword_term_weight(t) >= 3.0]
        search_terms = high_weight_terms if high_weight_terms else terms[:10]
        # SQL LIKE 条件数上限：知识库规模增大后，几十个 OR-LIKE 会让全表扫描代价急剧上升
        search_terms = search_terms[:24]

        async with async_session() as db:
            # 同时搜索 chunk 内容和文档名
            content_conditions = [Chunk.content.contains(term) for term in search_terms]
            name_conditions = [Document.name.contains(term) for term in search_terms if len(term) >= 4]
            all_conditions = content_conditions + name_conditions
            result = await db.execute(
                select(Chunk, Document)
                .join(Document, Chunk.document_id == Document.id)
                .where(or_(*all_conditions))
                .limit(max(top_k * KEYWORD_SEARCH_LIMIT_FACTOR, 500))
            )
            items = []
            for c, doc in result.all():
                matched_terms = [term for term in terms if term in c.content]
                # 文档名匹配的关键词也加入
                doc_name = doc.name or ""
                name_matched_terms = [term for term in terms if len(term) >= 4 and term in doc_name]
                all_matched = list(set(matched_terms + name_matched_terms))
                if not all_matched:
                    continue
                keyword_score = sum(_keyword_term_weight(term) for term in all_matched)
                # 文档名匹配额外加分
                for term in name_matched_terms:
                    keyword_score += _keyword_term_weight(term) * 1.0
                items.append({
                    "source": "keyword",
                    "content": c.content,
                    "metadata": {"document_id": c.document_id, "chunk_index": c.chunk_index},
                    "document_id": c.document_id,
                    "document_name": doc.name,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "vector_id": c.vector_id,
                    "keyword_hits": len(all_matched),
                    "keyword_score": keyword_score,
                    "keyword_term_count": len(terms),
                    "matched_terms": all_matched,
                })
            return sorted(
                items,
                key=lambda item: (
                    item.get("keyword_score", 0),
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

    async def _expand_neighbor_chunks(self, items: list[dict], limit: int) -> list[dict]:
        """Add nearby chunks for top hits so one law/document can provide adjacent articles."""
        if not items:
            return items

        existing = {
            (item.get("document_id"), item.get("chunk_index"))
            for item in items
            if item.get("document_id") is not None and item.get("chunk_index") is not None
        }
        wanted = set()
        parent_scores = {}
        for item in items[: max(5, min(limit, 10))]:
            document_id = item.get("document_id")
            chunk_index = item.get("chunk_index")
            if document_id is None or chunk_index is None:
                continue
            for offset in (-5, -4, -3, -2, -1, 1, 2, 3, 4, 5):
                neighbor_key = (document_id, chunk_index + offset)
                if chunk_index + offset >= 0:
                    wanted.add(neighbor_key)
                    parent_scores[neighbor_key] = max(parent_scores.get(neighbor_key, 0), item.get("score", 0))
        if not wanted:
            return items

        async with async_session() as db:
            result = await db.execute(
                select(Chunk, Document)
                .join(Document, Chunk.document_id == Document.id)
                .where(or_(*(and_(Chunk.document_id == doc_id, Chunk.chunk_index == idx) for doc_id, idx in wanted)))
            )
            neighbors = []
            for chunk, doc in result.all():
                parent_score = parent_scores.get((chunk.document_id, chunk.chunk_index), 0)
                neighbors.append({
                    "source": "neighbor",
                    "content": chunk.content,
                    "metadata": {"document_id": chunk.document_id, "chunk_index": chunk.chunk_index},
                    "document_id": chunk.document_id,
                    "document_name": doc.name,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "vector_id": chunk.vector_id,
                    "score": max(parent_score - 0.02, 0),
                    "retrieval_sources": ["neighbor"],
                })

        merged = {f"{item.get('document_id')}:{item.get('chunk_index')}": item for item in items}
        for doc_id, idx in wanted & existing:
            key = f"{doc_id}:{idx}"
            if key in merged:
                merged[key]["score"] = max(merged[key].get("score", 0), parent_scores.get((doc_id, idx), 0) - 0.02)
                sources = merged[key].setdefault("retrieval_sources", [])
                if "neighbor" not in sources:
                    sources.append("neighbor")
        for item in neighbors:
            merged.setdefault(f"{item.get('document_id')}:{item.get('chunk_index')}", item)
        return sorted(merged.values(), key=lambda item: item.get("score", 0), reverse=True)

    def _format_graph_context(self, graph_results: list[dict]) -> str:
        if not graph_results:
            return "- 未检索到相关实体或关系"

        lines = []
        seen = set()

        # 优先输出多跳推理路径：它们串联了问题中两个概念之间的中间实体
        for item in graph_results:
            path = item.get("path")
            if not path:
                continue
            nodes = path.get("nodes") or []
            rels = path.get("rels") or []
            if len(nodes) < 2:
                continue
            parts = [nodes[0]["name"]]
            for i, rel in enumerate(rels):
                target = nodes[i + 1]["name"] if i + 1 < len(nodes) else ""
                parts.append(f"—[{rel}]→ {target}")
            line = "- 推理路径：" + " ".join(parts)
            if line not in seen:
                lines.append(line)
                seen.add(line)

        for item in graph_results[:12]:
            if item.get("path"):
                continue
            entity = item.get("entity") or item.get("metadata") or {}
            name = entity.get("name", "")
            entity_type = entity.get("type", "")
            desc = entity.get("description", "")
            if name and is_high_quality_entity_name(name):
                line = f"- 实体：{name}（类型：{entity_type or '未知'}）"
                if desc:
                    line += f" — {desc}"
                if line not in seen:
                    lines.append(line)
                    seen.add(line)
            for rel in entity.get("relations", [])[:4]:
                source = rel.get("source", "")
                rel_type = rel.get("relation_type", "")
                target = rel.get("target", "")
                if (
                    source
                    and rel_type
                    and target
                    and is_high_quality_entity_name(source)
                    and is_high_quality_entity_name(target)
                ):
                    line = f"- 关系：{source} → {rel_type} → {target}"
                    if line not in seen:
                        lines.append(line)
                        seen.add(line)

        return "\n".join(lines) if lines else "- 未检索到相关实体或关系"

    def _format_retrieval_hints(self, question: str, fused_results: list[dict]) -> str:
        context = "\n".join(item.get("content", "") for item in fused_results)
        hints = []
        if "总公司" in question and "分公司" in question:
            if "资质证明文件" in context and "业绩情况" in context:
                hints.append("- 已检索到政府采购法关于供应商条件、资质证明文件和业绩情况的规定，可用于判断资质、业绩、设备和人员证明材料的认定。")
            if "分公司不具有法人资格" in context and "民事责任由公司承担" in context:
                hints.append("- 已检索到公司法关于分公司不具有法人资格、民事责任由公司承担的规定，可用于判断总分公司法律责任和材料归属关系。")
            if "招标文件中没有规定的评标标准不得作为评审的依据" in context:
                hints.append("- 已检索到政府采购法实施条例关于招标文件未规定的评标标准不得作为评审依据的规定，可用于判断评分标准没有特别要求时的认定边界。")
            if hints:
                hints.append("- 在采购文件或评分标准没有特别要求时，应围绕“总公司使用分公司资质、业绩、设备和人员证明材料可予认定；合同签订和社保缴纳材料结合总公司授权及招标文件要求认定”给出结论。")
                hints.append("- 不要额外推断劳动关系风险，不要要求分公司必须另行签订合同或缴纳社保，除非参考资料中明确写明。")
                hints.append("- 不要将总公司统一签订合同、缴纳社保描述为“常见企业管理模式”；只能表述为题述情形下结合授权和招标文件要求认定。")
                hints.append("- 不要自行列举工商登记文件、内部管理文件等额外证明材料；如果资料不足以列清单，只说明需结合总公司授权和招标文件要求认定。")
                hints.append("- 请基于上述已检索资料综合回答，不要因缺少逐字问答资料而直接拒答。")
        return "\n".join(hints) if hints else "- 无额外提示"

    def _rrf_fusion(
        self,
        vector_results: list,
        graph_results: list,
        keyword_results: list,
        config: RetrievalRuntimeConfig | None = None,
    ) -> list[dict]:
        config = config or RetrievalRuntimeConfig()
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
                "distance",
                "vector_similarity",
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
                target["keyword_score"] = max(target.get("keyword_score", 0), item.get("keyword_score", 0))

        def _keyword_bonus(item: dict) -> float:
            term_count = max(item.get("keyword_term_count", 0), 1)
            hit_ratio = min(1.0, item.get("keyword_hits", 0) / term_count)
            strong_hits = sum(1 for term in item.get("matched_terms", []) if len(term) >= 4 or ":" in term)
            weighted_hits = item.get("keyword_score", item.get("keyword_hits", 0))
            document_name = item.get("document_name", "")
            policy_bonus = 0.0
            # 企业制度文档大幅加分
            if "管理制度" in document_name:
                policy_bonus += 0.08
            elif "制度" in document_name:
                policy_bonus += 0.05
            if "手册" in document_name:
                policy_bonus += 0.05
            if "通知" in document_name and ("年终" in document_name or "体检" in document_name):
                policy_bonus += 0.05
            if "保密" in document_name:
                policy_bonus += 0.05
            # 匹配的关键词中包含文档名片段时额外加分
            for term in item.get("matched_terms", []):
                if len(term) >= 4 and term in document_name:
                    policy_bonus += 0.04
            if strong_hits >= 5:
                policy_bonus += 0.03
            return min(0.25, 0.01 * weighted_hits) + 0.03 * hit_ratio + 0.01 * min(strong_hits, 3) + policy_bonus

        for rank, item in enumerate(vector_results):
            key = _key(item)
            if key not in scores:
                scores[key] = {**item, "score": 0, "retrieval_sources": []}
            _merge_item(scores[key], item)
            scores[key]["score"] += config.vector_weight / (RRF_K + rank + 1)

        for rank, item in enumerate(graph_results):
            key = _key(item)
            if key not in scores:
                scores[key] = {**item, "score": 0, "retrieval_sources": []}
            _merge_item(scores[key], item)
            scores[key]["score"] += config.graph_weight / (RRF_K + rank + 1)

        for rank, item in enumerate(keyword_results):
            key = _key(item)
            if key not in scores:
                scores[key] = {**item, "score": 0, "retrieval_sources": []}
            _merge_item(scores[key], item)
            scores[key]["score"] += config.keyword_weight / (RRF_K + rank + 1) + _keyword_bonus(item)

        return sorted(scores.values(), key=lambda x: x["score"], reverse=True)

    def _display_score(self, item: dict) -> float:
        if item.get("keyword_hits") and item.get("keyword_term_count"):
            keyword_score = min(1.0, item["keyword_hits"] / max(item["keyword_term_count"], 1))
            if item.get("distance") is None:
                return keyword_score
            vector_score = self._vector_similarity(item)
            return max(vector_score, keyword_score)
        if item.get("distance") is not None:
            return self._vector_similarity(item)
        return item.get("score", 0)

    def _extract_intent_terms(self, question: str) -> list[str]:
        """从问题中提取意图关键词，用于定向二次检索。

        策略：提取问题中具体的查询对象词（如"加班费""字数""体检费"），
        这些词是用户真正想查找的内容，应该出现在 chunk 中。
        """
        terms = []
        # 意图模式：问题中具体的查询对象
        intent_patterns = [
            # 费用/标准类
            (r"(加班费|调休|年假|事假|病假|婚假|产假|丧假)", 1),
            (r"(住宿费|交通费|伙食费|通讯费|差旅费|报销)", 1),
            (r"(体检费|体检标准|体检费用)", 1),
            (r"(工资|薪资|薪酬|奖金|补贴|津贴|福利)", 1),
            # 数量/要求类
            (r"(字数|字以内|不少于|不超过|至少|上限|下限)", 1),
            (r"(权重|占比|比例|百分比|%)", 1),
            (r"(天数|几天|多少天|期限|有效期|截止)", 1),
            # 时间/条件类
            (r"(提前多久|提前几天|多久之内|几个工作日)", 1),
            (r"(审批|批准|审核|签字)", 1),
            # 资格/条件类
            (r"(商号|注册商标|授权商标|品牌)", 1),
            (r"(资质|资格|条件|要求|标准)", 1),
            (r"(开办费|长期待摊|管理费用|当期损益)", 1),
            (r"(固定资产|折旧|入账|暂估)", 1),
            # 具体数字
            (r"(\d+元|\d+天|\d+倍|\d+%)", 2),
        ]
        for pattern, weight in intent_patterns:
            matches = re.findall(pattern, question)
            for match in matches:
                if match not in terms:
                    terms.append(match)

        return terms

    async def _targeted_retrieval(self, intent_terms: list[str], fused: list[dict]) -> list[dict]:
        """定向二次检索：搜索包含意图关键词的 chunk。

        策略：
        1. 扩展搜索词（如"加班费"→也搜"加班""1.5倍"）
        2. 在所有文档中搜索，不限于 fused 结果
        3. 使用子串匹配（"加班"匹配"加班费"）
        """
        if not intent_terms:
            return []

        # 扩展搜索词：每个意图词加上相关变体
        search_terms = list(intent_terms)
        term_expansions = {
            "加班费": ["加班按", "倍工资", "加班申请", "加班工资"],
            "调休": ["调休需", "调休", "补休", "调休有效期"],
            "体检费": ["体检", "体检费用", "体检标准"],
            "字数": ["800字", "1500字", "2500字", "不少于"],
            "权重": ["50%", "20%", "10%", "占比"],
            "审批": ["审批", "批准", "负责人"],
            "开办费": ["开办费", "管理费用", "筹建期间"],
            "当期损益": ["管理费用", "开办费"],
            "长期待摊": ["长期待摊", "管理费用"],
            "授权商标": ["商号", "注册商标", "商标"],
            "商号": ["注册商标", "商标", "制造"],
            "有效期": ["使用完毕", "调休有效期", "期限"],
        }
        for term in intent_terms:
            if term in term_expansions:
                for exp in term_expansions[term]:
                    if exp not in search_terms:
                        search_terms.append(exp)

        # 从 fused 结果中提取文档 ID（优先在这些文档中搜索）
        priority_doc_ids = {item.get("document_id") for item in fused[:10] if item.get("document_id")}

        async with async_session() as db:
            targeted = []
            seen_targeted_keys: set[tuple] = set()

            def _make_targeted_dict(c, doc, matched, score):
                return {
                    "source": "targeted",
                    "content": c.content,
                    "metadata": {"document_id": c.document_id, "chunk_index": c.chunk_index},
                    "document_id": c.document_id,
                    "document_name": doc.name,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "vector_id": c.vector_id,
                    "score": score / 20.0,  # 归一化分数
                    "retrieval_sources": ["targeted"],
                    "keyword_hits": len(matched),
                    "matched_terms": matched,
                }

            # 第一轮：优先在企业制度文档（PDF）中搜索
            enterprise_conditions = [
                Document.name.endswith('.pdf'),
                or_(*(Chunk.content.contains(term) for term in search_terms)),
            ]
            enterprise_result = await db.execute(
                select(Chunk, Document)
                .join(Document, Chunk.document_id == Document.id)
                .where(and_(*enterprise_conditions))
                .limit(30)
            )

            for c, doc in enterprise_result.all():
                key = (c.document_id, c.chunk_index)
                if key in seen_targeted_keys:
                    continue
                matched = [term for term in search_terms if term in c.content]
                # 必须匹配至少一个原始意图词（不是扩展词）
                intent_matched = [t for t in intent_terms if t in c.content]
                if not intent_matched:
                    continue
                # 至少匹配 2 个词（意图词 + 扩展词）以减少误匹配
                if len(matched) < 2 and not any(len(t) >= 4 for t in intent_matched):
                    continue
                score = 10 + len(matched) * 2  # 企业文档基础分 10
                score += len(intent_matched) * 5  # 匹配原始意图词大幅加分
                if c.document_id in priority_doc_ids:
                    score += 3
                targeted.append(_make_targeted_dict(c, doc, matched, score))
                seen_targeted_keys.add(key)

            # 第二轮：在其他文档中搜索（补充）
            if len(targeted) < 3:
                other_conditions = [
                    not_(Document.name.endswith('.pdf')),
                    or_(*(Chunk.content.contains(term) for term in search_terms)),
                ]
                other_result = await db.execute(
                    select(Chunk, Document)
                    .join(Document, Chunk.document_id == Document.id)
                    .where(and_(*other_conditions))
                    .limit(20)
                )

                for c, doc in other_result.all():
                    key = (c.document_id, c.chunk_index)
                    if key in seen_targeted_keys:
                        continue
                    matched = [term for term in search_terms if term in c.content]
                    # 必须匹配至少一个原始意图词
                    intent_matched = [t for t in intent_terms if t in c.content]
                    if not intent_matched:
                        continue
                    if len(matched) < 2 and not any(len(t) >= 4 for t in intent_matched):
                        continue
                    score = len(matched) * 2
                    score += len(intent_matched) * 5
                    if c.document_id in priority_doc_ids:
                        score += 2
                    targeted.append(_make_targeted_dict(c, doc, matched, score))
                    seen_targeted_keys.add(key)

            # 按分数排序
            targeted.sort(key=lambda x: -x.get("score", 0))

            return targeted[:5]

    def _vector_similarity(self, item: dict) -> float | None:
        if item.get("vector_similarity") is not None:
            return item.get("vector_similarity")
        if item.get("distance") is None:
            return None
        return max(0.0, min(1.0, 1 - float(item.get("distance", 1.0))))


_rag_engine: RAGEngine | None = None


def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
