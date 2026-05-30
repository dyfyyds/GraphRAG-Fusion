from neo4j import AsyncGraphDatabase, AsyncDriver
from app.config import get_settings

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


async def close_neo4j():
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
