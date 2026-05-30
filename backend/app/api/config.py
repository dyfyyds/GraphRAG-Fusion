from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db
from app.dependencies import require_admin
from app.schemas.config import ConfigOut, ConfigUpdate, ConfigBatchUpdate, ConfigSectionOut
from app.services import config_service
from app.core.runtime_config import mask_config_items

router = APIRouter(prefix="/api/config", tags=["系统配置"])


@router.get("", response_model=list[ConfigOut])
async def get_all_config(db: AsyncSession = Depends(get_db)):
    return mask_config_items(await config_service.get_all_config(db))


@router.get("/sections", response_model=list[ConfigSectionOut])
async def get_config_sections(db: AsyncSession = Depends(get_db)):
    sections = []
    for section_name in ["llm", "embedding", "retrieval", "parsing"]:
        items = await config_service.get_config_by_section(db, section_name)
        sections.append(ConfigSectionOut(section=section_name, items=mask_config_items(items)))
    return sections


@router.put("/{key}", response_model=ConfigOut)
async def update_config(key: str, body: ConfigUpdate, _admin: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return mask_config_items([await config_service.update_config(db, key, body.config_value)])[0]


@router.put("/batch/update", response_model=list[ConfigOut])
async def batch_update_config(body: ConfigBatchUpdate, _admin: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return mask_config_items(await config_service.batch_update_config(db, body.configs))


@router.get("/apikey-status")
async def get_api_key_status(db: AsyncSession = Depends(get_db)):
    """检查 API Key 是否已配置（数据库或环境变量）"""
    from app.config import get_settings
    from sqlalchemy import select
    from app.models.system_config import SystemConfig

    settings = get_settings()
    result = await db.execute(
        select(SystemConfig.config_key, SystemConfig.config_value)
        .where(SystemConfig.config_key.in_(["llm_api_key", "embedding_api_key"]))
    )
    db_keys = {row[0]: row[1] for row in result.fetchall()}

    llm_configured = bool(db_keys.get("llm_api_key") or settings.LLM_API_KEY)
    emb_configured = bool(db_keys.get("embedding_api_key") or settings.EMBEDDING_API_KEY)

    return {
        "llm_api_key_configured": llm_configured,
        "embedding_api_key_configured": emb_configured,
    }
