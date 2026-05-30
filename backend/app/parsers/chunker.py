import re


def _estimate_tokens(text: str) -> int:
    """估算 token 数: CJK 字符≈1 token, 英文单词≈1.3 token"""
    cjk = 0
    other = text
    for ch in text:
        if '一' <= ch <= '鿿' or '㐀' <= ch <= '䶿':
            cjk += 1
            other = other.replace(ch, '', 1)
    words = len(other.split())
    # 每个英文单词约 1.3 token
    return cjk + max(1, int(words * 1.3))


def chunk_text(text: str, max_tokens: int = 512, overlap: int = 64) -> list[str]:
    """标题优先切分 + 固定长度二次切分"""
    # 先按标题切分
    sections = re.split(r"(?=^#{1,6}\s)", text, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]

    chunks = []
    for section in sections:
        if _estimate_tokens(section) <= max_tokens and len(section) <= max_tokens:
            chunks.append(section)
        else:
            # 固定长度二次切分，带重叠
            start = 0
            step = max(1, max_tokens - overlap)
            while start < len(section):
                end = start + max_tokens
                chunk = section[start:end]
                if chunk.strip():
                    chunks.append(chunk.strip())
                start += step
    return chunks
