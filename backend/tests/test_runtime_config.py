import json
from types import SimpleNamespace

import pytest

from app.core.runtime_config import (
    mask_config_items,
    parse_embedding_config,
    parse_llm_config,
)


def test_parse_llm_config_prefers_database_values_and_falls_back_to_settings():
    settings = SimpleNamespace(
        LLM_API_URL="https://env-llm.example/v1",
        LLM_API_KEY="env-llm-key",
        LLM_MODEL="env-model",
        LLM_TIMEOUT=60,
    )
    raw = {
        "llm_config": json.dumps({
            "api_url": "https://db-llm.example/v1",
            "model": "db-model",
            "temperature": 0.3,
            "max_tokens": 2048,
        }),
        "llm_api_key": "db-llm-key",
    }

    config = parse_llm_config(raw, settings)

    assert config.api_url == "https://db-llm.example/v1/chat/completions"
    assert config.api_key == "db-llm-key"
    assert config.model == "db-model"
    assert config.temperature == 0.3
    assert config.max_tokens == 2048
    assert config.timeout == 60


def test_parse_embedding_config_prefers_database_values_and_falls_back_to_settings():
    settings = SimpleNamespace(
        EMBEDDING_API_URL="https://env-embedding.example/v1",
        EMBEDDING_API_KEY="env-embedding-key",
        EMBEDDING_MODEL="env-embedding",
        EMBEDDING_DIM=1024,
        EMBEDDING_TIMEOUT=30,
    )
    raw = {
        "embedding_model": json.dumps({
            "api_url": "https://db-embedding.example/v1",
            "model": "db-embedding",
            "dimension": 768,
        }),
        "embedding_api_key": "db-embedding-key",
    }

    config = parse_embedding_config(raw, settings)

    assert config.api_url == "https://db-embedding.example/v1/embeddings"
    assert config.api_key == "db-embedding-key"
    assert config.model == "db-embedding"
    assert config.dimension == 768
    assert config.timeout == 30


def test_mask_config_items_hides_api_keys_without_mutating_originals():
    item = SimpleNamespace(
        id=1,
        config_key="llm_api_key",
        config_value="sk-secret-value",
        description="LLM key",
    )

    masked = mask_config_items([item])

    assert masked[0].config_value == "********"
    assert item.config_value == "sk-secret-value"


def test_parse_llm_config_requires_api_url_and_key():
    settings = SimpleNamespace(
        LLM_API_URL="",
        LLM_API_KEY="",
        LLM_MODEL="mimo-v2.5-pro",
        LLM_TIMEOUT=60,
    )

    with pytest.raises(ValueError, match="LLM API Base URL"):
        parse_llm_config({}, settings)


def test_with_suffix_does_not_double_append():
    from app.core.runtime_config import _with_suffix

    assert _with_suffix("https://api.openai.com/v1", "/chat/completions") == "https://api.openai.com/v1/chat/completions"
    assert _with_suffix("https://api.openai.com/v1/chat/completions", "/chat/completions") == "https://api.openai.com/v1/chat/completions"
    assert _with_suffix("https://api.openai.com/v1/chat/completions/", "/chat/completions") == "https://api.openai.com/v1/chat/completions"
    assert _with_suffix("https://api.example.com/v1", "/embeddings") == "https://api.example.com/v1/embeddings"
    assert _with_suffix("https://api.example.com/v1/embeddings", "/embeddings") == "https://api.example.com/v1/embeddings"
    assert _with_suffix("", "/chat/completions") == ""
    assert _with_suffix(None, "/chat/completions") == ""
