"""Hybrid retrieval: dense (Qdrant cosine) + sparse (BM25) search, fused with
Reciprocal Rank Fusion (RRF). RRF combines two differently-scaled rankings
by rank position rather than raw score, which sidesteps having to normalize
cosine similarity against BM25 scores onto a common scale.
"""

import asyncio
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.factory import get_embedding_provider
from app.ai.retrieval.bm25_index import sparse_search
from app.ai.vectorstore.factory import get_vector_store

_RRF_K = 60


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: uuid.UUID
    fused_score: float


def _reciprocal_rank_fusion(*rankings: list[uuid.UUID]) -> list[RetrievedChunk]:
    scores: dict[uuid.UUID, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (_RRF_K + rank + 1)
    ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    return [RetrievedChunk(chunk_id=chunk_id, fused_score=score) for chunk_id, score in ranked]


async def hybrid_retrieve(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    query: str,
    dense_top_k: int = 50,
    sparse_top_k: int = 50,
    fused_top_k: int = 30,
) -> list[RetrievedChunk]:
    query_vector = await get_embedding_provider().embed_query(query)

    dense_results, sparse_results = await asyncio.gather(
        get_vector_store().search(
            query_vector=query_vector, workspace_id=workspace_id, top_k=dense_top_k
        ),
        sparse_search(db, workspace_id=workspace_id, query=query, top_k=sparse_top_k),
    )

    dense_ranking = [uuid.UUID(r.payload["chunk_id"]) for r in dense_results]
    sparse_ranking = [r.chunk_id for r in sparse_results]

    fused = _reciprocal_rank_fusion(dense_ranking, sparse_ranking)
    return fused[:fused_top_k]
