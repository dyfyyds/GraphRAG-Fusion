import time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig
from app.exceptions import NotFoundError

_cache: dict = {}
_cache_time: float = 0
CACHE_TTL = 60

# Section-to-key-prefix mapping used to group config keys into logical sections
SECTION_PREFIXES: dict[str, list[str]] = {
    "llm": ["llm_model", "llm_config", "llm_api_key", "kg_config", "model_profiles"],
    "embedding": ["embedding_model"],
    "retrieval": ["retrieval_config"],
    "parsing": ["chunk_config", "upload_config"],
    "system": [],  # virtual section — health info, not config keys
}


async def get_all_config(db: AsyncSession) -> list[SystemConfig]:
    global _cache, _cache_time
    now = time.time()
    if _cache and now - _cache_time < CACHE_TTL:
        return list(_cache.values())

    result = await db.execute(select(SystemConfig))
    configs = list(result.scalars().all())
    _cache = {c.config_key: c for c in configs}
    _cache_time = now
    return configs


async def get_config_by_section(db: AsyncSession, section: str) -> list[SystemConfig]:
    """Return configs filtered by section name."""
    all_configs = await get_all_config(db)
    prefixes = SECTION_PREFIXES.get(section, [])
    if not prefixes:
        return []
    return [c for c in all_configs if c.config_key in prefixes]


async def update_config(db: AsyncSession, key: str, value: str) -> SystemConfig:
    global _cache
    result = await db.execute(select(SystemConfig).where(SystemConfig.config_key == key))
    config = result.scalar_one_or_none()
    if not config:
        config = SystemConfig(config_key=key, config_value=value, description=f"Auto-created: {key}")
        db.add(config)
    else:
        config.config_value = value
    await db.commit()
    await db.refresh(config)
    _cache.pop(key, None)
    return config


async def batch_update_config(db: AsyncSession, configs: dict[str, str]) -> list[SystemConfig]:
    """Update multiple config keys at once."""
    global _cache
    updated = []
    for key, value in configs.items():
        result = await db.execute(select(SystemConfig).where(SystemConfig.config_key == key))
        config = result.scalar_one_or_none()
        if config:
            config.config_value = value
            _cache.pop(key, None)
            updated.append(config)
    await db.commit()
    for c in updated:
        await db.refresh(c)
    return updated
