import re


LEADING_NOISE_RE = re.compile(
    r"^(?:但|但是|只是|并且|同时|以及|或者|若|如|对于|关于|根据|按照|依据|下列|以下|上述|前述|进一步|继续|加强|规范|明确|通知|要求)+"
)
ENUM_PREFIX_RE = re.compile(r"^[（(]?[一二三四五六七八九十百0-9]+[）)、.．]\s*")
PUNCTUATION_RE = re.compile(r"[\s，。；;：:、,]+")
LEGAL_DOC_RE = re.compile(r"《[^》]{2,80}》")
LEGAL_CODE_RE = re.compile(r"(?:[\u4e00-\u9fff]{1,12})?[〔\[]\d{4}[〕\]]\d+号|(?:财政部令|国务院令)第\d+号|第[一二三四五六七八九十百0-9]+条")

GOOD_SUFFIXES = (
    "法",
    "条例",
    "办法",
    "通知",
    "规定",
    "制度",
    "准则",
    "指南",
    "目录",
    "标准",
    "规则",
    "意见",
    "公告",
    "流程",
    "系统",
    "声明函",
    "证明文件",
    "证明材料",
    "资质",
    "资格",
    "条件",
    "情况",
    "责任",
    "费用",
    "票据",
    "账户",
    "预算",
    "合同",
    "项目",
    "产品",
    "服务",
    "供应商",
    "采购人",
    "代理机构",
    "总公司",
    "分公司",
    # 新增通用企业文档/管理术语
    "文件",
    "报告",
    "协议",
    "章程",
    "决议",
    "纪要",
    "说明",
    "清单",
    "台账",
    "记录",
    "档案",
    "方案",
    "计划",
    "指标",
    "数据",
    "平台",
    "模型",
    "技术",
    "程序",
    "权限",
    "能力",
    "要求",
    "情形",
    "期限",
    "限额",
    "比例",
    "范围",
    "依据",
    "方式",
    "凭证",
    "经费",
    "收入",
    "支出",
    "收费项目",
    "会费",
    "科目",
    "核算",
    "账务处理",
    "财务会计",
    "预算会计",
    "评审标准",
    "评标标准",
    "评分标准",
    "资质证明",
    "业绩证明",
    "人员证明",
    "设备证明",
    "授权文件",
    "社保材料",
    "劳动合同",
    "投标资格",
    "履约能力",
)
ORG_SUFFIXES = (
    "公司",
    "集团",
    "单位",
    "机关",
    "部门",
    "财政部",
    "国务院",
    "人民政府",
    "委员会",
    "办公厅",
    "财政厅",
    "财政局",
    "中心",
    "医院",
    "大学",
    "学院",
)
BAD_EXACT = {
    "进一步规范",
    "进一步明确",
    "有关问题",
    "相关资料",
    "下列情形",
    "以下情形",
    "其他情形",
    "有关事项",
    "相关政策",
}
# 过于宽泛、单独成词时无检索价值的通用词（精确匹配才拒绝，不影响复合实体）
GENERIC_STOPWORDS = {
    "内容", "方面", "情况", "问题", "其他", "相关", "等", "等等", "如下", "上述",
}
BAD_SUFFIXES = (
    "进行",
    "开展",
    "加强",
    "规范",
    "明确",
    "完善",
    "提高",
    "推进",
    "落实",
)
VERB_PHRASES = (
    "可以要求",
    "应当",
    "不得",
    "提供",
    "参加",
    "根据",
    "认为",
    "获得",
    "实行",
    "审查",
    "出具",
    "签订",
    "缴纳",
    "承担",
    "具备",
    "符合",
    "明确",
)

DOMAIN_KEYWORDS = (
    # 政府采购/招投标
    "采购", "政府采购", "招标", "投标", "评标", "评审", "履约", "供应商",
    "采购人", "代理机构", "资格审查", "招标文件", "投标文件", "中标",
    # 财会/行政事业/非税
    "会计", "政府会计", "小企业会计", "财务会计", "预算会计", "科目",
    "核算", "账务", "行政事业", "事业单位", "工会", "会费", "经费",
    "非税", "收费", "票据", "资产", "预算", "决算", "报销", "发票",
    # 证明材料/资质能力
    "资质", "资格", "业绩", "设备", "人员", "专业技术", "授权", "社保",
    "合同", "劳动合同", "证明材料", "证明文件",
    # 会议差旅/安全生产/资产管理
    "差旅", "会议", "培训", "安全生产", "固定资产", "国有资产",
    # 通用治理
    "财务", "审计", "税务", "合规", "风险", "内控", "法务", "质量",
    "安全", "环保", "消防", "行政", "档案", "印章", "公文", "接待",
    "信息", "网络", "数据", "系统", "平台", "协议",
)


def normalize_entity_name(name: str) -> str:
    name = (name or "").strip()
    name = name.strip(" \t\r\n，。；;：:、,.!?！？“”\"'`")
    name = ENUM_PREFIX_RE.sub("", name).strip()
    name = LEADING_NOISE_RE.sub("", name).strip()
    return name.strip(" \t\r\n，。；;：:、,.!?！？“”\"'`")


def is_high_quality_entity_name(name: str) -> bool:
    raw_name = (name or "").strip()
    name = normalize_entity_name(name)
    if not name:
        return False
    if raw_name in BAD_EXACT:
        return False
    if raw_name.startswith(("以下", "下列", "上述", "前述")) and len(name) <= 2:
        return False
    if name in BAD_EXACT or name in GENERIC_STOPWORDS:
        return False
    if len(name) < 2 or len(name) > 80:
        return False
    if ("《" in name or "》" in name) and not LEGAL_DOC_RE.fullmatch(name):
        return False
    if PUNCTUATION_RE.search(name) and not LEGAL_DOC_RE.fullmatch(name):
        return False
    if LEGAL_DOC_RE.fullmatch(name) or LEGAL_CODE_RE.fullmatch(name):
        return True
    # 动词短语检查：只在短语出现在名称开头位置时拒绝（谓语片段特征）
    _verb_hit = next((phrase for phrase in VERB_PHRASES if phrase in name), None)
    if _verb_hit and name.find(_verb_hit) < 3 and not name.endswith(("责任", "能力", "条件", "资格", "资质")):
        return False
    if name.startswith(("但", "下列", "以下", "进一步")):
        return False
    # 领域关键字命中：直接通过（快速正向通道）
    if len(name) >= 4 and any(keyword in name for keyword in DOMAIN_KEYWORDS):
        return True
    # 只对较短名称（<8字）检查坏后缀（如"进一步推进"），长名称可能是合法复合名词
    if len(name) < 8 and name.endswith(BAD_SUFFIXES):
        return False
    # 通用领域默认接受：凡通过上述结构化噪声过滤的名词性词条均视为有效实体，
    # 不再要求其必须命中法规/财会等特定领域的后缀或关键字（适配任意文本抽取）。
    return True


def clean_entity_record(entity: dict) -> dict | None:
    name = normalize_entity_name(str(entity.get("name", "")))
    if not is_high_quality_entity_name(name):
        return None
    entity_type = (entity.get("type") or "概念").strip() or "概念"
    return {**entity, "name": name, "type": entity_type}
