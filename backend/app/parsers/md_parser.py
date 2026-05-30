from app.parsers.base import BaseParser, ParsedContent


class MdParser(BaseParser):
    def parse(self, file_path: str) -> ParsedContent:
        content = ParsedContent()
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
        content.text = raw
        content.page_map.append({"page": 1, "text": raw})
        return content
