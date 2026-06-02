from app.services.graph_service import _apply_python_limit, _limit_clause, _parse_props
from app.core.graph_build_service import _merge_extraction_data


def test_limit_zero_means_unlimited():
    items = [{"id": 1}, {"id": 2}, {"id": 3}]

    assert _limit_clause(0) == ""
    assert _apply_python_limit(items, 0) == items


def test_positive_limit_still_applies():
    items = [{"id": 1}, {"id": 2}, {"id": 3}]

    assert _limit_clause(2) == " LIMIT $limit"
    assert _apply_python_limit(items, 2) == [{"id": 1}, {"id": 2}]


def test_parse_props_valid_json():
    """解析有效的 JSON 属性字符串"""
    assert _parse_props('{"amount": "100万", "articleNumber": "22"}') == {
        "amount": "100万",
        "articleNumber": "22",
    }


def test_parse_props_empty_or_invalid():
    """空值或非法 JSON 应返回空字典"""
    assert _parse_props(None) == {}
    assert _parse_props("") == {}
    assert _parse_props("not json") == {}
    assert _parse_props('"just a string"') == {}


def test_parse_props_non_dict_json():
    """非字典的合法 JSON 应返回空字典"""
    assert _parse_props("[1, 2, 3]") == {}
    assert _parse_props("123") == {}


def test_merge_extraction_deduplicates_by_normalized_name():
    """合并抽取结果应去重"""
    primary = {
        "entities": [{"name": "供应商", "type": "主体"}],
        "relations": [{"source": "供应商", "target": "资质证明文件", "type": "要求提供"}],
        "synonyms": [{"original": "中华人民共和国政府采购法", "synonym": "政府采购法"}],
    }
    supplemental = {
        "entities": [{"name": "供应商", "type": "主体"}],  # 重复
        "relations": [{"source": "供应商", "target": "资质证明文件", "type": "要求提供"}],  # 重复
        "synonyms": [{"original": "中华人民共和国政府采购法", "synonym": "政府采购法"}],  # 重复
    }
    merged = _merge_extraction_data(primary, supplemental)
    assert len(merged["entities"]) == 1
    assert len(merged["relations"]) == 1
    assert len(merged["synonyms"]) == 1


def test_merge_extraction_adds_new_entries():
    """合并应添加新条目"""
    primary = {
        "entities": [{"name": "供应商", "type": "主体"}],
        "relations": [],
        "synonyms": [],
    }
    supplemental = {
        "entities": [{"name": "采购人", "type": "主体"}],
        "relations": [],
        "synonyms": [],
    }
    merged = _merge_extraction_data(primary, supplemental)
    assert len(merged["entities"]) == 2
    assert {e["name"] for e in merged["entities"]} == {"供应商", "采购人"}
