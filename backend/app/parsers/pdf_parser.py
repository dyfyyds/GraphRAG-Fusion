import pdfplumber
from app.parsers.base import BaseParser, ParsedContent


class PDFParser(BaseParser):
    def parse(self, file_path: str) -> ParsedContent:
        content = ParsedContent()
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                content.text += text + "\n"
                content.page_map.append({"page": i, "text": text})
                tables = page.extract_tables()
                for table in tables:
                    content.tables.append(table)
        return content
