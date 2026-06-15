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

# ── 系统提示词：实体抽取（通用领域，细粒度）──────────────────────
EXTRACT_SYSTEM_PROMPT = """## 1. 任务
你是一个通用领域的知识图谱抽取器，适用于任意文本：法律法规、企业制度、科技工程、新闻时事、历史人文、自然科学、产品文档、学术论文等。
请从文本中抽取细粒度、可独立检索的实体、关系和同义词，目标是覆盖读者可能据此提问的全部关键对象，而不是只保留少量笼统的概括节点。

## 2. 领域自适应：先判断领域，再选类型
- 先判断文本主题领域，再选择贴合该领域的实体类型；不要把所有文本都套用同一套标签。
- 通用实体类型（按领域取用，可自行扩展）：
  - 人物、组织机构、地点、时间或日期、事件
  - 概念或术语、理论或方法、技术或工具、产品或系统、作品或文献
  - 物质、物种、生物结构、自然现象（科技与自然类）
  - 法规、条款、制度、主体、职责、条件、材料、资质（法律与制度类）
  - 指标或数值、金额、比例、流程或步骤、标准或规范、范围、例外
- 实体必须是名词性、可独立检索的对象，名称优先使用原文中最完整的表达。{entity_types_section}

## 3. 抽取粒度：要细、要全
- 对 800-1800 字的段落，通常应抽取 10-30 个实体和 8-30 条关系；若只输出 2-3 个实体，说明抽取过粗，请重新细化。
- 既抽取主干概念，也抽取其属性对象、组成部分、相关条件、参与者、产物等可被追问的细节。
- 数值、日期、金额、比例优先作为相关实体的 properties（如 date、amount、ratio、number）；但若存在可检索的约束名词（如“80%的比例”“收费项目”“三年期限”），可将约束对象作为实体，数字放入 properties。
- 条款号（如“第二十二条”“第十七条”）在法规文本中应作为条款实体，并与所属法规建立关系。

## 4. 不要抽取的内容：保证精确度
- 不要把谓语、半句话、连接词开头的片段当作实体，例如“进一步规范”“以下情形”“应当提交以下材料”“可以要求”。
- 遇到“但下列收费项目”“以及相关材料”这类片段，应抽取其中真实的名词实体。
- 不要输出过于宽泛、无检索价值的孤立词，例如“内容”“方面”“情况”“问题”。

## 5. 共指与同义词
- 同一实体有全称、简称、代称时，name 用最完整的标识符，并把简称和常见问法写入 synonyms。
- 例如“中华人民共和国政府采购法”与“政府采购法”、“人工智能”与“AI”、“万有引力定律”与“万有引力”。
- 不要编造文本中不存在或不常见的同义词。

## 6. 关系
- 关系必须来自文本语义，方向准确，类型用简洁的动词或动词短语。
- 通用关系示例：属于、包含、组成、位于、隶属、提出、发现、发明、使用、依赖、导致、影响、规定、要求、提供、适用、引用、衔接、废止、对立、合作。
- 只在已抽取的实体之间建立关系，避免悬空端点。{relation_types_section}

## 7. 输出纪律
只输出 JSON，不得输出解释文字。entities、relations、synonyms 三个字段都必须存在，可为空数组。
description 用 15-40 字概括该实体或关系在本文中的作用，不要整句复制原文。"""

# ── 用户消息模板 ──────────────────────────────────────────────────
EXTRACT_USER_TEMPLATE = """使用给定的格式从以下输入中提取信息：

{text}

提示：请务必输出格式正确的完整 JSON，不要遗漏任何字段。请优先做细粒度抽取，覆盖文中出现的人物、组织、概念、术语、技术、事件、条款、条件、数值比例等一切可检索对象。
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


def _fallback_extract(text: str, max_entities: int = 80) -> dict:
    """LLM 不可用时的保底抽取，保证文档仍能生成可检索的基础图谱。"""
    candidates: list[str] = []
    seen = set()
    patterns = [
        r"《[^》]{2,80}》",
        r"(?:[\u4e00-\u9fff]{1,12})?[〔\[]\d{4}[〕\]]\d+号|(?:财政部令|国务院令)第\d+号|第[一二三四五六七八九十百0-9]+条",
        r"[一-鿿A-Za-z0-9][一-鿿A-Za-z0-9·（）()《》_-]{2,36}(?:公司|集团|大学|学院|研究院|平台|系统|模型|算法|项目|技术|方案|流程|标准|规范|文件|报告|计划|指标|数据|服务|办法|制度|准则|目录|通知|规定|条例|材料|凭证|票据|合同|经费|会费|收入|支出|核算|科目|账务处理|收费项目|证明|资质|资格|能力|责任|条件|范围|期限|比例|限额)",
        r"(?:政府采购|招标|投标|评标|评审|资格审查|资质证明|业绩证明|设备证明|人员证明|社保材料|劳动合同|授权文件|行政事业性收费项目|政府会计准则|小企业会计准则|工会经费|非税收入|资产核算|账务处理)[一-鿿A-Za-z0-9·（）()《》_-]{0,18}",
        r"[A-Z][A-Za-z0-9_-]{2,}(?:\s+[A-Z][A-Za-z0-9_-]{2,}){0,3}",
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


def _guess_entity_type(name: str) -> str:
    if re.fullmatch(r"第[一二三四五六七八九十百0-9]+条", name):
        return "条款"
    if name.startswith("《") and name.endswith("》"):
        return "法规"
    if re.search(r"[〔\[]\d{4}[〕\]]\d+号|(?:财政部令|国务院令)第\d+号", name):
        return "文件"
    if any(word in name for word in ("采购人", "供应商", "总公司", "分公司", "机构", "部门", "单位")):
        return "主体"
    if any(word in name for word in ("证明", "材料", "凭证", "票据", "合同", "授权文件")):
        return "材料"
    if any(word in name for word in ("条件", "资格", "资质", "能力", "责任", "要求")):
        return "条件"
    if any(word in name for word in ("标准", "准则", "制度", "办法", "条例", "规定", "目录", "通知")):
        return "规则"
    if any(word in name for word in ("经费", "会费", "收入", "支出", "收费", "金额", "比例", "限额")):
        return "财务事项"
    return "概念"


def _candidate_entity_fragments(value: str) -> list[str]:
    """把“劳动合同和社保材料”这类粘连短语拆成可检索实体。"""
    normalized = normalize_entity_name(value)
    if not normalized:
        return []
    parts = re.split(r"(?:、|，|,|；|;|以及|或者|和|及|与|或)", normalized)
    fragments: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        part = re.sub(r"^.*?(?:应当|应|可以|需|需要|要求|提供|提交|出具|签订|缴纳|加强|按照)", "", part).strip()
        part = normalize_entity_name(part)
        domain_starts = (
            "政府采购", "招标", "投标", "评标", "评审", "资格审查",
            "资质证明", "业绩证明", "设备证明", "人员证明", "社保材料",
            "劳动合同", "授权文件", "行政事业性收费项目", "政府会计",
            "小企业会计", "工会经费", "非税收入", "票据", "资产核算",
            "账务处理", "预算会计", "财务会计",
        )
        marker_positions = [(part.find(marker), marker) for marker in domain_starts if part.find(marker) > 0]
        if marker_positions:
            start, _ = min(marker_positions, key=lambda item: item[0])
            part = part[start:]
        if part and part not in fragments:
            fragments.append(part)
    return fragments or [normalized]


def _rule_extract_domain_context(text: str, max_entities: int = 120) -> dict:
    """补充抽取跨领域的法规、条款、材料、条件和财会事项。"""
    entities: list[dict] = []
    relations: list[dict] = []
    synonyms: list[dict] = []
    seen_entities: set[str] = set()
    seen_relations: set[tuple] = set()

    def _add_entity(name: str, entity_type: str | None = None, description: str = "") -> str | None:
        rec = clean_entity_record({
            "name": name,
            "type": entity_type or _guess_entity_type(normalize_entity_name(name)),
            "description": description,
        })
        if not rec:
            return None
        normalized = rec["name"]
        if normalized not in seen_entities and len(entities) < max_entities:
            seen_entities.add(normalized)
            entities.append(rec)
        return normalized

    def _add_rel(source: str, rel_type: str, target: str, description: str = ""):
        s, t = normalize_entity_name(source), normalize_entity_name(target)
        if s not in seen_entities or t not in seen_entities:
            return
        key = (s, rel_type, t)
        if key in seen_relations:
            return
        seen_relations.add(key)
        relations.append({"source": s, "target": t, "type": rel_type, "description": description})

    doc_names = []
    for match in re.findall(r"《[^》]{2,80}》", text):
        name = _add_entity(match, "法规", "文中引用或规定的法规制度")
        if name:
            doc_names.append(name)

    codes = []
    for match in re.findall(r"(?:[\u4e00-\u9fff]{1,12})?[〔\[]\d{4}[〕\]]\d+号|(?:财政部令|国务院令)第\d+号", text):
        name = _add_entity(match, "文件", "文中引用的政策文件编号")
        if name:
            codes.append(name)

    articles = []
    for match in re.findall(r"第[一二三四五六七八九十百0-9]+条", text):
        name = _add_entity(match, "条款", "文中出现的具体条款依据")
        if name:
            articles.append(name)

    for doc in doc_names + codes:
        for article in articles[:40]:
            _add_rel(doc, "包含", article, "法规或文件包含该条款")

    phrase_patterns = [
        r"(?:总公司|分公司|子公司|采购人|供应商|招标人|投标人|代理机构|评审专家|财政部门|行政事业单位|事业单位|工会组织)",
        r"(?:资质证明|业绩证明|设备证明|人员证明|证明材料|证明文件|社保材料|劳动合同|授权文件|营业执照|合同|凭证|票据)",
        r"(?:评审标准|评标标准|评分标准|资格条件|资格审查|履约能力|专业技术能力|民事责任|法人资格|投标资格)",
        r"(?:行政事业性收费项目|收费项目|政府会计准则制度新旧衔接|政府会计准则|小企业会计准则|政府会计制度|会计制度|工会经费|会费|非税收入|资产核算|账务处理|预算会计|财务会计|会计科目)",
        r"[一-鿿A-Za-z0-9]{2,28}(?:资质证明|业绩证明|设备证明|人员证明|证明材料|证明文件|社保材料|劳动合同|授权文件|营业执照|合同|凭证|票据)",
        r"[一-鿿A-Za-z0-9]{2,28}(?:评审标准|评标标准|评分标准|资格条件|资格审查|履约能力|专业技术能力|民事责任|法人资格|投标资格)",
        r"[一-鿿A-Za-z0-9]{2,28}(?:行政事业性收费项目|收费项目|政府会计准则|小企业会计准则|政府会计制度|会计制度|工会经费|会费|非税收入|资产核算|账务处理|预算会计|财务会计|会计科目)",
        r"[一-鿿A-Za-z0-9]{2,28}(?:目录|清单|范围|期限|限额|比例|标准|办法|规定|制度|准则|条例|通知)",
    ]
    phrase_names: list[str] = []
    for pattern in phrase_patterns:
        for match in re.findall(pattern, text):
            for fragment in _candidate_entity_fragments(match):
                name = _add_entity(fragment, None, "文中可独立检索的业务对象")
                if name:
                    phrase_names.append(name)

    for source in articles[:40] or doc_names[:8] or codes[:8]:
        window_start = max(text.find(source) - 250, 0) if source in text else 0
        window_end = min(text.find(source) + 600, len(text)) if source in text else len(text)
        window = text[window_start:window_end]
        for phrase in phrase_names[:80]:
            if phrase in window and source != phrase:
                rel_type = "要求" if any(key in phrase for key in ("证明", "材料", "条件", "资格", "能力")) else "规定"
                _add_rel(source, rel_type, phrase, "条款或文件对该事项作出规定")

    synonym_pairs = (
        ("社会保障资金", "社保"),
        ("中华人民共和国政府采购法", "政府采购法"),
        ("中华人民共和国政府采购法实施条例", "政府采购法实施条例"),
        ("中华人民共和国公司法", "公司法"),
        ("政府会计准则制度新旧衔接", "新旧衔接"),
        ("行政事业性收费项目", "收费项目"),
    )
    entity_set = {item["name"] for item in entities}
    for original, synonym in synonym_pairs:
        if original in entity_set or original in text:
            normalized = _add_entity(original, _guess_entity_type(original), "常见正式名称")
            if normalized:
                synonyms.append({"original": normalized, "synonym": synonym})

    return {"entities": entities, "relations": relations, "synonyms": synonyms}


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
    # 注意：document_id 仅在首次创建时写入，避免共享实体被后续文档覆盖导致删除时孤儿残留
    async def _merge_entity(name, etype, desc, props_str):
        async with driver.session() as session:
            await session.run(
                "MERGE (e:Entity {name: $name}) "
                "ON CREATE SET e.document_id = $doc_id "
                "SET e.type = $type, e.description = $desc, e.status = 'pending', "
                "e.properties = $props",
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


async def extract_graph_data(text: str, doc_label: str | int = "?") -> dict:
    """纯抽取：LLM 分段抽取 + 规则补充 + 兜底，返回 {entities, relations, synonyms}，不写库。

    供文档解析（extract_and_build）与图谱导入（prose 文件回退 graph_import_service）共用。
    """
    kg_config = await _load_kg_config()
    entity_types = kg_config.get("entity_types", "")
    relation_types = kg_config.get("relation_types", "")
    configured_max_chars = int(kg_config.get("max_chars", 1800))
    max_chars = max(800, min(configured_max_chars, 2600))
    min_entities = int(kg_config.get("min_entities_per_document", 12))

    entity_types_section = f"\n- **允许的节点标签：**{entity_types}" if entity_types else ""
    relation_types_section = f"\n- **允许的关系类型：**{relation_types}" if relation_types else ""

    system_prompt = EXTRACT_SYSTEM_PROMPT.format(
        entity_types_section=entity_types_section,
        relation_types_section=relation_types_section,
    )

    # 分段落抽取：长文档按结构切段后分批抽取
    sections = _split_text_for_extraction(text, max_chars)
    logger.info(f"文档 {doc_label} 分为 {len(sections)} 段进行实体抽取")

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
                temperature=0.05,
                retries=2,
                no_timeout=True,
            )
            logger.info(f"文档 {doc_label} 段 {idx+1}/{len(sections)} LLM 抽取响应长度: {len(response)}")
            section_data = _clean_json_response(response)
            all_data = _merge_extraction_data(all_data, section_data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"文档 {doc_label} 段 {idx+1} 抽取失败: {str(e)[:200]}")
            extraction_failed = True

    # 合并确定性规则抽取结果：先补法规特例，再补通用领域实体，避免 LLM 抽得过粗。
    rule_data = _merge_extraction_data(
        _rule_extract_legal_context(text),
        _rule_extract_domain_context(text),
    )
    all_data = _merge_extraction_data(all_data, rule_data)

    entity_total = len(all_data.get("entities") or [])
    relation_total = len(all_data.get("relations") or [])
    if entity_total == 0 and relation_total == 0:
        logger.warning(f"文档 {doc_label} LLM 未抽取到任何实体或关系")

    expected_min_entities = max(min_entities, min(80, len(text) // 180))
    if extraction_failed or entity_total < expected_min_entities or relation_total < max(6, expected_min_entities // 2):
        try:
            fallback_data = _fallback_extract(text, max_entities=max(80, expected_min_entities))
            all_data = _merge_extraction_data(all_data, fallback_data)
            logger.info(
                "文档 %s 启用补充抽取: LLM/规则结果 %s 实体 %s 关系, 目标下限 %s",
                doc_label, entity_total, relation_total, expected_min_entities,
            )
        except Exception as fallback_err:
            logger.error(f"文档 {doc_label} 降级抽取也失败: {fallback_err}", exc_info=True)

    return all_data


async def extract_and_build(text: str, document_id: int) -> dict:
    """LLM 抽取实体/关系/同义词 -> Neo4j 写入（待审核状态）"""
    all_data = await extract_graph_data(text, doc_label=document_id)

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
