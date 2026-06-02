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


def normalize_entity_name(name: str) -> str:
    name = (name or "").strip()
    name = name.strip(" \t\r\n，。；;：:、,.!?！？“”\"'`")
    name = ENUM_PREFIX_RE.sub("", name).strip()
    name = LEADING_NOISE_RE.sub("", name).strip()
    return name.strip(" \t\r\n，。；;：:、,.!?！？“”\"'`")


def is_high_quality_entity_name(name: str) -> bool:
    name = normalize_entity_name(name)
    if not name:
        return False
    if name in BAD_EXACT:
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
    # 领域关键字检查（优先于坏后缀，因为合法复合名词常见）
    if len(name) >= 4 and any(keyword in name for keyword in (
        # 采购/财务/行政
        "采购", "会计", "差旅", "会议", "资产", "安全生产", "非税", "票据",
        # 人力资源
        "人力", "招聘", "培训", "绩效", "薪酬", "考勤", "福利",
        # 财务/审计
        "财务", "审计", "预算", "报销", "发票", "税务",
        # 合规/风控
        "合规", "风险", "内控", "法务",
        # 质量管理
        "质量", "安全", "环保", "消防",
        # 行政/综合
        "行政", "档案", "印章", "公文", "接待",
        # IT/数字化
        "信息", "网络", "数据", "系统", "平台",
        # 合同/法务
        "合同", "协议", "招投标", "供应商",
    )):
        return True
    # 只对较短名称（<8字）检查坏后缀，长名称可能是合法复合名词
    if len(name) < 8 and name.endswith(BAD_SUFFIXES):
        return False
    if name.endswith(GOOD_SUFFIXES) or name.endswith(ORG_SUFFIXES):
        return True
    if re.search(r"\d", name) and re.search(r"[一-鿿]", name):
        return True
    return False


def clean_entity_record(entity: dict) -> dict | None:
    name = normalize_entity_name(str(entity.get("name", "")))
    if not is_high_quality_entity_name(name):
        return None
    entity_type = (entity.get("type") or "概念").strip() or "概念"
    return {**entity, "name": name, "type": entity_type}
