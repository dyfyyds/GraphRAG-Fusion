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


@router.post("/fetch-models")
async def fetch_models(body: dict, db: AsyncSession = Depends(get_db)):
    """从 OpenAI 兼容 API 获取可用模型列表"""
    import json as _json
    import httpx
    from sqlalchemy import select
    from app.models.system_config import SystemConfig
    from app.config import get_settings

    api_url = body.get("api_url", "").strip().rstrip("/")
    api_key = body.get("api_key", "").strip()
    model_type = body.get("model_type", "llm")  # llm 或 embedding
    profile_id = body.get("profile_id", "").strip()
    use_saved_key = bool(body.get("use_saved_key", False))

    if not api_url:
        return {"models": [], "error": "请填写 API Base URL"}

    def _strip_known_suffix(value: str) -> str:
        normalized = (value or "").strip().rstrip("/")
        for suffix in ["/chat/completions", "/embeddings", "/models"]:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].rstrip("/")
        return normalized

    def _same_api_base(left: str, right: str) -> bool:
        left_base = _strip_known_suffix(left)
        right_base = _strip_known_suffix(right)
        if left_base == right_base:
            return True
        # DeepSeek 官方 base_url 是 https://api.deepseek.com，同时兼容 /v1。
        deepseek_aliases = {"https://api.deepseek.com", "https://api.deepseek.com/v1"}
        return left_base in deepseek_aliases and right_base in deepseek_aliases

    def _is_deepseek_url(value: str) -> bool:
        return "api.deepseek.com" in (value or "").lower()

    async def _resolve_saved_api_key() -> str:
        if not use_saved_key:
            return ""
        settings = get_settings()
        result = await db.execute(
            select(SystemConfig.config_key, SystemConfig.config_value)
        )
        all_configs = {row[0]: row[1] for row in result.fetchall()}

        def _profile_key_ref(target_profile_id: str) -> str:
            return f"{model_type}_profile_{target_profile_id}_api_key" if target_profile_id else ""

        # 读取 model_profiles 找到当前类型配置的 api_key_ref
        profiles_raw = all_configs.get("model_profiles", "[]")
        try:
            profiles = _json.loads(profiles_raw)
        except Exception:
            profiles = []

        if profile_id:
            selected_profile = next((p for p in profiles if p.get("id") == profile_id), None)
            # 只有当前请求 URL 与当前 profile URL 一致时，才复用该 profile 的保存 Key。
            # 避免把 Mimo 等旧配置的 Key 发送给 DeepSeek 造成 401。
            if selected_profile and _same_api_base(selected_profile.get("api_url", ""), api_url):
                return all_configs.get(_profile_key_ref(profile_id), "")
        else:
            # 未传 profile_id 时，兼容旧前端：匹配 model_type 和 api_url 的 profile，找到对应 Key
            for p in profiles:
                if p.get("type") == model_type and _same_api_base(p.get("api_url", ""), api_url):
                    saved_key = all_configs.get(_profile_key_ref(p.get("id", "")), "")
                    if saved_key:
                        return saved_key

            # 兜底：环境变量
            env_url = settings.LLM_API_URL if model_type == "llm" else settings.EMBEDDING_API_URL
            env_key = settings.LLM_API_KEY if model_type == "llm" else settings.EMBEDDING_API_KEY
            if _same_api_base(env_url, api_url):
                return env_key
        return ""

    # 构建 /v1/models 端点
    models_url = api_url
    if not models_url.endswith("/models"):
        for suffix in ["/chat/completions", "/embeddings"]:
            if models_url.endswith(suffix):
                models_url = models_url[: -len(suffix)]
                break
        models_url = f"{models_url}/models"

    async def _request_models(client: httpx.AsyncClient, key: str = "") -> dict:
        headers = {"Accept": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        resp = await client.get(models_url, headers=headers)
        resp.raise_for_status()
        return resp.json()

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                data = await _request_models(client)
            except httpx.HTTPStatusError as e:
                if e.response.status_code not in (401, 403):
                    raise
                retry_key = api_key or await _resolve_saved_api_key()
                if not retry_key:
                    raise
                data = await _request_models(client, retry_key)

        model_list = data.get("data", [])
        models = []
        for item in model_list:
            model_id = item.get("id", "")
            if model_id:
                models.append(model_id)

        models.sort()
        return {"models": models, "error": None}
    except httpx.TimeoutException:
        return {"models": [], "error": "请求超时，请检查 API 地址是否正确"}
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 403) and _is_deepseek_url(api_url):
            return {
                "models": [],
                "error": "DeepSeek API Key 无效。请确认使用的是 DeepSeek 平台生成的 API Key，并且不是 Mimo/OpenRouter/网页登录 Token。",
            }
        if e.response.status_code in (401, 403):
            return {"models": [], "error": "该服务的模型列表需要 API Key，请填写当前 API 地址对应的 Key 后重试"}
        return {"models": [], "error": f"API 返回错误: {e.response.status_code} - {e.response.text[:200]}"}
    except Exception as e:
        return {"models": [], "error": f"获取模型列表失败: {str(e)}"}
