"""图谱导入解析测试（纯函数，无需 Neo4j / LLM）。"""
import json
import pytest

from app.core.graph_import_service import (
    _split_triple_line,
    _looks_like_triples,
    _parse_json,
    _parse_triple_lines,
    parse_import_file,
)


def test_split_triple_line_separators():
    assert _split_triple_line("供应商 | 提供 | 资质证明文件") == ["供应商", "提供", "资质证明文件"]
    assert _split_triple_line("A -> 关联 -> B") == ["A", "关联", "B"]
    assert _split_triple_line("甲\t隶属\t乙") == ["甲", "隶属", "乙"]
    assert _split_triple_line("源，关系，目标") == ["源", "关系", "目标"]
    assert _split_triple_line("单独实体") is None  # 无分隔符


def test_looks_like_triples_detects_structured_vs_prose():
    triples = ["A | 含 | B", "C | 属于 | D", "E | 使用 | F"]
    prose = [
        "这是一段普通的说明文字，用来描述某个概念的来龙去脉。",
        "它没有任何三元组结构，应当被判定为正文走 LLM 抽取。",
    ]
    assert _looks_like_triples(triples) is True
    assert _looks_like_triples(prose) is False
    assert _looks_like_triples([]) is False


def test_parse_json_object_form():
    raw = json.dumps({
        "entities": [{"name": "爱因斯坦", "type": "人物"}, {"name": "相对论", "entity_type": "理论"}],
        "relations": [{"source": "爱因斯坦", "target": "相对论", "type": "提出"}],
        "synonyms": [{"original": "相对论", "synonym": "Relativity"}],
    }, ensure_ascii=False)
    data = _parse_json(raw)
    assert {e["name"] for e in data["entities"]} == {"爱因斯坦", "相对论"}
    assert data["relations"][0] == {"source": "爱因斯坦", "target": "相对论", "type": "提出", "description": ""}
    assert data["synonyms"][0]["synonym"] == "Relativity"


def test_parse_json_triple_array_form():
    raw = json.dumps([["A", "关联", "B"], {"source": "C", "target": "D", "relation": "包含"}], ensure_ascii=False)
    data = _parse_json(raw)
    assert len(data["relations"]) == 2
    assert data["relations"][0]["source"] == "A"
    assert data["relations"][1]["type"] == "包含"


def test_parse_triple_lines_relations_and_entities():
    lines = ["供应商 | 提供 | 资质证明文件 | 依据第二十三条", "孤立实体"]
    data = _parse_triple_lines(lines)
    assert data["relations"][0]["source"] == "供应商"
    assert data["relations"][0]["target"] == "资质证明文件"
    assert data["relations"][0]["description"] == "依据第二十三条"
    assert any(e["name"] == "孤立实体" for e in data["entities"])


@pytest.mark.asyncio
async def test_parse_import_file_json_mode():
    raw = json.dumps({"entities": [{"name": "长江"}], "relations": []}, ensure_ascii=False).encode("utf-8")
    data = await parse_import_file("graph.json", raw)
    assert data["mode"] == "json"
    assert data["entities"][0]["name"] == "长江"


@pytest.mark.asyncio
async def test_parse_import_file_txt_triples_mode():
    content = "供应商 | 提供 | 资质证明文件\n采购人 | 要求 | 业绩情况\n".encode("utf-8")
    data = await parse_import_file("triples.txt", content)
    assert data["mode"] == "txt"
    assert len(data["relations"]) == 2
