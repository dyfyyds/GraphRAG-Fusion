"""文件校验工具测试"""
from app.utils.file_utils import validate_file, MAX_FILE_SIZE


def test_validate_pdf():
    valid, msg = validate_file("test.pdf", 1024)
    assert valid is True


def test_validate_docx():
    valid, msg = validate_file("test.docx", 1024)
    assert valid is True


def test_validate_txt():
    valid, msg = validate_file("test.txt", 1024)
    assert valid is True


def test_validate_md():
    valid, msg = validate_file("test.md", 1024)
    assert valid is True


def test_validate_unsupported_type():
    valid, msg = validate_file("test.exe", 1024)
    assert valid is False
    assert "不支持" in msg


def test_validate_oversized():
    valid, msg = validate_file("test.pdf", MAX_FILE_SIZE + 1)
    assert valid is False
    assert "超过限制" in msg


def test_validate_exact_limit():
    valid, msg = validate_file("test.pdf", MAX_FILE_SIZE)
    assert valid is True
