from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.ai.parsers.base import ParsedDocument


@dataclass(frozen=True, slots=True)
class Chunk:
    chunk_index: int
    content: str
    token_count: int
    page_number: int | None


class Chunker(ABC):
    @abstractmethod
    def chunk(self, document: ParsedDocument) -> list[Chunk]: ...
