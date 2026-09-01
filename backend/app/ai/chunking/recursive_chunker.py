"""Recursive character-based chunker, splitting on paragraph/sentence/word
boundaries where possible (via `langchain-text-splitters`, a small standalone
package already pulled in transitively by `langgraph`). Operates per-page so
every chunk keeps an accurate `page_number` for citations.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ai.chunking.base import Chunk, Chunker
from app.ai.parsers.base import ParsedDocument
from app.core.config import settings

_CHARS_PER_TOKEN_ESTIMATE = 4


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN_ESTIMATE)


class RecursiveChunker(Chunker):
    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size or settings.CHUNK_SIZE_CHARS,
            chunk_overlap=chunk_overlap or settings.CHUNK_OVERLAP_CHARS,
        )

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        index = 0
        for page in document.pages:
            if not page.text.strip():
                continue
            for piece in self._splitter.split_text(page.text):
                if not piece.strip():
                    continue
                chunks.append(
                    Chunk(
                        chunk_index=index,
                        content=piece,
                        token_count=_estimate_tokens(piece),
                        page_number=page.page_number,
                    )
                )
                index += 1
        return chunks
