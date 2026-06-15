import re


ARTICLE_RE = re.compile(r"^第[一二三四五六七八九十百千万零〇两0-9]+条(?:\s|　|$)")
STRUCTURAL_BOUNDARY_RE = re.compile(
    r"^(?:"
    r"#{1,6}\s+.+|"
    r"第[一二三四五六七八九十百千万零〇两0-9]+[章节编部分].*|"
    r"第[一二三四五六七八九十百千万零〇两0-9]+条(?:\s|　|$).*|"
    r"附件[0-9一二三四五六七八九十]*[：:].*|"
    r"[一二三四五六七八九十]+、.{2,80}|"
    r"（[一二三四五六七八九十0-9]+）.{2,80}"
    r")$"
)
INLINE_BOUNDARY_RE = re.compile(
    r"(?<!^)(?=(?:"
    r"第[一二三四五六七八九十百千万零〇两0-9]+[章节编部分]\s*|"
    r"第[一二三四五六七八九十百千万零〇两0-9]+条\s*|"
    r"附件[0-9一二三四五六七八九十]*[：:]"
    r"))"
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？；;])")
LIST_ITEM_RE = re.compile(r"(?=（[一二三四五六七八九十0-9]+）|[一二三四五六七八九十0-9]+[、.．])")

# 层级标题识别：章/编 为一级，节 为二级；Markdown #/## 一级，###/#### 二级
CHAPTER_HEADING_RE = re.compile(
    r"^(?:第[一二三四五六七八九十百千万零〇两0-9]+[章编]\s*\S{0,40}|#{1,2}\s+.+)$"
)
SECTION_HEADING_RE = re.compile(
    r"^(?:第[一二三四五六七八九十百千万零〇两0-9]+节\s*\S{0,40}|#{3,4}\s+.+)$"
)
BREADCRUMB_PREFIX = "【所属章节："
BREADCRUMB_RE = re.compile(r"^【所属章节：[^】]{0,120}】\n?")


def strip_breadcrumb(text: str) -> str:
    """移除分块开头的章节面包屑，返回原始正文（页码定位等场景使用）。"""
    return BREADCRUMB_RE.sub("", text or "", count=1)


def _clean_heading(line: str, max_len: int = 40) -> str:
    line = re.sub(r"^#{1,6}\s+", "", line.strip())
    line = line.strip(" 　:：")
    return line[:max_len]


def _estimate_tokens(text: str) -> int:
    """估算 token 数: CJK 字符≈1 token, 英文单词≈1.3 token, 标点不计"""
    cjk = 0
    other_chars: list[str] = []
    for ch in text:
        if "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿":
            cjk += 1
        elif ch.isalpha() or ch.isspace():
            other_chars.append(ch)
    words = len("".join(other_chars).split())
    return cjk + max(1, int(words * 1.3))


def _normalize_text(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _inject_inline_boundaries(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        parts = [part.strip() for part in INLINE_BOUNDARY_RE.split(line) if part and part.strip()]
        if len(parts) <= 1:
            lines.append(line)
        else:
            lines.extend(parts)
    return "\n".join(lines)


def _is_boundary(line: str) -> bool:
    line = line.strip()
    return bool(line and STRUCTURAL_BOUNDARY_RE.match(line))


def _split_sections(text: str) -> list[str]:
    text = _inject_inline_boundaries(_normalize_text(text))
    if not text:
        return []

    sections: list[str] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current and current[-1] != "":
                current.append("")
            continue

        if _is_boundary(line) and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)

    if current:
        sections.append("\n".join(current).strip())
    return [section for section in sections if section]


def _is_list_item(text: str) -> bool:
    """判断文本是否以列表项标记开头（如 （一）、1、 等）"""
    stripped = text.strip()
    return bool(LIST_ITEM_RE.match(stripped) or re.match(r"^[（(][一二三四五六七八九十0-9]+[）)]", stripped))


def _split_long_text(text: str, max_tokens: int, overlap: int) -> list[str]:
    if len(text) <= max_tokens and _estimate_tokens(text) <= max_tokens:
        return [text.strip()] if text.strip() else []

    units = []
    for paragraph in re.split(r"\n{2,}", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        list_parts = [part.strip() for part in LIST_ITEM_RE.split(paragraph) if part and part.strip()]
        if len(list_parts) > 1:
            # 保留列表项的上下文：将短列表项与其前缀合并，但列表项之间不合并
            prefix = ""
            for part in list_parts:
                if _is_list_item(part):
                    if prefix:
                        # 前缀作为独立 unit
                        units.append(prefix)
                        prefix = ""
                    units.append(part)
                else:
                    # 非列表项内容（如"第四条 ..."），作为前缀
                    if prefix:
                        units.append(prefix)
                    prefix = part
            if prefix:
                units.append(prefix)
        else:
            units.extend(part.strip() for part in SENTENCE_SPLIT_RE.split(paragraph) if part.strip())

    chunks: list[str] = []
    current = ""
    for unit in units:
        # 列表项不与前面内容合并，保持独立
        if _is_list_item(unit) and current:
            chunks.append(current)
            current = unit
            continue
        candidate = f"{current}\n{unit}".strip() if current else unit
        if len(candidate) <= max_tokens and _estimate_tokens(candidate) <= max_tokens:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(unit) <= max_tokens:
            current = unit
        else:
            chunks.extend(_fixed_window_split(unit, max_tokens, overlap))
            current = ""
    if current:
        chunks.append(current)
    return chunks


def _fixed_window_split(text: str, max_tokens: int, overlap: int) -> list[str]:
    chunks = []
    start = 0
    step = max(1, max_tokens - overlap)
    while start < len(text):
        chunk = text[start:start + max_tokens].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


def _merge_tiny_chunks(chunks: list[str], min_chars: int = 40, max_tokens: int = 512) -> list[str]:
    merged: list[str] = []
    pending = ""
    for chunk in chunks:
        first_line = chunk.splitlines()[0].strip() if chunk.strip() else ""
        is_structural = _is_boundary(first_line)
        is_list = _is_list_item(first_line)
        # 列表项和结构性内容不合并，保持独立
        if len(chunk) < min_chars and not is_structural and not is_list:
            pending = f"{pending}\n{chunk}".strip() if pending else chunk
            continue
        if pending:
            candidate = f"{pending}\n{chunk}".strip()
            if len(candidate) <= max_tokens and _estimate_tokens(candidate) <= max_tokens and not is_list:
                chunk = candidate
                pending = ""
            else:
                merged.append(pending)
                pending = ""
        merged.append(chunk)
    if pending:
        if merged and len(f"{merged[-1]}\n{pending}") <= max_tokens:
            merged[-1] = f"{merged[-1]}\n{pending}".strip()
        else:
            merged.append(pending)
    return merged


def is_structural_chunk(text: str) -> bool:
    """Whether a short chunk is meaningful enough to keep despite min_chunk_size."""
    stripped = (text or "").strip()
    if not stripped:
        return False
    if ARTICLE_RE.match(stripped):
        return True
    if re.search(r"《[^》]{2,80}》|[〔\[]\d{4}[〕\]]\d+号|第[一二三四五六七八九十百千万零〇两0-9]+条", stripped):
        return True
    if re.search(
        r"(资质证明文件|业绩情况|法人资格|民事责任|社会保障资金|声明函|评审依据|"
        r"营业执照|安全生产|质量管理|风险管理|内部控制|合规管理|"
        r"人力资源|财务管理|合同管理|项目管理|档案管理|"
        r"供应商|采购人|代理机构|总公司|分公司)",
        stripped,
    ):
        return True
    return False


def _sections_with_breadcrumbs(sections: list[str]) -> list[tuple[str, str]]:
    """遍历切分后的章节块，跟踪当前 章/编 与 节 标题，为每块计算层级面包屑。

    解决扁平化分块丢失文档层级关系的问题：每个条款块都能携带
    “第X章 YYY > 第X节 ZZZ”的归属信息，跨文档检索时不再失去上下文。
    """
    chapter = ""
    section_heading = ""
    out: list[tuple[str, str]] = []
    for sec in sections:
        first_line = sec.splitlines()[0].strip() if sec.strip() else ""
        if CHAPTER_HEADING_RE.match(first_line):
            chapter = _clean_heading(first_line)
            section_heading = ""
            breadcrumb = ""  # 章标题块自身无需前缀
        elif SECTION_HEADING_RE.match(first_line):
            section_heading = _clean_heading(first_line)
            breadcrumb = chapter
        else:
            breadcrumb = " > ".join(x for x in (chapter, section_heading) if x)
        out.append((breadcrumb, sec))
    return out


def chunk_text(text: str, max_tokens: int = 512, overlap: int = 64) -> list[str]:
    """结构化切分：标题/章/条/附件优先，长块按款项和句子二次切分。

    每个分块前置【所属章节】层级面包屑，保留文档层级上下文。
    """
    text = _normalize_text(text)
    if not text:
        return []

    sections = _split_sections(text)
    if not sections:
        sections = [text]

    # 切分并记录每块的层级归属
    tagged: list[tuple[str, str]] = []
    for breadcrumb, section in _sections_with_breadcrumbs(sections):
        for piece in _split_long_text(section, max_tokens=max_tokens, overlap=overlap):
            piece = piece.strip()
            if piece:
                tagged.append((breadcrumb, piece))

    # 小块合并仅在同一面包屑分组内进行，避免跨章节混淆上下文
    final: list[str] = []
    i = 0
    while i < len(tagged):
        breadcrumb = tagged[i][0]
        group = []
        while i < len(tagged) and tagged[i][0] == breadcrumb:
            group.append(tagged[i][1])
            i += 1
        for merged in _merge_tiny_chunks(group, max_tokens=max_tokens):
            if breadcrumb and BREADCRUMB_PREFIX not in merged:
                final.append(f"{BREADCRUMB_PREFIX}{breadcrumb}】\n{merged}")
            else:
                final.append(merged)
    return final
