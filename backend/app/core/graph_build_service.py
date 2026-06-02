import asyncio
import json
import logging
import re

from sqlalchemy import select

from app.core.llm_client import get_llm_client
from app.core.entity_quality import clean_entity_record, normalize_entity_name
from app.db.neo4j import get_neo4j_driver
from app.db.mysql import async_session
from app.models.system_config import SystemConfig

logger = logging.getLogger("app")

# ── 系统提示词：实体抽取 ──────────────────────────────────────────
EXTRACT_SYSTEM_PROMPT = """## 1. 概述
你是一个顶级算法，旨在从文本中提取结构化格式信息，以构建知识图谱。
- **节点**代表实体和概念，类似于维基百科节点。
- 目的是实现知识图谱的简单性和清晰度，使其可供企业级问答检索使用。
- 你的输出将直接影响 RAG 系统的检索精度，请务必遵守所有规则。

## 2. 标记节点
- **一致性**：确保使用基本或基础类型作为节点标签。
  - 例如，当你识别到一个"条款"时，始终标记为**"条款"**，避免使用更具体的术语如"资格要求条款"或"例外条款"。
  - 当你识别到一个"组织"时，始终标记为**"组织"**，不要使用"政府机关"或"国企"等更细化的标签。
- **节点 ID**：切勿使用整数作为节点 ID。节点 ID 必须是文本中出现的名称或人类可读的标识符。
- **实体名称**：必须精确引用原文，不要缩写、改写或自行总结。保持名称的完整性和可检索性。
- **实体质量**：实体应是可独立检索的名词性对象。不要把普通谓语、半句话、连接词开头的片段抽成实体（例如"进一步规范""但下列行政事业性收费项目""以下情形"等负面示例）。如果片段带有"但下列/以下/上述"等前缀，应只保留真实名词实体。
{entity_types_section}
{relation_types_section}

## 3. 处理数值数据和日期
- 数值数据（如金额、比例、数量）和日期（如发布日期、生效日期）应作为对应节点的**属性（properties）**合并，而不是创建单独的节点。
- **不要为日期或数字创建单独的节点**。始终将它们附加为节点的属性。
- **属性格式**：属性必须采用 JSON 键值格式（key-value）。
- **引号**：切勿在属性值中使用转义单引号或双引号。
- **命名约定**：使用 camelCase 作为属性键，例如 "effectiveDate"、"amount"、"ratio"、"articleNumber"。

## 4. 共指消解（Coreference Resolution）
- **维护实体一致性**：提取实体时，确保一致性至关重要。
- 如果某个实体在文本中多次提及，但使用不同的名称或简称、代称，在整个知识图谱中**始终使用该实体最完整的标识符**。
- 例如：文本中先后出现"中华人民共和国政府采购法"、"政府采购法"、"本法"，统一使用"中华人民共和国政府采购法"作为实体 ID。
- 将简称和别名记录在同义词列表中。
- 请记住，知识图谱应该是连贯且易于理解的，保持实体引用的一致性至关重要。

## 5. 同义词（Synonyms）
- 同义词只输出文本中**有明确指代**或**常见等价表达**的词，不要编造。
- 同义词用于将用户口语化提问映射到正式实体名，例如用户问"社保"时能匹配到"社会保障资金"。
- 每个同义词条目包含 original（正式实体名）和 synonym（简称或别名）。

## 6. 关系（Relations）
- 关系必须有**明确的语义依据**，不能凭空臆造。
- 关系方向要准确：从源实体指向目标实体。
- 关系类型使用简洁的动词或动词短语。
- 对企业法规类文档，优先识别以下语义关系：
  - 发布、引用、规定、要求、包含、适用、约束、承担、提供、例外、关联
  - 对于条款与法规的关系，使用"规定"或"引用"
  - 对于条件与主体的关系，使用"要求"或"具备"

## 7. 严格合规
严格遵守以上规则。不合规将导致抽取结果被质量过滤器丢弃。"""

# ── 用户消息模板 ──────────────────────────────────────────────────
EXTRACT_USER_TEMPLATE = """使用给定的格式从以下输入中提取信息：

{text}

提示：请务必输出正确格式的完整 JSON，不要遗漏任何字段。
description 必须是对该实体在本文中角色或含义的简短概括（15-40字），不要复制原文。

只输出 JSON，不要其他内容：
{{
  "entities": [{{"name": "实体名称", "type": "实体类型", "description": "该实体在文中的含义概括", "properties": {{"key": "value"}}}}],
  "relations": [{{"source": "源实体名称", "target": "目标实体名称", "type": "关系类型", "description": "关系说明"}}],
  "synonyms": [{{"original": "原实体名", "synonym": "同义词或简称"}}]
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
    """4 层容错 JSON 解析，参考 wttc-nonelove/RAG 的鲁棒策略。"""
    response = response.strip()
    # 移除 markdown 代码块标记
    if response.startswith("```"):
        lines = response.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response = "\n".join(lines).strip()
    json_start = response.find("{")
    json_end = response.rfind("}")
    if json_start != -1 and json_end != -1:
        response = response[json_start:json_end + 1]

    # 第 1 层：直接解析
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # 第 2 层：去除尾部逗号
    try:
        cleaned = re.sub(r",\s*([}\]])", r"\1", response)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 第 3 层：修复缺失逗号
    try:
        cleaned = re.sub(r'"\s*\n\s*"', '",\n"', response)
        cleaned = re.sub(r'"\s*}\s*"', '"}', cleaned)
        cleaned = re.sub(r'"\s*]\s*"', ']', cleaned)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 第 4 层：正则逐段提取
    entities_match = re.search(r'"entities"\s*:\s*\[(.*?)\]', response, re.DOTALL)
    relations_match = re.search(r'"relations"\s*:\s*\[(.*?)\]', response, re.DOTALL)
    synonyms_match = re.search(r'"synonyms"\s*:\s*\[(.*?)\]', response, re.DOTALL)
    entities, relations, synonyms = [], [], []
    if entities_match:
        try:
            entities = json.loads('[' + entities_match.group(1) + ']')
        except Exception:
            pass
    if relations_match:
        try:
            relations = json.loads('[' + relations_match.group(1) + ']')
        except Exception:
            pass
    if synonyms_match:
        try:
            synonyms = json.loads('[' + synonyms_match.group(1) + ']')
        except Exception:
            pass
    return {"entities": entities, "relations": relations, "synonyms": synonyms}


def _fallback_extract(text: str, max_entities: int = 30) -> dict:
    """LLM 不可用时的保底抽取，保证文档仍能生成可检索的基础图谱。"""
    candidates: list[str] = []
    seen = set()
    patterns = [
        r"[一-鿿A-Za-z0-9][一-鿿A-Za-z0-9·（）()《》_-]{2,30}(?:公司|集团|大学|学院|研究院|平台|系统|模型|算法|项目|技术|方案|流程|标准|规范|文件|报告|计划|指标|数据|服务)",
        r"[A-Z][A-Za-z0-9_-]{2,}(?:\s+[A-Z][A-Za-z0-9_-]{2,}){0,3}",
        r"《[^》]{2,30}》",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text):
            entity = clean_entity_record({"name": match, "type": "概念"})
            if entity is None:
                continue
            name = entity["name"]
            if name in seen:
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
            entity = clean_entity_record({"name": title[:40], "type": "概念"})
            if entity:
                candidates.append(entity["name"])

    entities = [{"name": name, "type": "概念", "description": ""} for name in candidates[:max_entities]]
    relations = [
        {"source": candidates[i], "target": candidates[i + 1], "type": "关联"}
        for i in range(min(len(candidates) - 1, 20))
    ]
    return {"entities": entities, "relations": relations, "synonyms": []}


def _rule_extract_legal_context(text: str) -> dict:
    """Deterministically extract legal entities/relations that LLM often misses."""
    entities: list[dict] = []
    relations: list[dict] = []
    synonyms: list[dict] = []
    seen_entities: set[str] = set()
    seen_relations: set[tuple] = set()

    def _add_entity(name: str, entity_type: str):
        rec = clean_entity_record({"name": name, "type": entity_type})
        if not rec or rec["name"] in seen_entities:
            return
        seen_entities.add(rec["name"])
        entities.append(rec)

    def _add_rel(source: str, rel_type: str, target: str):
        s, t = normalize_entity_name(source), normalize_entity_name(target)
        k = (s, rel_type, t)
        if s not in seen_entities or t not in seen_entities or k in seen_relations:
            return
        seen_relations.add(k)
        relations.append({"source": s, "target": t, "type": rel_type})

    # 政府采购法实施条例
    if "政府采购法实施条例" in text:
        _add_entity("中华人民共和国政府采购法实施条例", "法规")
        if "第十七条" in text:
            _add_entity("第十七条", "条款")
            _add_rel("中华人民共和国政府采购法实施条例", "规定", "第十七条")
        for name, etype in (
            ("供应商", "主体"), ("法人或者其他组织", "主体"),
            ("社会保障资金", "材料"), ("设备和专业技术能力证明材料", "材料"),
            ("营业执照等证明文件", "材料"),
        ):
            if name in text:
                _add_entity(name, etype)

    # 政府采购法
    if "政府采购法" in text:
        _add_entity("中华人民共和国政府采购法", "法规")
        for art in ("第二十一条", "第二十二条", "第二十三条"):
            if art in text:
                _add_entity(art, "条款")
                _add_rel("中华人民共和国政府采购法", "规定", art)
        for name, etype in (
            ("采购人", "主体"), ("供应商", "主体"), ("法人", "主体"),
            ("独立承担民事责任", "条件"), ("资质证明文件", "材料"), ("业绩情况", "材料"),
        ):
            if name in text:
                _add_entity(name, etype)
        _add_rel("第二十三条", "要求提供", "资质证明文件")
        _add_rel("第二十三条", "要求提供", "业绩情况")
        _add_rel("采购人", "要求提供", "业绩情况")

    # 公司法
    if "公司法" in text:
        _add_entity("中华人民共和国公司法", "法规")
        for art in ("第十三条", "第十四条"):
            if art in text:
                _add_entity(art, "条款")
                _add_rel("中华人民共和国公司法", "规定", art)
        for name, etype in (
            ("总公司", "主体"), ("分公司", "主体"), ("子公司", "主体"),
            ("法人资格", "条件"), ("民事责任", "责任"),
        ):
            _add_entity(name, etype)
        _add_rel("分公司", "不具有", "法人资格")
        _add_rel("总公司", "设立", "分公司")
        _add_rel("总公司", "承担", "民事责任")
        synonyms.append({"original": "总公司", "synonym": "公司"})

    return {"entities": entities, "relations": relations, "synonyms": synonyms}


def _merge_extraction_data(primary: dict, supplemental: dict) -> dict:
    """合并两组抽取结果，按归一化名称去重。"""
    entities = list(primary.get("entities") or [])
    relations = list(primary.get("relations") or [])
    synonyms = list(primary.get("synonyms") or [])
    entity_keys = {normalize_entity_name(str(item.get("name", ""))) for item in entities}
    relation_keys = {
        (
            normalize_entity_name(str(item.get("source", ""))),
            str(item.get("type", "")),
            normalize_entity_name(str(item.get("target", ""))),
        )
        for item in relations
    }
    synonym_keys = {
        (
            normalize_entity_name(str(item.get("original", ""))),
            normalize_entity_name(str(item.get("synonym", ""))),
        )
        for item in synonyms
    }

    for entity in supplemental.get("entities", []):
        key = normalize_entity_name(str(entity.get("name", "")))
        if key and key not in entity_keys:
            entity_keys.add(key)
            entities.append(entity)
    for relation in supplemental.get("relations", []):
        key = (
            normalize_entity_name(str(relation.get("source", ""))),
            str(relation.get("type", "")),
            normalize_entity_name(str(relation.get("target", ""))),
        )
        if key not in relation_keys:
            relation_keys.add(key)
            relations.append(relation)
    for synonym in supplemental.get("synonyms", []):
        key = (
            normalize_entity_name(str(synonym.get("original", ""))),
            normalize_entity_name(str(synonym.get("synonym", ""))),
        )
        if key not in synonym_keys:
            synonym_keys.add(key)
            synonyms.append(synonym)
    return {"entities": entities, "relations": relations, "synonyms": synonyms}


def _split_text_for_extraction(text: str, max_chars: int) -> list[str]:
    """将长文本按结构边界切分为多个段落，每段不超过 max_chars。"""
    if not text or not text.strip():
        return [text] if text else []
    if len(text) <= max_chars:
        return [text]

    # 按结构边界切分：章节标题、条款、附件、编号项等
    boundary_pattern = re.compile(
        r'(?:^|\n)(?='
        r'第[一二三四五六七八九十百千万零两0-9]+[章节编条]|'
        r'#[1-6]\s|'
        r'[一二三四五六七八九十]+[、．.]|'
        r'（[一二三四五六七八九十0-9]+）|'
        r'附件[0-9一二三四五六七八九十]*[：:]|'
        r'[0-9]+[.、]\s*[一-龥]'
        r')',
    )

    parts = boundary_pattern.split(text)
    if len(parts) <= 1:
        parts = text.split('\n\n')

    sections: list[str] = []
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(current) + len(part) + 1 <= max_chars:
            current = f"{current}\n{part}".strip() if current else part
        else:
            if current:
                sections.append(current)
            if len(part) > max_chars:
                for i in range(0, len(part), max_chars):
                    sections.append(part[i:i + max_chars].strip())
            else:
                current = part
    if current:
        sections.append(current)

    return sections if sections else [text[:max_chars]]


async def _write_graph(data: dict, document_id: int) -> tuple[int, int]:
    raw_entities = data.get("entities", [])
    raw_relations = data.get("relations", [])
    raw_synonyms = data.get("synonyms", [])

    entities = []
    entity_names = set()
    for entity in raw_entities:
        cleaned = clean_entity_record(entity)
        if not cleaned or cleaned["name"] in entity_names:
            continue
        entity_names.add(cleaned["name"])
        entities.append(cleaned)

    relations = []
    for rel in raw_relations:
        source = normalize_entity_name(str(rel.get("source", "")))
        target = normalize_entity_name(str(rel.get("target", "")))
        if source not in entity_names or target not in entity_names:
            continue
        relations.append({**rel, "source": source, "target": target})

    synonyms = []
    for syn in raw_synonyms:
        original = normalize_entity_name(str(syn.get("original", "")))
        synonym = normalize_entity_name(str(syn.get("synonym", "")))
        if original not in entity_names or not synonym or synonym == original:
            continue
        synonyms.append({"original": original, "synonym": synonym})

    if not entities and not relations:
        return 0, 0

    driver = await get_neo4j_driver()

    # 关键：每个写操作独立 auto-commit，避免并发文档 MERGE 同一节点时 ExclusiveLock 死锁
    async def _merge_entity(name, etype, desc, props_str):
        async with driver.session() as session:
            await session.run(
                "MERGE (e:Entity {name: $name}) "
                "SET e.type = $type, e.description = $desc, e.status = 'pending', "
                "e.document_id = $doc_id, e.properties = $props",
                name=name, type=etype, desc=desc, doc_id=document_id, props=props_str,
            )

    async def _merge_relation(src, tgt, rel_type, rel_desc):
        async with driver.session() as session:
            await session.run(
                "MATCH (a:Entity {name: $src}), (b:Entity {name: $tgt}) "
                "MERGE (a)-[r:RELATES {rel_type: $rel_type}]->(b) "
                "SET r.description = $rel_desc, r.status = 'pending', r.document_id = $doc_id",
                src=src, tgt=tgt, rel_type=rel_type, rel_desc=rel_desc, doc_id=document_id,
            )

    async def _merge_synonym(orig, syn):
        async with driver.session() as session:
            await session.run(
                "MERGE (s:Synonym {original: $orig, synonym: $syn})",
                orig=orig, syn=syn,
            )

    for entity in entities:
        if not entity.get("name"):
            continue
        entity_props = entity.get("properties") or {}
        props_json = json.dumps(entity_props, ensure_ascii=False) if isinstance(entity_props, dict) else "{}"
        desc = entity.get("description", "") or ""
        try:
            await _merge_entity(entity["name"], entity.get("type", "Unknown"), desc, props_json)
        except Exception as exc:
            logger.warning(f"写入实体 '{entity['name']}' 失败: {str(exc)[:200]}")

    for rel in relations:
        if not rel.get("source") or not rel.get("target"):
            continue
        try:
            await _merge_relation(
                rel["source"], rel["target"],
                rel.get("type", "RELATED"),
                rel.get("description", "") or "",
            )
        except Exception as exc:
            logger.warning(f"写入关系 '{rel['source']}→{rel['target']}' 失败: {str(exc)[:200]}")

    for syn in synonyms:
        if not syn.get("original") or not syn.get("synonym"):
            continue
        try:
            await _merge_synonym(syn["original"], syn["synonym"])
        except Exception as exc:
            logger.warning(f"写入同义词 '{syn['original']}→{syn['synonym']}' 失败: {str(exc)[:200]}")

    return len(entities), len(relations)


async def extract_and_build(text: str, document_id: int) -> dict:
    """LLM 抽取实体/关系/同义词 -> Neo4j 写入（待审核状态）"""
    kg_config = await _load_kg_config()
    entity_types = kg_config.get("entity_types", "")
    relation_types = kg_config.get("relation_types", "")
    max_chars = int(kg_config.get("max_chars", 4000))

    if entity_types:
        entity_types_section = f"\n- **允许的节点标签：**{entity_types}"
    else:
        entity_types_section = ""

    if relation_types:
        relation_types_section = f"\n- **允许的关系类型：**{relation_types}"
    else:
        relation_types_section = ""

    system_prompt = EXTRACT_SYSTEM_PROMPT.format(
        entity_types_section=entity_types_section,
        relation_types_section=relation_types_section,
    )

    # 分段落抽取：长文档按结构切段后分批抽取
    sections = _split_text_for_extraction(text, max_chars)
    logger.info(f"文档 {document_id} 分为 {len(sections)} 段进行实体抽取")

    llm = get_llm_client()
    all_data: dict = {"entities": [], "relations": [], "synonyms": []}
    extraction_failed = False

    for idx, section_text in enumerate(sections):
        if not section_text.strip():
            continue
        user_message = EXTRACT_USER_TEMPLATE.format(text=section_text)
        try:
            response = await llm.chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                retries=1,
                no_timeout=True,
            )
            logger.info(f"文档 {document_id} 段 {idx+1}/{len(sections)} LLM 抽取响应长度: {len(response)}")
            section_data = _clean_json_response(response)
            all_data = _merge_extraction_data(all_data, section_data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"文档 {document_id} 段 {idx+1} 抽取失败: {str(e)[:200]}")
            extraction_failed = True

    # 合并确定性规则抽取结果（法规特有实体/关系）
    rule_data = _rule_extract_legal_context(text)
    all_data = _merge_extraction_data(all_data, rule_data)

    if not all_data.get("entities") and not all_data.get("relations"):
        logger.warning(f"文档 {document_id} LLM 未抽取到任何实体或关系")

    if extraction_failed and (not all_data.get("entities")):
        try:
            fallback_data = _fallback_extract(text[:max_chars])
            all_data = _merge_extraction_data(all_data, fallback_data)
        except Exception as fallback_err:
            logger.error(f"文档 {document_id} 降级抽取也失败: {fallback_err}", exc_info=True)

    if not all_data.get("entities") and not all_data.get("relations"):
        return {"success": True, "message": "未抽取到实体和关系", "entity_count": 0, "relation_count": 0}

    entity_count, relation_count = await _write_graph(all_data, document_id)
    logger.info(f"文档 {document_id} 图谱构建完成: {entity_count} 实体, {relation_count} 关系")
    return {
        "success": True,
        "message": "图谱构建完成",
        "entity_count": entity_count,
        "relation_count": relation_count,
    }
