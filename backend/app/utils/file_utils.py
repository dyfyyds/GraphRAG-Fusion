import os
import re
import unicodedata
import magic
from pathlib import Path

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def sanitize_filename(filename: str) -> str:
    """清洗文件名：去除路径分隔符、控制字符、特殊字符，防止路径穿越"""
    # 只取文件名部分，去除路径
    filename = Path(filename).name
    # Unicode 正规化
    filename = unicodedata.normalize("NFC", filename)
    # 去除控制字符
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)
    # 去除路径分隔符和危险字符
    filename = re.sub(r"[/\\:*?\"<>|]", "_", filename)
    # 去除前后空白和点号（防止隐藏文件）
    filename = filename.strip(". ")
    # 限制长度
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:190] + ext
    return filename or "unnamed"


def validate_file(file_path: str, file_size: int) -> tuple[bool, str]:
    ext = Path(file_path).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"不支持的文件类型: {ext}"

    if file_size > MAX_FILE_SIZE:
        return False, f"文件大小超过限制: {file_size / 1024 / 1024:.1f}MB > {MAX_FILE_SIZE / 1024 / 1024}MB"

    # 文件名安全检查
    filename = Path(file_path).name
    if ".." in filename or "/" in filename or "\\" in filename:
        return False, "文件名包含非法字符"

    return True, ""


def validate_file_content(file_bytes: bytes) -> tuple[bool, str]:
    try:
        mime = magic.from_buffer(file_bytes, mime=True)
        if mime not in ALLOWED_MIME_TYPES:
            return False, f"文件内容类型不匹配: {mime}"
    except Exception:
        # magic 库异常时拒绝文件（而非放行）
        return False, "文件内容类型检测失败"
    return True, ""
