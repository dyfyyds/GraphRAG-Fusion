import httpx

from app.core import embedding_client as embedding_client_module
from app.core.embedding_client import (
    EmbeddingClient,
    _embedding_endpoints,
    _extract_embeddings,
    _local_compat_embedding,
)
from app.core.runtime_config import EmbeddingRuntimeConfig


def test_embedding_endpoints_try_plain_and_v1_suffixes():
    assert _embedding_endpoints("https://api.deepseek.com/embeddings") == [
        "https://api.deepseek.com/embeddings",
        "https://api.deepseek.com/v1/embeddings",
    ]


def test_embedding_endpoints_replace_chat_completions_suffix():
    assert "https://api.example.com/v1/embeddings" in _embedding_endpoints(
        "https://api.example.com/v1/chat/completions"
    )


def test_extract_embeddings_supports_common_response_shapes():
    assert _extract_embeddings({"data": [{"embedding": [0.1, 0.2]}]}) == [[0.1, 0.2]]
    assert _extract_embeddings({"embedding": [0.3, 0.4]}) == [[0.3, 0.4]]
    assert _extract_embeddings({"embeddings": [[0.5, 0.6]]}) == [[0.5, 0.6]]


def test_local_compat_embedding_is_stable_and_normalized():
    first = _local_compat_embedding("9点17打卡属于什么", 128)
    second = _local_compat_embedding("9点17打卡属于什么", 128)

    assert first == second
    assert len(first) == 128
    assert 0.99 < sum(value * value for value in first) < 1.01


async def test_request_embeddings_uses_local_compat_when_endpoints_are_missing(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            request = httpx.Request("POST", "https://api.deepseek.com/embeddings")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("not found", request=request, response=response)

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(embedding_client_module.httpx, "AsyncClient", FakeClient)

    config = EmbeddingRuntimeConfig(
        api_url="https://api.deepseek.com/embeddings",
        api_key="test-key",
        model="deepseek-v4-pro",
        dimension=256,
        timeout=30,
        batch_size=64,
    )

    embeddings = await EmbeddingClient()._request_embeddings(config, ["客户现场安全保密规定"])

    assert len(embeddings) == 1
    assert len(embeddings[0]) == 256
