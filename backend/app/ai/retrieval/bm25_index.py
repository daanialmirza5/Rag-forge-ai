"""BM25 sparse (keyword) search over a workspace's chunks.

The index is built on demand from Postgres rather than maintained as a
separate persistent structure — simplest thing that works, and fast enough
(milliseconds) for a workspace with up to tens of thousands of chunks.

A tiny in-process cache avoids re-tokenizing on every query for the common
case where the workspace hasn't changed since the last search. Cache
staleness is tracked via a **Redis-backed version counter** rather than a
local heuristic (e.g. chunk count) — ingestion runs in a separate Celery
worker *process* from the FastAPI web process, so a purely in-memory
invalidation call from the worker would never reach the web process's
cache. Both processes read/increment the same Redis key, so the web
process's cache correctly detects staleness after the worker finishes
(re)ingesting a document, no cross-process signaling beyond Redis needed.
"""

import re
import uuid
from collections import OrderedDict
from dataclasses import dataclass

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis_client
from app.models.chunk import DocumentChunk

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_CACHE_MAX_WORKSPACES = 32


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _version_key(workspace_id: uuid.UUID) -> str:
    return f"bm25:version:{workspace_id}"


async def get_bm25_version(workspace_id: uuid.UUID) -> int:
    value = await get_redis_client().get(_version_key(workspace_id))
    return int(value) if value else 0


async def invalidate_workspace_bm25_cache(workspace_id: uuid.UUID) -> None:
    """Call after ingestion writes or deletes chunks for a workspace."""
    await get_redis_client().incr(_version_key(workspace_id))


@dataclass(frozen=True, slots=True)
class SparseSearchResult:
    chunk_id: uuid.UUID
    score: float


class _WorkspaceBM25Cache:
    def __init__(self, maxsize: int = _CACHE_MAX_WORKSPACES) -> None:
        self._entries: OrderedDict[uuid.UUID, tuple[int, BM25Okapi | None, list[uuid.UUID]]] = (
            OrderedDict()
        )
        self._maxsize = maxsize

    def get(self, workspace_id: uuid.UUID, version: int) -> tuple[BM25Okapi | None, list[uuid.UUID]] | None:
        cached = self._entries.get(workspace_id)
        if cached is not None and cached[0] == version:
            self._entries.move_to_end(workspace_id)
            return cached[1], cached[2]
        return None

    def put(
        self,
        workspace_id: uuid.UUID,
        version: int,
        bm25: BM25Okapi | None,
        chunk_ids: list[uuid.UUID],
    ) -> None:
        self._entries[workspace_id] = (version, bm25, chunk_ids)
        self._entries.move_to_end(workspace_id)
        if len(self._entries) > self._maxsize:
            self._entries.popitem(last=False)


_cache = _WorkspaceBM25Cache()


async def sparse_search(
    db: AsyncSession, *, workspace_id: uuid.UUID, query: str, top_k: int
) -> list[SparseSearchResult]:
    version = await get_bm25_version(workspace_id)

    cached = _cache.get(workspace_id, version)
    if cached is None:
        result = await db.execute(
            select(DocumentChunk.id, DocumentChunk.content).where(
                DocumentChunk.workspace_id == workspace_id
            )
        )
        rows = [(row.id, row.content) for row in result.all()]
        chunk_ids = [row[0] for row in rows]
        bm25 = BM25Okapi([_tokenize(row[1]) for row in rows]) if rows else None
        _cache.put(workspace_id, version, bm25, chunk_ids)
        cached = (bm25, chunk_ids)

    bm25, chunk_ids = cached
    if bm25 is None:
        return []

    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(zip(chunk_ids, scores, strict=True), key=lambda pair: pair[1], reverse=True)
    return [
        SparseSearchResult(chunk_id=chunk_id, score=float(score))
        for chunk_id, score in ranked[:top_k]
    ]
