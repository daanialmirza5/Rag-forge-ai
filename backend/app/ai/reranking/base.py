from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RerankResult:
    index: int
    """Index into the original `documents` list passed to `rerank()`."""
    relevance_score: float


class RerankProvider(ABC):
    @abstractmethod
    async def rerank(
        self, *, query: str, documents: list[str], top_n: int
    ) -> list[RerankResult]:
        """Returns up to `top_n` results, ordered most-relevant first."""
        ...
