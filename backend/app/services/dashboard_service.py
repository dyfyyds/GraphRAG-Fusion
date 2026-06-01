import asyncio
from urllib.parse import urlparse

import httpx
from datetime import date, timedelta
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.chunk import Chunk
from app.models.user import User
from app.models.message import Message
from app.db.neo4j import get_neo4j_driver
from app.db.chroma import get_chroma_client
from app.core.embedding_client import _embedding_endpoints, _extract_embeddings
from app.core.runtime_config import (
    get_embedding_runtime_config,
    get_llm_runtime_config,
)


async def get_stats(db: AsyncSession) -> dict:
    doc_count = (await db.execute(select(func.count()).select_from(Document))).scalar() or 0
    chunk_count = (await db.execute(select(func.count()).select_from(Chunk))).scalar() or 0
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    today = date.today()
    today_count = (
        await db.execute(
            select(func.count()).select_from(Message).where(
                cast(Message.created_at, Date) == today, Message.role == "user"
            )
        )
    ).scalar() or 0
    return {
        "document_count": doc_count,
        "chunk_count": chunk_count,
        "user_count": user_count,
        "today_chat_count": today_count,
    }


async def get_trend(db: AsyncSession, days: int = 7) -> list[dict]:
    today = date.today()
    results = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        count = (
            await db.execute(
                select(func.count()).select_from(Message).where(
                    cast(Message.created_at, Date) == d, Message.role == "user"
                )
            )
        ).scalar() or 0
        results.append({"date": d.isoformat(), "count": count})
    return results


async def get_hot_questions(db: AsyncSession, limit: int = 10) -> list[dict]:
    result = await db.execute(
        select(Message.content, func.count().label("cnt"))
        .where(Message.role == "user")
        .group_by(Message.content)
        .order_by(func.count().desc())
        .limit(limit)
    )
    return [{"question": row[0], "count": row[1]} for row in result.all()]


async def get_doc_types(db: AsyncSession) -> list[dict]:
    """Return document counts grouped by file_type with percentage."""
    total = (await db.execute(select(func.count()).select_from(Document))).scalar() or 0
    if total == 0:
        return []
    result = await db.execute(
        select(Document.file_type, func.count().label("cnt"))
        .group_by(Document.file_type)
        .order_by(func.count().desc())
    )
    rows = result.all()
    return [
        {"file_type": row[0], "count": row[1], "percentage": round(row[1] / total * 100, 1)}
        for row in rows
    ]


async def get_system_health() -> list[dict]:
    """Check health of each dependent service."""
    services = []

    # MySQL — if we got here, it's working
    services.append({"name": "MySQL 数据库", "status": "online", "detail": "v8.0 | 端口: 3306"})

    # ChromaDB
    try:
        client = get_chroma_client()
        heartbeat = client.heartbeat()
        collections = client.list_collections()
        services.append({
            "name": "ChromaDB 向量库",
            "status": "online",
            "detail": f"端口: 8000 | 集合: {len(collections)}",
        })
    except Exception:
        services.append({"name": "ChromaDB 向量库", "status": "offline", "detail": "连接失败"})

    # Neo4j
    try:
        driver = await get_neo4j_driver()
        async with asyncio.timeout(2):
            async with driver.session() as session:
                result = await session.run("MATCH (n) RETURN count(n) AS cnt LIMIT 1")
                record = await result.single()
                node_count = record["cnt"] if record else 0
                result2 = await session.run("MATCH ()-[r]->() RETURN count(r) AS cnt LIMIT 1")
                record2 = await result2.single()
                rel_count = record2["cnt"] if record2 else 0
        services.append({
            "name": "Neo4j 图数据库",
            "status": "online",
            "detail": f"端口: 7474 | 节点: {node_count} | 关系: {rel_count}",
        })
    except Exception:
        services.append({"name": "Neo4j 图数据库", "status": "offline", "detail": "连接失败"})

    llm_status, embedding_status = await asyncio.gather(
        _check_llm_service(),
        _check_embedding_service(),
    )
    services.extend([llm_status, embedding_status])

    return services


def _safe_host(api_url: str) -> str:
    parsed = urlparse(api_url or "")
    return parsed.netloc or parsed.path.split("/")[0] or "未配置地址"


def _short_timeout(value: int | float, default: float = 3.0) -> float:
    try:
        return max(1.0, min(float(value), default))
    except (TypeError, ValueError):
        return default


def _health_item(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


async def _check_llm_service() -> dict:
    try:
        config = await get_llm_runtime_config()
    except Exception as exc:
        return _health_item("LLM 服务", "offline", str(exc))

    name = f"LLM 服务 ({config.model})"
    detail_prefix = f"{_safe_host(config.api_url)}"
    try:
        async with httpx.AsyncClient(timeout=_short_timeout(config.timeout)) as client:
            resp = await client.post(
                config.api_url,
                headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
                json={
                    "model": config.model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                    "temperature": 0,
                    "stream": False,
                },
            )
        if resp.status_code in (401, 403):
            return _health_item(name, "offline", f"{detail_prefix} | 认证失败")
        if resp.status_code == 404:
            return _health_item(name, "offline", f"{detail_prefix} | 接口或模型不存在")
        if resp.status_code == 429:
            return _health_item(name, "warning", f"{detail_prefix} | 额度不足或请求过快")
        if resp.status_code >= 400:
            return _health_item(name, "warning", f"{detail_prefix} | HTTP {resp.status_code}")
        data = resp.json()
        if not isinstance(data.get("choices"), list):
            return _health_item(name, "warning", f"{detail_prefix} | 返回格式异常")
        return _health_item(name, "online", f"{detail_prefix} | 连接正常")
    except (httpx.TimeoutException, httpx.NetworkError):
        return _health_item(name, "offline", f"{detail_prefix} | 连接超时")
    except Exception as exc:
        return _health_item(name, "warning", f"{detail_prefix} | {str(exc)[:80]}")


async def _check_embedding_service() -> dict:
    try:
        config = await get_embedding_runtime_config()
    except Exception as exc:
        return _health_item("Embedding 服务", "offline", str(exc))

    name = f"Embedding 服务 ({config.model})"
    detail_prefix = f"{_safe_host(config.api_url)} | 维度: {config.dimension}"
    last_404 = False
    try:
        async with httpx.AsyncClient(timeout=_short_timeout(config.timeout)) as client:
            for endpoint in _embedding_endpoints(config.api_url):
                resp = await client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
                    json={"model": config.model, "input": ["ping"]},
                )
                if resp.status_code == 404:
                    last_404 = True
                    continue
                if resp.status_code in (401, 403):
                    return _health_item(name, "offline", f"{detail_prefix} | 认证失败")
                if resp.status_code == 429:
                    return _health_item(name, "warning", f"{detail_prefix} | 额度不足或请求过快")
                if resp.status_code >= 400:
                    return _health_item(name, "warning", f"{detail_prefix} | HTTP {resp.status_code}")
                embeddings = _extract_embeddings(resp.json())
                if not embeddings:
                    return _health_item(name, "warning", f"{detail_prefix} | 返回格式异常")
                return _health_item(name, "online", f"{detail_prefix} | 连接正常")
        if last_404:
            return _health_item(name, "warning", f"{detail_prefix} | Embedding 接口或模型不存在")
        return _health_item(name, "offline", f"{detail_prefix} | 未配置接口地址")
    except (httpx.TimeoutException, httpx.NetworkError):
        return _health_item(name, "offline", f"{detail_prefix} | 连接超时")
    except Exception as exc:
        return _health_item(name, "warning", f"{detail_prefix} | {str(exc)[:80]}")
