from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.db.mysql import engine
from app.db.neo4j import get_neo4j_driver, close_neo4j
from app.db.chroma import get_chroma_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：初始化连接池
    get_chroma_client()
    await get_neo4j_driver()
    yield
    # 关闭：释放资源
    await engine.dispose()
    await close_neo4j()
