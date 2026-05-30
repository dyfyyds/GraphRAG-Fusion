from app.parsers.base import BaseParser, ParsedContent


class TxtParser(BaseParser):
    def parse(self, file_path: str) -> ParsedContent:
        content = ParsedContent()
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content.text = f.read()
        content.page_map.append({"page": 1, "text": content.text})
        return content
