"""Embedding provider abstraction.

Providers distinguish query vs. document embedding calls where the
underlying model supports asymmetric embeddings (Voyage does, via
`input_type`) — this measurably improves retrieval quality over embedding
both sides the same way, so it's part of the interface rather than an
implementation detail.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vectors: list[list[float]]
    total_tokens: int = 0


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimensions(self) -> int: ...

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        """Embed chunk text for indexing."""
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embed a single search query."""
        ...
