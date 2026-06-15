"""限流中间件测试：验证专属路径限额不被全局限额误伤。

复现 bug：上传接口配置了 200 次/分钟的专属限额，但全局限额仅 100 次/分钟，
且全局限额先于专属限额检查并消耗配额，导致上传超过 100 次后被全局限流拦截，
大批量上传时部分文件失败后不再上传。
"""
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.middleware.rate_limit import RateLimitMiddleware


def _build_app() -> FastAPI:
    """构造仅含限流中间件的最小应用，隔离 DB / 鉴权等依赖。"""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.post("/api/documents/upload")
    async def _upload():
        return {"ok": True}

    @app.get("/api/health")
    async def _health():
        return {"status": "ok"}

    return app


async def _fire(app: FastAPI, method: str, path: str, count: int, ip: str = "9.9.9.9"):
    transport = ASGITransport(app=app)
    statuses = []
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(count):
            resp = await client.request(method, path, headers={"X-Forwarded-For": ip})
            statuses.append(resp.status_code)
    return statuses


@pytest.mark.asyncio
async def test_upload_not_blocked_by_global_limit():
    """上传专属限额 200/分钟，150 次连续上传不应被全局 100/分钟 限额提前拦截。"""
    app = _build_app()
    statuses = await _fire(app, "POST", "/api/documents/upload", 150)
    throttled = [s for s in statuses if s == 429]
    assert throttled == [], f"150 次上传(<200 限额)不应出现 429，实际被限流 {len(throttled)} 次"


@pytest.mark.asyncio
async def test_upload_path_limit_still_enforced():
    """超过上传专属限额 200 后仍应限流（前 200 放行，其余 429）。"""
    app = _build_app()
    statuses = await _fire(app, "POST", "/api/documents/upload", 230)
    assert statuses[:200].count(429) == 0, "前 200 次上传不应被限流"
    assert 429 in statuses[200:], "超过 200 次上传后应触发限流"


@pytest.mark.asyncio
async def test_global_limit_still_applies_to_unconfigured_paths():
    """无专属配置的接口仍受全局 100/分钟 限额保护。"""
    app = _build_app()
    statuses = await _fire(app, "GET", "/api/health", 150)
    assert 429 in statuses, "无专属配置的接口超过全局限额后应被限流"
