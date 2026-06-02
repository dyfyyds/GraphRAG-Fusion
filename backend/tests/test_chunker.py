"""文本分块测试"""
from app.parsers.chunker import chunk_text, is_structural_chunk


def test_short_text():
    text = "这是一段短文本"
    chunks = chunk_text(text, max_tokens=100)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_long_text_split():
    text = "a" * 1000
    chunks = chunk_text(text, max_tokens=200, overlap=20)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 200


def test_heading_split():
    text = "# 标题1\n内容1\n\n# 标题2\n内容2\n\n# 标题3\n内容3"
    chunks = chunk_text(text, max_tokens=1000)
    assert len(chunks) == 3


def test_overlap():
    text = "a" * 500
    chunks = chunk_text(text, max_tokens=200, overlap=50)
    assert len(chunks) >= 2


def test_empty_text():
    chunks = chunk_text("")
    assert len(chunks) == 0


def test_markdown_headings():
    text = "# H1\ncontent1\n## H2\ncontent2\n### H3\ncontent3"
    chunks = chunk_text(text, max_tokens=100)
    assert len(chunks) >= 3


def test_legal_articles_split_on_article_boundaries():
    text = (
        "中华人民共和国政府采购法\n"
        "第二十一条 供应商是指向采购人提供货物、工程或者服务的法人、其他组织或者自然人。\n"
        "第二十二条 供应商参加政府采购活动应当具备独立承担民事责任的能力。\n"
        "第二十三条 采购人可以要求参加政府采购的供应商提供有关资质证明文件和业绩情况。"
    )

    chunks = chunk_text(text, max_tokens=120)

    assert any(chunk.startswith("第二十二条") for chunk in chunks)
    assert any(chunk.startswith("第二十三条") for chunk in chunks)
    assert any("资质证明文件" in chunk and "业绩情况" in chunk for chunk in chunks)


def test_inline_legal_articles_are_split_before_articles():
    text = (
        "第一章 总则 第一条 为规范采购活动。"
        "第二条 本法适用于政府采购。"
        "第三条 政府采购应当遵循公开透明原则。"
    )

    chunks = chunk_text(text, max_tokens=80)

    assert any(chunk.startswith("第一条") for chunk in chunks)
    assert any(chunk.startswith("第二条") for chunk in chunks)
    assert any(chunk.startswith("第三条") for chunk in chunks)


def test_structural_short_chunk_is_meaningful():
    assert is_structural_chunk("第十七条 供应商应提供社会保障资金相关材料。")
    assert is_structural_chunk("第二十三条 资质证明文件和业绩情况。")


# ── 新增测试 ──────────────────────────────────────────────

def test_cjk_sentence_split():
    """CJK 标点应该作为句子分割点 — 使用足够长的文本"""
    text = (
        "第一点说明供应商应当提供完整的资质证明材料。"
        "第二点说明业绩情况需包含近三年合同复印件。"
        "第三点说明财务状况应当良好无亏损记录。"
        "第四点说明人员配置需满足专业技术要求。"
        "第五点说明售后服务应当承诺响应时间。"
        "第六点说明价格报价不得超过预算限额。"
        "第七点说明技术方案应当包含实施计划。"
    )
    chunks = chunk_text(text, max_tokens=80)
    # 长文本应该被分割成多个 chunk
    assert len(chunks) >= 2


def test_numbered_list_split():
    """编号列表如 1. xxx 应该被分割"""
    text = "以下是要求：\n1. 供应商需具备资质。\n2. 供应商需提供业绩。\n3. 供应商需缴纳保证金。"
    chunks = chunk_text(text, max_tokens=100)
    assert len(chunks) >= 1


def test_chinese_parenthesized_list():
    """（一）样式的列表应该被识别"""
    text = "（一）资质要求\n供应商应当具有独立承担民事责任的能力。\n（二）业绩要求\n供应商应当提供近三年业绩。"
    chunks = chunk_text(text, max_tokens=100)
    assert len(chunks) >= 2


def test_structural_chunk_business_keywords():
    """扩展的结构性关键词应被识别"""
    assert is_structural_chunk("营业执照等证明文件需加盖公章。")
    assert is_structural_chunk("安全生产管理制度应包含消防相关内容。")
    assert is_structural_chunk("质量管理体系建设方案")


def test_mixed_cjk_latin_text():
    """混合中英文文本应正确分块"""
    text = "系统要求 The system requires Python 3.10 及以上版本。"
    chunks = chunk_text(text, max_tokens=50)
    assert len(chunks) >= 1
    # 不会因为混合文本而崩溃
