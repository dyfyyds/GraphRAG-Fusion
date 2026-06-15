from app.core.entity_quality import clean_entity_record, is_high_quality_entity_name, normalize_entity_name
from app.core.graph_build_service import (
    _fallback_extract,
    _rule_extract_domain_context,
    _rule_extract_legal_context,
    _split_text_for_extraction,
)


def test_rejects_predicate_fragment_entities():
    assert not is_high_quality_entity_name("进一步规范")
    assert not is_high_quality_entity_name("以下情形")
    assert not is_high_quality_entity_name("有关问题")


def test_normalizes_leading_noise_before_entity_name():
    assert normalize_entity_name("但下列行政事业性收费项目") == "行政事业性收费项目"
    assert clean_entity_record({"name": "但下列行政事业性收费项目", "type": "概念"}) == {
        "name": "行政事业性收费项目",
        "type": "概念",
    }


def test_keeps_legal_documents_and_codes():
    assert is_high_quality_entity_name("《政府采购法实施条例》")
    assert is_high_quality_entity_name("财库〔2020〕46号")
    assert is_high_quality_entity_name("财政部令第87号")
    assert is_high_quality_entity_name("第二十二条")


def test_accepts_fine_grained_policy_entities():
    assert is_high_quality_entity_name("行政事业性收费项目")
    assert is_high_quality_entity_name("政府会计准则制度新旧衔接")
    assert is_high_quality_entity_name("工会经费")
    assert is_high_quality_entity_name("评标标准")
    assert is_high_quality_entity_name("社保材料")
    assert is_high_quality_entity_name("授权文件")


def test_fallback_extract_filters_low_quality_fragments():
    extracted = _fallback_extract(
        "进一步规范政府采购管理。但下列行政事业性收费项目应当按照财政部令第87号执行。"
    )
    names = {item["name"] for item in extracted["entities"]}

    assert "进一步规范" not in names
    assert "但下列行政事业性收费项目" not in names
    assert "行政事业性收费项目" in names


def test_rule_extracts_branch_company_legal_relations():
    extracted = _rule_extract_legal_context(
        "中华人民共和国公司法 第十三条 公司可以设立分公司。"
        "分公司不具有法人资格，其民事责任由公司承担。"
    )
    names = {item["name"] for item in extracted["entities"]}
    relations = {
        (item["source"], item["type"], item["target"])
        for item in extracted["relations"]
    }

    assert "总公司" in names
    assert "分公司" in names
    assert ("分公司", "不具有", "法人资格") in relations
    assert ("总公司", "设立", "分公司") in relations
    assert ("总公司", "承担", "民事责任") in relations


def test_rule_extracts_procurement_material_relations():
    extracted = _rule_extract_legal_context(
        "中华人民共和国政府采购法 第二十二条 供应商应当具有独立承担民事责任的能力。"
        "第二十三条 采购人可以要求参加政府采购的供应商提供有关资质证明文件和业绩情况。"
    )
    names = {item["name"] for item in extracted["entities"]}
    relations = {
        (item["source"], item["type"], item["target"])
        for item in extracted["relations"]
    }

    assert "资质证明文件" in names
    assert "业绩情况" in names
    assert ("第二十三条", "要求提供", "资质证明文件") in relations
    assert ("采购人", "要求提供", "业绩情况") in relations


def test_domain_rule_extracts_fine_grained_entities_and_relations():
    extracted = _rule_extract_domain_context(
        "财会〔2018〕34号 财政部关于进一步做好政府会计准则制度新旧衔接和加强行政事业单位资产核算的通知。"
        "但下列行政事业性收费项目应当按照非税收入和票据管理规定执行。"
        "第十七条 供应商应提供资质证明、业绩证明、设备证明、人员证明、授权文件、劳动合同和社保材料。"
    )
    names = {item["name"] for item in extracted["entities"]}
    relations = {
        (item["source"], item["type"], item["target"])
        for item in extracted["relations"]
    }

    assert "财会〔2018〕34号" in names
    assert "第十七条" in names
    assert "政府会计准则制度新旧衔接" in names
    assert "行政事业性收费项目" in names
    assert "资质证明" in names
    assert "业绩证明" in names
    assert "设备证明" in names
    assert "人员证明" in names
    assert "社保材料" in names
    assert any(source == "第十七条" and target == "社保材料" for source, _, target in relations)


def test_extraction_split_uses_structural_boundaries():
    text = "\n".join(
        [
            "第一条 供应商应当提供资质证明文件。",
            "第二条 采购人可以要求供应商提供业绩情况。",
            "第三条 分公司不具有法人资格。",
        ]
    )
    sections = _split_text_for_extraction(text, 40)
    assert len(sections) >= 2
    assert all(len(section) <= 40 for section in sections)


# ── 新增测试：扩展的领域关键字 ──────────────────────────

def test_accepts_general_business_entities():
    """确保通用企业文档实体不被误过滤"""
    assert is_high_quality_entity_name("财务管理制度")
    assert is_high_quality_entity_name("人力资源管理办法")
    assert is_high_quality_entity_name("安全生产管理制度")
    assert is_high_quality_entity_name("合同管理办法")
    assert is_high_quality_entity_name("质量管理体系")
    assert is_high_quality_entity_name("风险控制流程")


def test_accepts_new_good_suffixes():
    """新扩展的后缀应该被接受"""
    assert is_high_quality_entity_name("年度经营计划")
    assert is_high_quality_entity_name("供应商评估报告")
    assert is_high_quality_entity_name("员工培训档案")
    assert is_high_quality_entity_name("固定资产台账")
    assert is_high_quality_entity_name("公司管理章程")


def test_long_compound_nouns_with_verb_suffix_are_accepted():
    """长复合名词即使包含动词后缀也应被接受"""
    assert is_high_quality_entity_name("安全生产技术规范")
    assert is_high_quality_entity_name("内部控制管理制度")
    assert is_high_quality_entity_name("绩效考核管理办法")


def test_verb_at_start_rejected():
    """谓语开头仍应被拒绝（谓语片段特征）"""
    assert not is_high_quality_entity_name("应当提交以下材料")
    assert not is_high_quality_entity_name("可以要求供应商提供")


def test_accepts_general_domain_entities():
    """通用领域实体（非法规/财会）也应被接受，适配任意文本抽取。"""
    for name in ["爱因斯坦", "光合作用", "万有引力定律", "Python", "三体", "长江", "区块链", "细胞膜", "文艺复兴", "神经网络"]:
        assert is_high_quality_entity_name(name), f"通用实体被误过滤: {name}"


def test_still_rejects_generic_stopwords_and_fragments():
    """放宽领域限制后，仍应拒绝无检索价值的孤立词和谓语片段。"""
    for name in ["内容", "方面", "情况", "问题", "进一步规范", "以下情形", "应当提交以下材料"]:
        assert not is_high_quality_entity_name(name), f"噪声词未被过滤: {name}"


def test_prompt_template_formats_without_error():
    """系统提示词应能正常注入类型配置（验证占位符与花括号转义正确）。"""
    from app.core.graph_build_service import EXTRACT_SYSTEM_PROMPT, EXTRACT_USER_TEMPLATE

    rendered = EXTRACT_SYSTEM_PROMPT.format(
        entity_types_section="\n- 允许的节点标签：人物、组织",
        relation_types_section="\n- 允许的关系类型：属于、包含",
    )
    assert "知识图谱抽取器" in rendered
    assert "人物、组织" in rendered
    user = EXTRACT_USER_TEMPLATE.format(text="示例文本")
    assert '"entities"' in user and "示例文本" in user


def test_properties_in_clean_entity_record():
    """clean_entity_record 应保留 properties 字段"""
    result = clean_entity_record({
        "name": "第二十二条",
        "type": "条款",
        "properties": {"articleNumber": "22"},
    })
    assert result is not None
    assert result["name"] == "第二十二条"
    assert result["type"] == "条款"
    assert result["properties"] == {"articleNumber": "22"}
