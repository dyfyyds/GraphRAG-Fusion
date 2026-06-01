import pytest

from app.core import rag_engine as rag_module
from app.core.rag_engine import FALLBACK_PREFIX, RAGEngine, SYSTEM_PROMPT, _build_keyword_terms


class FakeEmbeddingClient:
    async def embed(self, _question):
        return [0.1, 0.2, 0.3]


class FakeLLM:
    def __init__(self, chunks=None):
        self.chunks = chunks or ["ok"]
        self.stream_messages = []

    async def chat_stream(self, messages):
        self.stream_messages.append(messages)
        for chunk in self.chunks:
            yield chunk


@pytest.mark.asyncio
async def test_query_calls_llm_fallback_when_no_internal_results(monkeypatch):
    engine = RAGEngine()
    llm = FakeLLM(["fallback answer"])

    monkeypatch.setattr(rag_module, "get_embedding_client", lambda: FakeEmbeddingClient())
    monkeypatch.setattr(rag_module, "get_llm_client", lambda: llm)
    monkeypatch.setattr(RAGEngine, "_vector_search", lambda self, embedding, top_k=5: _async_return([]))
    monkeypatch.setattr(RAGEngine, "_graph_search", lambda self, question: _async_return([]))
    monkeypatch.setattr(RAGEngine, "_keyword_search", lambda self, question, top_k=5: _async_return([]))

    events = [event async for event in engine.query("企业外的问题")]

    assert events[0] == ("sources", [])
    assert events[1] == ("answer", FALLBACK_PREFIX)
    assert events[2] == ("answer", "fallback answer")
    assert llm.stream_messages[0][0]["content"] == "你是一个专业的 AI 助手，请直接回答用户的问题。"


@pytest.mark.asyncio
async def test_query_uses_internal_prompt_sources_and_graph_context(monkeypatch):
    engine = RAGEngine()
    llm = FakeLLM(["internal answer"])

    vector_result = [{
        "source": "vector",
        "content": "9:16-9:30打卡视为严重迟到，每次扣减当月绩效分2分。",
        "document_id": 7,
        "document_name": "考勤管理制度.pdf",
        "page_number": 3,
        "chunk_index": 2,
    }]
    graph_result = [{
        "source": "graph",
        "entity": {
            "name": "打卡流程",
            "type": "流程",
            "relations": [{
                "source": "打卡流程",
                "relation_type": "涉及",
                "target": "指纹/人脸识别考勤系统",
            }],
        },
    }]

    monkeypatch.setattr(rag_module, "get_embedding_client", lambda: FakeEmbeddingClient())
    monkeypatch.setattr(rag_module, "get_llm_client", lambda: llm)
    monkeypatch.setattr(RAGEngine, "_vector_search", lambda self, embedding, top_k=5: _async_return(vector_result))
    monkeypatch.setattr(RAGEngine, "_graph_search", lambda self, question: _async_return(graph_result))
    monkeypatch.setattr(RAGEngine, "_keyword_search", lambda self, question, top_k=5: _async_return([]))

    events = [event async for event in engine.query("9点17打卡属于什么")]

    assert events[0][0] == "sources"
    assert events[0][1][0]["document_name"] == "考勤管理制度.pdf"
    assert events[0][1][0]["page_number"] == 3
    assert events[0][1][0]["source_type"] == "vector"
    assert "企业内部文件问答搜索" in llm.stream_messages[0][0]["content"]
    assert "引用来源：" in llm.stream_messages[0][0]["content"]
    user_prompt = llm.stream_messages[0][1]["content"]
    assert "[向量检索-文档7] 考勤管理制度.pdf (第3页) - 分块2" in user_prompt
    assert "【知识图谱引用】" in SYSTEM_PROMPT
    assert "打卡流程 → 涉及 → 指纹/人脸识别考勤系统" in user_prompt


@pytest.mark.asyncio
async def test_hydrate_chunk_results_adds_document_metadata(monkeypatch):
    engine = RAGEngine()

    chunk = type("ChunkRow", (), {
        "document_id": 7,
        "chunk_index": 2,
        "page_number": 3,
        "vector_id": "doc_7_chunk_2",
        "content": "制度片段",
    })()
    doc = type("DocumentRow", (), {"name": "考勤管理制度.pdf"})()

    class FakeResult:
        def all(self):
            return [(chunk, doc)]

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, _statement):
            return FakeResult()

    monkeypatch.setattr(rag_module, "async_session", lambda: FakeSession())

    hydrated = await engine._hydrate_chunk_results([{
        "source": "vector",
        "content": "旧片段",
        "document_id": 7,
        "chunk_index": 2,
        "vector_id": "doc_7_chunk_2",
    }])

    assert hydrated[0]["document_name"] == "考勤管理制度.pdf"
    assert hydrated[0]["page_number"] == 3
    assert hydrated[0]["content"] == "制度片段"


def test_keyword_terms_normalize_attendance_time_query():
    terms = _build_keyword_terms("9点17打卡属于什么")

    assert "9:17" in terms
    assert "打卡" in terms
    assert "考勤" in terms
    assert "迟到" in terms
    assert "9:16" in terms
    assert "9:30" in terms
    assert "严重迟到" in terms


def test_rrf_fusion_combines_same_document_chunk_across_retrievers():
    engine = RAGEngine()

    fused = engine._rrf_fusion(
        [{
            "source": "vector",
            "document_id": 55,
            "chunk_index": 1,
            "content": "9:16-9:30 打卡视为严重迟到",
        }],
        [],
        [{
            "source": "keyword",
            "document_id": 55,
            "chunk_index": 1,
            "content": "9:16-9:30 打卡视为严重迟到",
        }],
    )

    assert len(fused) == 1
    assert fused[0]["score"] > 0.01


async def _async_return(value):
    return value
