import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from app.config import get_settings
from app.db.mysql import async_session
from app.models.system_config import SystemConfig
from app.schemas.config import ConfigOut


MASKED_VALUE = "********"


@dataclass(frozen=True)
class LLMRuntimeConfig:
    api_url: str
    api_key: str
    model: str
    temperature: float
    top_p: float
    max_tokens: int
    timeout: int


@dataclass(frozen=True)
class EmbeddingRuntimeConfig:
    api_url: str
    api_key: str
    model: str
    dimension: int
    timeout: int


def _json_value(raw: dict[str, str], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _with_suffix(base_url: str, suffix: str) -> str:
    normalized = (base_url or "").strip().rstrip("/")
    if not normalized:
        return ""
    if normalized.endswith(suffix):
        return normalized
    suffix_stripped = suffix.lstrip("/")
    if normalized.endswith(suffix_stripped):
        return normalized
    return f"{normalized}{suffix}"


def _require(value: str, message: str) -> str:
    if not value:
        raise ValueError(message)
    return value


def parse_llm_config(raw: dict[str, str], settings=None) -> LLMRuntimeConfig:
    settings = settings or get_settings()
    llm_config = _json_value(raw, "llm_config")
    legacy_llm_model = _json_value(raw, "llm_model")
    if legacy_llm_model and not llm_config:
        llm_config = legacy_llm_model
    api_url = llm_config.get("api_url") or raw.get("llm_api_url") or settings.LLM_API_URL
    api_key = raw.get("llm_api_key") or settings.LLM_API_KEY
    model = llm_config.get("model") or (raw.get("llm_model") if not legacy_llm_model else None) or settings.LLM_MODEL

    return LLMRuntimeConfig(
        api_url=_with_suffix(_require(api_url, "LLM API Base URL 未配置，请在系统配置中填写。"), "/chat/completions"),
        api_key=_require(api_key, "LLM API Key 未配置，请在系统配置中填写。"),
        model=model,
        temperature=float(llm_config.get("temperature", 0.7)),
        top_p=float(llm_config.get("top_p", 0.9)),
        max_tokens=int(llm_config.get("max_tokens", 2048)),
        timeout=int(getattr(settings, "LLM_TIMEOUT", 60)),
    )


def parse_embedding_config(raw: dict[str, str], settings=None) -> EmbeddingRuntimeConfig:
    settings = settings or get_settings()
    embedding_config = _json_value(raw, "embedding_model")
    api_url = embedding_config.get("api_url") or raw.get("embedding_api_url") or settings.EMBEDDING_API_URL
    api_key = raw.get("embedding_api_key") or settings.EMBEDDING_API_KEY
    model = embedding_config.get("model") or settings.EMBEDDING_MODEL

    return EmbeddingRuntimeConfig(
        api_url=_with_suffix(_require(api_url, "Embedding API Base URL 未配置，请在系统配置中填写。"), "/embeddings"),
        api_key=_require(api_key, "Embedding API Key 未配置，请在系统配置中填写。"),
        model=model,
        dimension=int(embedding_config.get("dimension", settings.EMBEDDING_DIM)),
        timeout=int(getattr(settings, "EMBEDDING_TIMEOUT", 30)),
    )


async def load_raw_runtime_config() -> dict[str, str]:
    async with async_session() as db:
        result = await db.execute(select(SystemConfig))
        return {item.config_key: item.config_value for item in result.scalars().all()}


async def get_llm_runtime_config() -> LLMRuntimeConfig:
    return parse_llm_config(await load_raw_runtime_config())


async def get_embedding_runtime_config() -> EmbeddingRuntimeConfig:
    return parse_embedding_config(await load_raw_runtime_config())


def mask_config_items(items) -> list[ConfigOut]:
    masked = []
    for item in items:
        value = item.config_value
        if item.config_key.endswith("_api_key") and value:
            value = MASKED_VALUE
        masked.append(
            ConfigOut(
                id=item.id,
                config_key=item.config_key,
                config_value=value,
                description=item.description,
            )
        )
    return masked
