import httpx
import asyncio

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.runtime_config import get_embedding_runtime_config, EmbeddingRuntimeConfig


def _friendly_http_error(exc: httpx.HTTPStatusError) -> ValueError:
    status = exc.response.status_code
    if status in (401, 403):
        return ValueError("Embedding 服务认证失败，请检查 Embedding API Key。")
    if status == 404:
        return ValueError("Embedding 服务接口或模型不存在，请检查 API Base URL 和模型名称。")
    if status == 429:
        return ValueError("Embedding 服务请求过于频繁或额度不足，请稍后重试。")
    return ValueError(f"Embedding 服务返回错误 HTTP {status}，请检查模型配置。")


class EmbeddingClient:
    async def _config(self) -> EmbeddingRuntimeConfig:
        return await get_embedding_runtime_config()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def embed(self, text: str) -> list[float]:
        config = await self._config()
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            resp = await client.post(
                config.api_url,
                headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
                json={"model": config.model, "input": text},
            )
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise _friendly_http_error(exc) from exc
            data = resp.json()
            return data["data"][0]["embedding"]

    async def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            result = await self._embed_with_retry(batch)
            results.extend([item["embedding"] for item in result["data"]])
        return results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def _embed_with_retry(self, batch: list[str]) -> dict:
        config = await self._config()
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            resp = await client.post(
                config.api_url,
                headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
                json={"model": config.model, "input": batch},
            )
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise _friendly_http_error(exc) from exc
            return resp.json()


_embedding_client: EmbeddingClient | None = None


def get_embedding_client() -> EmbeddingClient:
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client
