import logging

from neo4j import AsyncGraphDatabase, AsyncDriver
from app.config import get_settings

logger = logging.getLogger("app")

_driver: AsyncDriver | None = None


async def get_neo4j_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        settings = get_settings()
        _driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _driver


async def ensure_graph_indexes():
    """启动时创建图谱索引（幂等）。

    - TEXT 索引：加速实体名/同义词的 CONTAINS 模糊检索（图谱检索主路径）
    - RANGE 索引：加速按 document_id 的等值清理与统计
    知识库规模增大后，无索引的全图扫描是检索延迟的主要来源之一。
    """
    driver = await get_neo4j_driver()
    statements = (
        "CREATE TEXT INDEX entity_name_text_idx IF NOT EXISTS FOR (n:Entity) ON (n.name)",
        "CREATE INDEX entity_document_idx IF NOT EXISTS FOR (n:Entity) ON (n.document_id)",
        "CREATE TEXT INDEX synonym_original_text_idx IF NOT EXISTS FOR (s:Synonym) ON (s.original)",
        "CREATE TEXT INDEX synonym_synonym_text_idx IF NOT EXISTS FOR (s:Synonym) ON (s.synonym)",
    )
    try:
        async with driver.session() as session:
            for stmt in statements:
                await session.run(stmt)
        logger.info("Neo4j 图谱索引已就绪")
    except Exception as exc:
        logger.warning(f"创建 Neo4j 索引失败（不影响功能，仅影响性能）: {exc}")


async def close_neo4j():
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
