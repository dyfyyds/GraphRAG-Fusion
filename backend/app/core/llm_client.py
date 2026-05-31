import httpx
import asyncio
import json
from typing import AsyncGenerator

from app.core.runtime_config import get_llm_runtime_config, LLMRuntimeConfig


def _friendly_http_error(exc: httpx.HTTPStatusError) -> str:
    status = exc.response.status_code
    if status in (401, 403):
        return "AI 服务认证失败，请检查 LLM API Key。"
    if status == 404:
        return "AI 服务接口或模型不存在，请检查 LLM API Base URL 和模型名称。"
    if status == 429:
        return "AI 服务请求过于频繁或额度不足，请稍后重试。"
    return f"AI 服务返回错误 HTTP {status}，请检查模型配置。"


class LLMClient:
    async def _config(self) -> LLMRuntimeConfig:
        return await get_llm_runtime_config()

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        timeout: int | None = None,
        retries: int = 3,
        no_timeout: bool = False,
    ) -> str:
        config = await self._config()
        attempts = max(1, retries)
        client_timeout = None if no_timeout else (timeout if timeout is not None else config.timeout)
        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(timeout=client_timeout) as client:
                    resp = await client.post(
                        config.api_url,
                        headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
                        json={
                            "model": config.model,
                            "messages": messages,
                            "temperature": temperature,
                            "top_p": config.top_p,
                            "max_tokens": config.max_tokens,
                            "stream": False,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt >= attempts - 1:
                    raise
                await asyncio.sleep(min(10, 2 ** attempt))

    async def chat_stream(self, messages: list[dict], temperature: float = 0.7) -> AsyncGenerator[str, None]:
        attempt = 0
        while attempt < 3:
            try:
                config = await self._config()
                async with httpx.AsyncClient(timeout=config.timeout) as client:
                    async with client.stream(
                        "POST",
                        config.api_url,
                        headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
                        json={
                            "model": config.model,
                            "messages": messages,
                            "temperature": temperature,
                            "top_p": config.top_p,
                            "max_tokens": config.max_tokens,
                            "stream": True,
                        },
                    ) as resp:
                        resp.raise_for_status()
                        async for line in resp.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            payload = line[6:]
                            if payload.strip() == "[DONE]":
                                return
                            chunk = json.loads(payload)
                            choices = chunk.get("choices", [])
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                return
            except ValueError as exc:
                yield str(exc)
                return
            except httpx.HTTPStatusError as exc:
                yield _friendly_http_error(exc)
                return
            except (KeyError, json.JSONDecodeError):
                yield "AI 服务返回格式异常，请检查模型是否兼容 OpenAI Chat Completions 接口。"
                return
            except (httpx.TimeoutException, httpx.NetworkError):
                attempt += 1
                if attempt >= 3:
                    yield "抱歉，AI服务暂时不可用，请稍后重试。"
                    return
                await asyncio.sleep(2 ** attempt)


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
