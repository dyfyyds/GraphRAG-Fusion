import asyncio
import logging

from app.db.neo4j import get_neo4j_driver

logger = logging.getLogger("app")


async def search_entities(query: str, limit: int = 20, entity_type: str | None = None) -> list[dict]:
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(10):
            async with driver.session() as session:
                if query and entity_type:
                    result = await session.run(
                        "MATCH (e) WHERE e.name CONTAINS $q AND e.type = $etype RETURN elementId(e) AS eid, e.name AS name, e.type AS type, e.description AS description LIMIT $limit",
                        q=query, etype=entity_type, limit=limit,
                    )
                elif query:
                    result = await session.run(
                        "MATCH (e) WHERE e.name CONTAINS $q RETURN elementId(e) AS eid, e.name AS name, e.type AS type, e.description AS description LIMIT $limit",
                        q=query, limit=limit,
                    )
                elif entity_type:
                    result = await session.run(
                        "MATCH (e) WHERE e.type = $etype RETURN elementId(e) AS eid, e.name AS name, e.type AS type, e.description AS description LIMIT $limit",
                        etype=entity_type, limit=limit,
                    )
                else:
                    result = await session.run(
                        "MATCH (e) RETURN elementId(e) AS eid, e.name AS name, e.type AS type, e.description AS description LIMIT $limit",
                        limit=limit,
                    )
                records = await result.data()
                return [{"id": r["eid"], "name": r.get("name") or "", "type": r.get("type") or "", "description": r.get("description") or ""} for r in records]
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"search_entities error: {e}")
        return []


async def search_entity_context(query: str, limit: int = 5) -> list[dict]:
    """Search matching entities and return their direct relationships for answer citations."""
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(10):
            async with driver.session() as session:
                result = await session.run(
                    """
                    MATCH (e)
                    WHERE e.name CONTAINS $q
                    OPTIONAL MATCH (e)-[out]->(out_node)
                    OPTIONAL MATCH (in_node)-[in_rel]->(e)
                    RETURN
                        elementId(e) AS eid,
                        e.name AS name,
                        e.type AS type,
                        e.description AS description,
                        collect(DISTINCT {
                            source: e.name,
                            target: out_node.name,
                            relation_type: out.rel_type
                        }) AS outgoing,
                        collect(DISTINCT {
                            source: in_node.name,
                            target: e.name,
                            relation_type: in_rel.rel_type
                        }) AS incoming
                    LIMIT $limit
                    """,
                    q=query,
                    limit=limit,
                )
                records = await result.data()
                items = []
                for record in records:
                    relations = []
                    for rel in (record.get("outgoing") or []) + (record.get("incoming") or []):
                        if rel.get("source") and rel.get("target") and rel.get("relation_type"):
                            relations.append({
                                "source": rel["source"],
                                "target": rel["target"],
                                "relation_type": rel["relation_type"],
                            })
                    items.append({
                        "id": record["eid"],
                        "name": record.get("name") or "",
                        "type": record.get("type") or "",
                        "description": record.get("description") or "",
                        "relations": relations,
                    })
                return items
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"search_entity_context error: {e}")
        return []


async def get_relations(limit: int = 100) -> list[dict]:
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(10):
            async with driver.session() as session:
                result = await session.run(
                    "MATCH (a)-[r]->(b) RETURN elementId(a) AS source_id, a.name AS source, elementId(b) AS target_id, b.name AS target, r.rel_type AS relation_type LIMIT $limit",
                    limit=limit,
                )
                records = await result.data()
                return records
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"get_relations error: {e}")
        return []


async def create_entity(name: str, entity_type: str, description: str = "") -> dict | None:
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(2):
            async with driver.session() as session:
                props = {"name": name, "type": entity_type}
                if description:
                    props["description"] = description
                result = await session.run(
                    "CREATE (e:Entity $props) RETURN e",
                    props=props,
                )
                record = await result.single()
                if record:
                    node = record["e"]
                    result_dict = {"id": node.element_id, "name": name, "type": entity_type}
                    if description:
                        result_dict["description"] = description
                    return result_dict
        return None
    except (asyncio.TimeoutError, Exception):
        return None


async def update_entity(entity_id: str, name: str | None = None, entity_type: str | None = None, description: str | None = None) -> bool:
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(2):
            async with driver.session() as session:
                set_clauses = []
                params = {"eid": entity_id}
                if name is not None:
                    set_clauses.append("e.name = $name")
                    params["name"] = name
                if entity_type is not None:
                    set_clauses.append("e.type = $etype")
                    params["etype"] = entity_type
                if description is not None:
                    set_clauses.append("e.description = $desc")
                    params["desc"] = description
                if not set_clauses:
                    return True
                set_str = ", ".join(set_clauses)
                await session.run(
                    f"MATCH (e) WHERE elementId(e) = $eid SET {set_str}",
                    **params,
                )
                return True
    except (asyncio.TimeoutError, Exception):
        return False


async def delete_entity(entity_id: str) -> bool:
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(2):
            async with driver.session() as session:
                await session.run(
                    "MATCH (e) WHERE elementId(e) = $eid DETACH DELETE e",
                    eid=entity_id,
                )
                return True
    except (asyncio.TimeoutError, Exception):
        return False


async def create_relation(source: str, target: str, relation_type: str, description: str = "") -> dict | None:
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(2):
            async with driver.session() as session:
                # Neo4j 关系类型只允许 ASCII，所以统一用 RELATES，实际类型存为属性
                props = {"rel_type": relation_type}
                if description:
                    props["description"] = description
                # 支持通过 name 或 elementId 匹配实体
                result = await session.run(
                    "MATCH (a), (b) WHERE "
                    "(a.name = $source OR elementId(a) = $source) AND "
                    "(b.name = $target OR elementId(b) = $target) "
                    "CREATE (a)-[r:RELATES $props]->(b) RETURN r, a.name AS a_name, b.name AS b_name",
                    source=source, target=target, props=props,
                )
                record = await result.single()
                if record:
                    return {"source": record["a_name"] or source, "target": record["b_name"] or target, "relation_type": relation_type}
        return None
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"创建关系失败: {e}")
        return None


async def delete_relation(source: str, target: str, relation_type: str) -> bool:
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(2):
            async with driver.session() as session:
                await session.run(
                    "MATCH (a)-[r:RELATES]->(b) WHERE "
                    "(a.name = $source OR elementId(a) = $source) AND "
                    "(b.name = $target OR elementId(b) = $target) AND "
                    "r.rel_type = $rel_type DELETE r",
                    source=source, target=target, rel_type=relation_type,
                )
                return True
    except (asyncio.TimeoutError, Exception):
        return False


async def delete_by_document(document_id: int) -> dict:
    """删除文档关联的知识图谱节点，返回各步骤执行结果"""
    result = {"neo4j": False, "error": None}
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(5):
            async with driver.session() as session:
                await session.run(
                    "MATCH (e:Entity) WHERE e.document_id = $doc_id DETACH DELETE e",
                    doc_id=document_id,
                )
                result["neo4j"] = True
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"删除文档 {document_id} 的图谱节点失败: {e}")
        result["error"] = str(e)
    return result


async def delete_all_entities() -> dict:
    """清空 Neo4j 所有节点和关系"""
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(10):
            async with driver.session() as session:
                await session.run("MATCH (n) DETACH DELETE n")
                return {"success": True, "message": "已清空所有图谱节点"}
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"清空Neo4j失败: {e}")
        return {"success": False, "message": str(e)}


async def get_graph_stats() -> dict:
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(2):
            async with driver.session() as session:
                nodes = await session.run("MATCH (n) RETURN count(n) AS cnt")
                rels = await session.run("MATCH ()-[r]->() RETURN count(r) AS cnt")
                node_count = (await nodes.single())["cnt"]
                rel_count = (await rels.single())["cnt"]
                # Count distinct entity types
                types_result = await session.run("MATCH (n) RETURN count(DISTINCT n.type) AS cnt")
                type_count = (await types_result.single())["cnt"]
                return {"entity_count": node_count, "relation_count": rel_count, "entity_type_count": type_count or 0}
    except (asyncio.TimeoutError, Exception):
        return {"entity_count": 0, "relation_count": 0, "entity_type_count": 0}
