import asyncio
import json
import logging
import re

from sqlalchemy import select

from app.core.llm_client import get_llm_client
from app.db.neo4j import get_neo4j_driver
from app.db.mysql import async_session
from app.models.system_config import SystemConfig

logger = logging.getLogger("app")

EXTRACT_PROMPT = """你是一个知识图谱构建专家。请从以下文本中抽取所有有意义的实体和它们之间的关系。

要求：
1. 抽取文本中出现的所有人名、机构、地点、产品、概念、术语、法规、文件、事件等实体
2. 为每个实体指定合适的类型（如：人物、组织、地点、产品、概念、法规、文件、事件、技术、流程、指标 等）
3. 识别实体之间的语义关系（如：包含、属于、发布、引用、管理、负责、使用、依赖、导致、关联 等）
4. 实体名称必须精确，不要缩写或改写
5. 关系必须有明确的语义依据

{entity_types_section}
{relation_types_section}

文本：
{text}

只输出 JSON，不要其他内容：
{{
  "entities": [{{"name": "实体名称", "type": "实体类型"}}],
  "relations": [{{"source": "源实体名称", "target": "目标实体名称", "type": "关系类型"}}]
}}"""


async def _load_kg_config() -> dict:
    """从数据库读取 kg_config 配置"""
    try:
        async with async_session() as db:
            result = await db.execute(
                select(SystemConfig).where(SystemConfig.config_key == "kg_config")
            )
            row = result.scalar_one_or_none()
            if row and row.config_value:
                return json.loads(row.config_value)
    except Exception as e:
        logger.warning(f"读取 kg_config 失败，使用默认值: {e}")
    return {}


def _clean_json_response(response: str) -> dict:
    response = response.strip()
    if response.startswith("```"):
        response = response.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    json_start = response.find("{")
    json_end = response.rfind("}")
    if json_start != -1 and json_end != -1:
        response = response[json_start:json_end + 1]
    return json.loads(response)


def _fallback_extract(text: str, max_entities: int = 30) -> dict:
    """LLM 不可用时的保底抽取，保证文档仍能生成可检索的基础图谱。"""
    candidates: list[str] = []
    seen = set()
    patterns = [
        r"[\u4e00-\u9fffA-Za-z0-9][\u4e00-\u9fffA-Za-z0-9·（）()《》_-]{2,30}(?:公司|集团|大学|学院|研究院|平台|系统|模型|算法|项目|技术|方案|流程|标准|规范|文件|报告|计划|指标|数据|服务)",
        r"[A-Z][A-Za-z0-9_-]{2,}(?:\s+[A-Z][A-Za-z0-9_-]{2,}){0,3}",
        r"《[^》]{2,30}》",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text):
            name = match.strip(" ，。；;：:\n\t")
            if not name or name in seen:
                continue
            seen.add(name)
            candidates.append(name)
            if len(candidates) >= max_entities:
                break
        if len(candidates) >= max_entities:
            break

    if not candidates:
        title = next((line.strip() for line in text.splitlines() if len(line.strip()) >= 3), "")
        if title:
            candidates.append(title[:40])

    entities = [{"name": name, "type": "概念"} for name in candidates[:max_entities]]
    relations = [
        {"source": candidates[i], "target": candidates[i + 1], "type": "关联"}
        for i in range(min(len(candidates) - 1, 20))
    ]
    return {"entities": entities, "relations": relations, "synonyms": []}


async def _write_graph(data: dict, document_id: int) -> tuple[int, int]:
    entities = data.get("entities", [])
    relations = data.get("relations", [])
    synonyms = data.get("synonyms", [])

    if not entities and not relations:
        return 0, 0

    driver = await get_neo4j_driver()
    async with driver.session() as session:
        for entity in entities:
            if not entity.get("name"):
                continue
            await session.run(
                "MERGE (e:Entity {name: $name}) SET e.type = $type, e.status = 'pending', e.document_id = $doc_id",
                name=entity["name"], type=entity.get("type", "Unknown"), doc_id=document_id,
            )

        for rel in relations:
            if not rel.get("source") or not rel.get("target"):
                continue
            await session.run(
                "MATCH (a:Entity {name: $src}), (b:Entity {name: $tgt}) "
                "MERGE (a)-[r:RELATES {rel_type: $rel_type}]->(b) SET r.status = 'pending'",
                src=rel["source"], tgt=rel["target"], rel_type=rel.get("type", "RELATED"),
            )

        for syn in synonyms:
            if not syn.get("original") or not syn.get("synonym"):
                continue
            await session.run(
                "MERGE (s:Synonym {original: $orig, synonym: $syn})",
                orig=syn["original"], syn=syn["synonym"],
            )

    return len(entities), len(relations)


async def extract_and_build(text: str, document_id: int) -> dict:
    """LLM 抽取实体/关系/同义词 → Neo4j 写入（待审核状态）"""
    # 读取 kg_config 配置
    kg_config = await _load_kg_config()
    entity_types = kg_config.get("entity_types", "")
    relation_types = kg_config.get("relation_types", "")
    max_chars = int(kg_config.get("max_chars", 4000))

    # 配置的类型作为建议，不是限制
    if entity_types:
        entity_types_section = f"参考实体类型（可自由扩展）：{entity_types}"
    else:
        entity_types_section = ""

    if relation_types:
        relation_types_section = f"参考关系类型（可自由扩展）：{relation_types}"
    else:
        relation_types_section = ""

    prompt = EXTRACT_PROMPT.format(
        text=text[:max_chars],
        entity_types_section=entity_types_section,
        relation_types_section=relation_types_section,
    )

    llm = get_llm_client()
    try:
        response = await llm.chat([{"role": "user", "content": prompt}], temperature=0.2, retries=1, no_timeout=True)
        logger.info(f"文档 {document_id} LLM 抽取原始响应长度: {len(response)}")

        data = _clean_json_response(response)

        if not data.get("entities") and not data.get("relations"):
            logger.warning(f"文档 {document_id} LLM 未抽取到任何实体或关系")
            return {"success": True, "message": "未抽取到实体和关系", "entity_count": 0, "relation_count": 0}

        entity_count, relation_count = await _write_graph(data, document_id)
        logger.info(f"文档 {document_id} 图谱构建完成: {entity_count} 实体, {relation_count} 关系")
        return {
            "success": True,
            "message": "图谱构建完成",
            "entity_count": entity_count,
            "relation_count": relation_count,
        }
    except json.JSONDecodeError as e:
        message = f"LLM 返回内容不是有效 JSON，图谱构建失败: {str(e)[:200]}"
        logger.warning(f"文档 {document_id} {message}，启用本地降级抽取")
    except Exception as e:
        logger.error(f"文档 {document_id} LLM 图谱抽取失败，启用本地降级抽取: {e}", exc_info=True)

    try:
        fallback_data = _fallback_extract(text[:max_chars])
        entity_count, relation_count = await _write_graph(fallback_data, document_id)
        logger.info(f"文档 {document_id} 本地降级图谱构建完成: {entity_count} 实体, {relation_count} 关系")
        return {
            "success": True,
            "message": "LLM 抽取失败，已使用本地规则完成基础图谱构建",
            "entity_count": entity_count,
            "relation_count": relation_count,
        }
    except Exception as fallback_err:
        logger.error(f"文档 {document_id} 本地降级图谱构建失败: {fallback_err}", exc_info=True)
        return {"success": False, "message": str(fallback_err)[:500], "entity_count": 0, "relation_count": 0}
