"""文本分块测试"""
from app.parsers.chunker import chunk_text


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
