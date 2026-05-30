"""分页工具测试"""
from app.utils.pagination import PageParams, PageResult


def test_page_params_default():
    p = PageParams()
    assert p.page == 1
    assert p.page_size == 20
    assert p.offset == 0


def test_page_params_offset():
    p = PageParams(page=3, page_size=10)
    assert p.offset == 20


def test_page_result_create():
    result = PageResult.create(items=[1, 2, 3], total=100, page=1, page_size=20)
    assert result.pages == 5
    assert len(result.items) == 3
    assert result.total == 100


def test_page_result_zero_page_size():
    result = PageResult.create(items=[], total=0, page=1, page_size=0)
    assert result.pages == 0
