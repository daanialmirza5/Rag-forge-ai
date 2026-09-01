"""Passthrough reranker — the free-tier fallback when no rerank API is
configured (`RERANK_PROVIDER=none`). Returns the input order unchanged
(truncated to `top_n`) rather than actually re-scoring anything.

Hybrid retrieval's Reciprocal Rank Fusion already produces a reasonable
ordering; this just means that ordering isn't refined by a cross-encoder
pass. Real relevance scores aren't available without an actual reranker, so
`relevance_score` here is a decreasing placeholder purely to preserve the
"most-relevant first" contract callers rely on for sorting/display.
"""

from app.ai.reranking.base import RerankProvider, RerankResult


class NoOpRerankProvider(RerankProvider):
    async def rerank(
        self, *, query: str, documents: list[str], top_n: int
    ) -> list[RerankResult]:
        return [
            RerankResult(index=i, relevance_score=1.0 - (i / max(len(documents), 1)))
            for i in range(min(len(documents), top_n))
        ]
