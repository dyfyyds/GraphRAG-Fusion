import httpx
import asyncio
import hashlib
import logging
import math

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.runtime_config import get_embedding_runtime_config, EmbeddingRuntimeConfig

logger = logging.getLogger("app")


def _friendly_http_error(exc: httpx.HTTPStatusError) -> ValueError:
    status = exc.response.status_code
    if status in (401, 403):
        return ValueError("Embedding 服务认证失败，请检查 Embedding API Key。")
    if status == 404:
        return ValueError("Embedding 服务接口或模型不存在，请检查 API Base URL 和模型名称。")
    if status == 429:
        return ValueError("Embedding 服务请求过于频繁或额度不足，请稍后重试。")
    return ValueError(f"Embedding 服务返回错误 HTTP {status}，请检查模型配置。")


def _embedding_endpoints(api_url: str) -> list[str]:
    normalized = (api_url or "").strip().rstrip("/")
    if not normalized:
        return []

    endpoints = [normalized]
    if normalized.endswith("/chat/completions"):
        endpoints.append(normalized[: -len("/chat/completions")] + "/embeddings")
    if normalized.endswith("/embeddings"):
        base = normalized[: -len("/embeddings")]
        if not base.endswith("/v1"):
            endpoints.append(f"{base}/v1/embeddings")
        elif base.endswith("/v1"):
            endpoints.append(f"{base[: -len('/v1')]}/embeddings")
    else:
        endpoints.append(f"{normalized}/embeddings")
        endpoints.append(f"{normalized}/v1/embeddings")

    deduped = []
    for endpoint in endpoints:
        if endpoint and endpoint not in deduped:
            deduped.append(endpoint)
    return deduped


def _extract_embeddings(data: dict) -> list[list[float]]:
    if isinstance(data.get("data"), list):
        embeddings = []
        for item in data["data"]:
            if isinstance(item, dict) and isinstance(item.get("embedding"), list):
                embeddings.append(item["embedding"])
            elif isinstance(item, list):
                embeddings.append(item)
        if embeddings:
            return embeddings

    if isinstance(data.get("embeddings"), list):
        embeddings = data["embeddings"]
        if embeddings and isinstance(embeddings[0], (int, float)):
            return [embeddings]
        return embeddings

    if isinstance(data.get("embedding"), list):
        return [data["embedding"]]

    nested = data.get("data")
    if isinstance(nested, dict) and isinstance(nested.get("embedding"), list):
        return [nested["embedding"]]

    raise ValueError("Embedding 服务返回格式异常，请检查接口是否兼容 OpenAI Embeddings 格式。")


def _local_compat_embedding(text: str, dimension: int) -> list[float]:
    """Deterministic feature-hash embedding for chat-only providers without embeddings endpoint."""
    dimension = max(128, int(dimension or 1024))
    vector = [0.0] * dimension
    tokens = _tokenize_for_hash_embedding(text)
    if not tokens:
        tokens = [text or "empty"]

    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        idx = int.from_bytes(digest[:8], "big") % dimension
        sign = 1.0 if digest[8] % 2 == 0 else -1.0
        vector[idx] += sign

    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _tokenize_for_hash_embedding(text: str) -> list[str]:
    text = (text or "").strip()
    tokens = []
    for i, char in enumerate(text):
        if char.isspace():
            continue
        tokens.append(char)
        if i + 1 < len(text) and not text[i + 1].isspace():
            tokens.append(text[i : i + 2])
    return tokens


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
        embeddings = await self._request_embeddings(config, [text])
        return embeddings[0]

    async def embed_batch(self, texts: list[str], batch_size: int | None = None) -> list[list[float]]:
        config = await self._config()
        batch_size = max(1, int(batch_size or config.batch_size))
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            result = await self._embed_with_retry(batch)
            results.extend(result)
        return results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def _embed_with_retry(self, batch: list[str]) -> list[list[float]]:
        config = await self._config()
        return await self._request_embeddings(config, batch)

    async def _request_embeddings(self, config: EmbeddingRuntimeConfig, inputs: list[str]) -> list[list[float]]:
        last_404 = None
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            for endpoint in _embedding_endpoints(config.api_url):
                resp = await client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
                    json={"model": config.model, "input": inputs},
                )
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 404:
                        last_404 = exc
                        continue
                    raise _friendly_http_error(exc) from exc
                embeddings = _extract_embeddings(resp.json())
                if len(embeddings) != len(inputs):
                    raise ValueError("Embedding 服务返回数量与输入数量不一致，请检查模型配置。")
                return embeddings

        if last_404:
            logger.warning(
                "Embedding endpoint not found for model %s, using local compatibility embeddings.",
                config.model,
            )
            return [_local_compat_embedding(text, config.dimension) for text in inputs]
        raise ValueError("Embedding API Base URL 未配置，请在系统配置中填写。")


_embedding_client: EmbeddingClient | None = None


def get_embedding_client() -> EmbeddingClient:
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client
