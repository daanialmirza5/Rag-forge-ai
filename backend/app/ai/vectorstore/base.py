"""Vector store abstraction. Points are keyed by `document_chunks.vector_id`
(see `docs/DATABASE.md`) — the store holds embeddings + a small payload for
filtering; chunk text and all other metadata live in Postgres.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class VectorPoint:
    id: uuid.UUID
    vector: list[float]
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class VectorSearchResult:
    id: uuid.UUID
    score: float
    payload: dict[str, Any]


class VectorStore(ABC):
    @abstractmethod
    async def ensure_collection(self) -> None:
        """Idempotent: create the collection + payload indexes if they don't
        already exist. Safe to call on every process startup."""
        ...

    @abstractmethod
    async def upsert(self, points: list[VectorPoint]) -> None: ...

    @abstractmethod
    async def search(
        self,
        *,
        query_vector: list[float],
        workspace_id: uuid.UUID,
        top_k: int,
        score_threshold: float | None = None,
    ) -> list[VectorSearchResult]:
        """Always scoped to a single workspace — this is the tenant-isolation
        boundary for vector search (see `docs/DATABASE.md`)."""
        ...

    @abstractmethod
    async def delete_by_document(self, document_id: uuid.UUID) -> None:
        """Remove all points for a document (re-ingestion / deletion)."""
        ...
