import pytest

from app.core.runtime_config import EmbeddingRuntimeConfig, LLMRuntimeConfig
from app.services import dashboard_service


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data


class FakeAsyncClient:
    responses = []
    requests = []

    def __init__(self, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_llm_health_uses_runtime_model_name(monkeypatch):
    async def fake_config():
        return LLMRuntimeConfig(
            api_url="https://api.example.com/v1/chat/completions",
            api_key="key",
            model="deepseek-v4-pro",
            temperature=0.2,
            top_p=0.9,
            max_tokens=4096,
            timeout=30,
        )

    FakeAsyncClient.responses = [FakeResponse(200, {"choices": [{"message": {"content": "ok"}}]})]
    FakeAsyncClient.requests = []
    monkeypatch.setattr(dashboard_service, "get_llm_runtime_config", fake_config)
    monkeypatch.setattr(dashboard_service.httpx, "AsyncClient", FakeAsyncClient)

    item = await dashboard_service._check_llm_service()

    assert item["name"] == "LLM 服务 (deepseek-v4-pro)"
    assert item["status"] == "online"
    assert "api.example.com" in item["detail"]
    assert FakeAsyncClient.requests[0][1]["json"]["model"] == "deepseek-v4-pro"


@pytest.mark.asyncio
async def test_embedding_health_warns_when_endpoint_or_model_missing(monkeypatch):
    async def fake_config():
        return EmbeddingRuntimeConfig(
            api_url="https://api.deepseek.com/embeddings",
            api_key="key",
            model="deepseek-v4-pro",
            dimension=1024,
            timeout=30,
            batch_size=64,
        )

    FakeAsyncClient.responses = [FakeResponse(404), FakeResponse(404)]
    FakeAsyncClient.requests = []
    monkeypatch.setattr(dashboard_service, "get_embedding_runtime_config", fake_config)
    monkeypatch.setattr(dashboard_service.httpx, "AsyncClient", FakeAsyncClient)

    item = await dashboard_service._check_embedding_service()

    assert item["name"] == "Embedding 服务 (deepseek-v4-pro)"
    assert item["status"] == "warning"
    assert "接口或模型不存在" in item["detail"]


@pytest.mark.asyncio
async def test_llm_health_reports_auth_failure(monkeypatch):
    async def fake_config():
        return LLMRuntimeConfig(
            api_url="https://api.example.com/v1/chat/completions",
            api_key="bad-key",
            model="bad-model",
            temperature=0.2,
            top_p=0.9,
            max_tokens=4096,
            timeout=30,
        )

    FakeAsyncClient.responses = [FakeResponse(401)]
    FakeAsyncClient.requests = []
    monkeypatch.setattr(dashboard_service, "get_llm_runtime_config", fake_config)
    monkeypatch.setattr(dashboard_service.httpx, "AsyncClient", FakeAsyncClient)

    item = await dashboard_service._check_llm_service()

    assert item["status"] == "offline"
    assert "认证失败" in item["detail"]
