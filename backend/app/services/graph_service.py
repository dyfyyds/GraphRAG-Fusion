import asyncio
import json
import logging

from app.core.entity_quality import is_high_quality_entity_name, normalize_entity_name
from app.db.neo4j import get_neo4j_driver

logger = logging.getLogger("app")


def _limit_clause(limit: int) -> str:
    return " LIMIT $limit" if limit and limit > 0 else ""


def _apply_python_limit(items: list[dict], limit: int) -> list[dict]:
    return items[:limit] if limit and limit > 0 else items


def _parse_props(raw: str | None) -> dict:
    """Parse JSON properties string from Neo4j into a dict."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


async def search_entities(query: str, limit: int = 20, entity_type: str | None = None) -> list[dict]:
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(10):
            async with driver.session() as session:
                limit_clause = _limit_clause(limit)
                if query and entity_type:
                    result = await session.run(
                        "MATCH (e) WHERE e.name CONTAINS $q AND e.type = $etype "
                        f"RETURN elementId(e) AS eid, e.name AS name, e.type AS type, "
                        f"e.description AS description, e.properties AS properties{limit_clause}",
                        q=query, etype=entity_type, limit=limit,
                    )
                elif query:
                    result = await session.run(
                        "MATCH (e) WHERE e.name CONTAINS $q "
                        f"RETURN elementId(e) AS eid, e.name AS name, e.type AS type, "
                        f"e.description AS description, e.properties AS properties{limit_clause}",
                        q=query, limit=limit,
                    )
                elif entity_type:
                    result = await session.run(
                        "MATCH (e) WHERE e.type = $etype "
                        f"RETURN elementId(e) AS eid, e.name AS name, e.type AS type, "
                        f"e.description AS description, e.properties AS properties{limit_clause}",
                        etype=entity_type, limit=limit,
                    )
                else:
                    result = await session.run(
                        f"MATCH (e) RETURN elementId(e) AS eid, e.name AS name, e.type AS type, "
                        f"e.description AS description, e.properties AS properties{limit_clause}",
                        limit=limit,
                    )
                records = await result.data()
                items = [
                    {
                        "id": r["eid"],
                        "name": normalize_entity_name(r.get("name") or ""),
                        "type": r.get("type") or "",
                        "description": r.get("description") or "",
                        "properties": _parse_props(r.get("properties")),
                    }
                    for r in records
                    if is_high_quality_entity_name(r.get("name") or "")
                ]
                return _apply_python_limit(items, limit)
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"search_entities error: {e}")
        return []


async def search_entity_context(query: str, limit: int = 5) -> list[dict]:
    """Search matching entities, synonyms, and their direct relationships for answer citations."""
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(10):
            async with driver.session() as session:
                limit_clause = _limit_clause(limit)
                # 注意：不能用 f-string，否则 Cypher 的 {source: ...} 会被 Python 解析为表达式
                cypher_query = (
                    """
                    OPTIONAL MATCH (s:Synonym)
                    WHERE s.synonym CONTAINS $q OR s.original CONTAINS $q
                    WITH collect(DISTINCT s.original) + collect(DISTINCT s.synonym) AS aliases
                    MATCH (e)
                    WHERE e.name CONTAINS $q
                       OR e.description CONTAINS $q
                       OR e.name IN aliases
                    OPTIONAL MATCH (e)-[out]->(out_node)
                    OPTIONAL MATCH (in_node)-[in_rel]->(e)
                    RETURN
                        elementId(e) AS eid,
                        e.name AS name,
                        e.type AS type,
                        e.description AS description,
                        e.properties AS properties,
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
                    """ + limit_clause
                )
                result = await session.run(
                    cypher_query,
                    q=query,
                    limit=limit,
                )
                records = await result.data()
                items = []
                for record in records:
                    name = record.get("name") or ""
                    if not is_high_quality_entity_name(name):
                        continue
                    relations = []
                    for rel in (record.get("outgoing") or []) + (record.get("incoming") or []):
                        if (
                            rel.get("source")
                            and rel.get("target")
                            and rel.get("relation_type")
                            and is_high_quality_entity_name(rel.get("source"))
                            and is_high_quality_entity_name(rel.get("target"))
                        ):
                            relations.append({
                                "source": normalize_entity_name(rel["source"]),
                                "target": normalize_entity_name(rel["target"]),
                                "relation_type": rel["relation_type"],
                            })
                    items.append({
                        "id": record["eid"],
                        "name": normalize_entity_name(record.get("name") or ""),
                        "type": record.get("type") or "",
                        "description": record.get("description") or "",
                        "properties": _parse_props(record.get("properties")),
                        "relations": relations,
                    })
                return _apply_python_limit(items, limit)
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"search_entity_context error: {e}")
        return []


async def find_multi_hop_paths(entity_names: list[str], max_hops: int = 2, limit: int = 12) -> list[dict]:
    """查找命中实体两两之间的多跳最短路径（1..max_hops 跳）。

    用于复杂问题的多步推理：当查询同时涉及概念 A 和 D 时，
    返回 A→B→C→D 的完整路径，补全直接检索遗漏的中间概念 B、C。
    """
    names = [n for n in dict.fromkeys(entity_names) if n]
    if len(names) < 2:
        return []
    max_hops = min(max(int(max_hops), 1), 4)
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(10):
            async with driver.session() as session:
                # 变长模式的跳数无法参数化，max_hops 为受控整数，安全
                result = await session.run(
                    "MATCH (a:Entity), (b:Entity) "
                    "WHERE a.name IN $names AND b.name IN $names "
                    "AND elementId(a) < elementId(b) "
                    f"MATCH p = shortestPath((a)-[*1..{max_hops}]-(b)) "
                    "RETURN [n IN nodes(p) | {name: n.name, type: n.type}] AS nodes, "
                    "[r IN relationships(p) | r.rel_type] AS rels "
                    "LIMIT $limit",
                    names=names, limit=limit,
                )
                records = await result.data()
                paths = []
                seen = set()
                for record in records:
                    nodes = record.get("nodes") or []
                    rels = record.get("rels") or []
                    node_names = [normalize_entity_name(n.get("name") or "") for n in nodes]
                    if len(node_names) < 2 or not all(is_high_quality_entity_name(n) for n in node_names):
                        continue
                    key = "→".join(node_names)
                    if key in seen:
                        continue
                    seen.add(key)
                    paths.append({
                        "nodes": [
                            {"name": normalize_entity_name(n.get("name") or ""), "type": n.get("type") or ""}
                            for n in nodes
                        ],
                        "rels": [r or "关联" for r in rels],
                        "hops": len(rels),
                    })
                # 多跳路径优先（包含中间概念的推理链价值更高）
                paths.sort(key=lambda p: -p["hops"])
                return paths
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"find_multi_hop_paths error: {e}")
        return []


async def get_relations(limit: int = 100) -> list[dict]:
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(10):
            async with driver.session() as session:
                limit_clause = _limit_clause(limit)
                result = await session.run(
                    "MATCH (a)-[r]->(b) "
                    f"RETURN elementId(a) AS source_id, a.name AS source, elementId(b) AS target_id, b.name AS target, "
                    f"r.rel_type AS relation_type, r.description AS description{limit_clause}",
                    limit=limit,
                )
                records = await result.data()
                cleaned = []
                for record in records:
                    if not (
                        is_high_quality_entity_name(record.get("source") or "")
                        and is_high_quality_entity_name(record.get("target") or "")
                    ):
                        continue
                    cleaned.append({
                        **record,
                        "source": normalize_entity_name(record.get("source") or ""),
                        "target": normalize_entity_name(record.get("target") or ""),
                    })
                return _apply_python_limit(cleaned, limit)
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"get_relations error: {e}")
        return []


async def create_entity(name: str, entity_type: str, description: str = "") -> dict | None:
    driver = await get_neo4j_driver()
    try:
        name = normalize_entity_name(name)
        if not is_high_quality_entity_name(name):
            return None
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
                    name = normalize_entity_name(name)
                    if not is_high_quality_entity_name(name):
                        return False
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
                if not is_high_quality_entity_name(source) or not is_high_quality_entity_name(target):
                    return None
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
                    return {
                        "source": record["a_name"] or source,
                        "target": record["b_name"] or target,
                        "relation_type": relation_type,
                        "description": description or "",
                    }
        return None
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"创建关系失败: {e}")
        return None


async def update_relation(
    source: str,
    target: str,
    relation_type: str,
    new_source: str | None = None,
    new_target: str | None = None,
    new_relation_type: str | None = None,
    description: str | None = None,
) -> bool:
    driver = await get_neo4j_driver()
    try:
        next_source = normalize_entity_name(new_source or source)
        next_target = normalize_entity_name(new_target or target)
        next_relation_type = new_relation_type if new_relation_type is not None else relation_type
        if (
            not is_high_quality_entity_name(source)
            or not is_high_quality_entity_name(target)
            or not is_high_quality_entity_name(next_source)
            or not is_high_quality_entity_name(next_target)
            or not next_relation_type
        ):
            return False

        async with asyncio.timeout(2):
            async with driver.session() as session:
                params = {
                    "source": source,
                    "target": target,
                    "rel_type": relation_type,
                    "new_source": next_source,
                    "new_target": next_target,
                    "new_rel_type": next_relation_type,
                    "description": description,
                }
                result = await session.run(
                    """
                    MATCH (old_source)-[old_rel:RELATES]->(old_target)
                    WHERE (old_source.name = $source OR elementId(old_source) = $source)
                      AND (old_target.name = $target OR elementId(old_target) = $target)
                      AND old_rel.rel_type = $rel_type
                    MATCH (new_source), (new_target)
                    WHERE (new_source.name = $new_source OR elementId(new_source) = $new_source)
                      AND (new_target.name = $new_target OR elementId(new_target) = $new_target)
                    WITH old_rel, new_source, new_target, old_rel.description AS old_desc
                    DELETE old_rel
                    CREATE (new_source)-[new_rel:RELATES]->(new_target)
                    SET new_rel.rel_type = $new_rel_type,
                        new_rel.description = CASE
                            WHEN $description IS NULL THEN old_desc
                            ELSE $description
                        END
                    RETURN count(new_rel) AS cnt
                    """,
                    **params,
                )
                record = await result.single()
                return bool(record and record["cnt"] > 0)
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"更新关系失败: {e}")
        return False


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
    """删除文档关联的知识图谱节点，返回各步骤执行结果。

    仅删除 document_id 匹配且无其他文档引用的实体。
    共享实体（被多文档引用）不删除，避免误删其他文档的图谱数据。
    """
    result = {"neo4j": False, "error": None}
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(5):
            async with driver.session() as session:
                # 删除该文档独有的实体（document_id 匹配且未被其他文档引用的节点）
                await session.run(
                    "MATCH (e:Entity) WHERE e.document_id = $doc_id "
                    "AND NOT EXISTS { "
                    "  MATCH (other:Entity) WHERE other.name = e.name AND other.document_id <> $doc_id "
                    "} "
                    "DETACH DELETE e",
                    doc_id=document_id,
                )
                result["neo4j"] = True
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"删除文档 {document_id} 的图谱节点失败: {e}")
        result["error"] = str(e)
    return result


async def cleanup_orphaned_entities(existing_doc_ids: list[int]) -> dict:
    """清理孤儿图谱节点：document_id 不在现有文档列表中的实体。

    用于修复历史数据不一致（文档已删除但图谱节点残留）。
    """
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(30):
            async with driver.session() as session:
                # 删除 document_id 不在现有文档列表中的实体
                result = await session.run(
                    "MATCH (e:Entity) WHERE e.document_id IS NOT NULL "
                    "AND NOT e.document_id IN $ids "
                    "DETACH DELETE e "
                    "RETURN count(e) AS deleted",
                    ids=existing_doc_ids,
                )
                record = await result.single()
                deleted = record["deleted"] if record else 0

                # 清理无 document_id 的孤立实体（没有关联关系的）
                result2 = await session.run(
                    "MATCH (e:Entity) WHERE e.document_id IS NULL "
                    "AND NOT (e)--() "
                    "DELETE e "
                    "RETURN count(e) AS deleted"
                )
                record2 = await result2.single()
                deleted_no_doc = record2["deleted"] if record2 else 0

                # 清理孤儿同义词（其 original 或 synonym 不再对应任何实体）
                result3 = await session.run(
                    "MATCH (s:Synonym) "
                    "WHERE NOT EXISTS { MATCH (e:Entity) WHERE e.name = s.original } "
                    "AND NOT EXISTS { MATCH (e:Entity) WHERE e.name = s.synonym } "
                    "DELETE s "
                    "RETURN count(s) AS deleted"
                )
                record3 = await result3.single()
                deleted_synonyms = record3["deleted"] if record3 else 0

                return {
                    "success": True,
                    "deleted_orphaned": deleted,
                    "deleted_disconnected": deleted_no_doc,
                    "deleted_orphaned_synonyms": deleted_synonyms,
                }
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"清理孤儿图谱实体失败: {e}")
        return {"success": False, "error": str(e)}


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


async def cleanup_low_quality_entities(limit: int = 5000) -> dict:
    """Normalize fixable fragment entities and delete unfixable low-quality entities."""
    driver = await get_neo4j_driver()
    try:
        async with asyncio.timeout(20):
            async with driver.session() as session:
                result = await session.run(
                    "MATCH (e:Entity) RETURN elementId(e) AS eid, e.name AS name LIMIT $limit",
                    limit=limit,
                )
                records = await result.data()
                bad_ids = []
                renamed = 0
                for record in records:
                    original = record.get("name") or ""
                    normalized = normalize_entity_name(original)
                    if not is_high_quality_entity_name(normalized):
                        bad_ids.append(record["eid"])
                    elif normalized != original:
                        await session.run(
                            "MATCH (e:Entity) WHERE elementId(e) = $eid "
                            "SET e.name = $name, e.cleaned_from = $original",
                            eid=record["eid"],
                            name=normalized,
                            original=original,
                        )
                        renamed += 1
                if bad_ids:
                    await session.run(
                        "MATCH (e:Entity) WHERE elementId(e) IN $ids DETACH DELETE e",
                        ids=bad_ids,
                    )
                return {
                    "success": True,
                    "checked": len(records),
                    "deleted": len(bad_ids),
                    "renamed": renamed,
                    "remaining_may_exist": len(records) >= limit,
                }
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"清理低质量图谱实体失败: {e}")
        return {"success": False, "checked": 0, "deleted": 0, "error": str(e)}
