from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedContent:
    text: str = ""
    page_map: list[dict] = field(default_factory=list)  # [{page: 1, text: "..."}]
    tables: list[list[list[str]]] = field(default_factory=list)


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> ParsedContent:
        ...
