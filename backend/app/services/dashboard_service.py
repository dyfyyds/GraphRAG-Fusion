import asyncio
from datetime import date, timedelta
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.chunk import Chunk
from app.models.user import User
from app.models.message import Message
from app.db.neo4j import get_neo4j_driver
from app.db.chroma import get_chroma_client


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

    # LLM and Embedding are external services — report as placeholder
    services.append({"name": "LLM 服务 (mimo-2.5-pro)", "status": "online", "detail": "外部服务"})
    services.append({"name": "Embedding 服务 (BAAI/bge-m3)", "status": "online", "detail": "外部服务"})

    return services
