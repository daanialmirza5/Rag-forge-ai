"""Document parser abstraction.

A parser turns raw file bytes into a sequence of `ParsedPage`s — plain text
plus a 1-indexed page number (page 1 for formats without a page concept,
e.g. plain text/Markdown/HTML). Chunking (`app/ai/chunking/*`) operates on
the concatenated result but keeps page boundaries so chunks can carry an
accurate `page_number` for citations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ParsedPage:
    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    pages: list[ParsedPage] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text.strip())

    @property
    def is_empty(self) -> bool:
        return not self.full_text.strip()


class DocumentParser(ABC):
    @property
    @abstractmethod
    def supported_mime_types(self) -> set[str]: ...

    @abstractmethod
    def parse(self, file_bytes: bytes) -> ParsedDocument: ...
