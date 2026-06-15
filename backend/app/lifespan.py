import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.db.mysql import engine
from app.db.neo4j import get_neo4j_driver, close_neo4j, ensure_graph_indexes
from app.db.chroma import get_chroma_client

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：初始化连接池 + 图谱索引
    get_chroma_client()
    await get_neo4j_driver()
    await ensure_graph_indexes()

    # 启动时清理孤儿数据（MySQL 已删除但 Neo4j/ChromaDB 残留的数据）
    try:
        from app.db.mysql import async_session
        from app.services.document_service import cleanup_orphaned_data
        async with async_session() as db:
            result = await cleanup_orphaned_data(db)
            if result.get("success"):
                logger.info(f"启动时孤儿数据清理完成: 现有文档 {result['existing_docs']} 个")
            else:
                logger.warning(f"启动时孤儿数据清理失败: {result.get('warnings')}")
    except Exception as e:
        logger.warning(f"启动时孤儿数据清理异常（不影响启动）: {e}")

    yield
    # 关闭：释放资源
    await engine.dispose()
    await close_neo4j()
