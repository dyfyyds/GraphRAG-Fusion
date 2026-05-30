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


def validate_file(file_path: str, file_size: int) -> tuple[bool, str]:
    ext = Path(file_path).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"不支持的文件类型: {ext}"

    if file_size > MAX_FILE_SIZE:
        return False, f"文件大小超过限制: {file_size / 1024 / 1024:.1f}MB > {MAX_FILE_SIZE / 1024 / 1024}MB"

    return True, ""


def validate_file_content(file_bytes: bytes) -> tuple[bool, str]:
    try:
        mime = magic.from_buffer(file_bytes, mime=True)
        if mime not in ALLOWED_MIME_TYPES:
            return False, f"文件内容类型不匹配: {mime}"
    except Exception:
        pass
    return True, ""
