from functools import lru_cache

from app.ai.reranking.base import RerankProvider
from app.core.config import settings
from app.core.exceptions import AppError


@lru_cache
def get_rerank_provider() -> RerankProvider:
    if settings.RERANK_PROVIDER == "voyage":
        from app.ai.reranking.voyage_provider import VoyageRerankProvider

        return VoyageRerankProvider()
    if settings.RERANK_PROVIDER == "none":
        from app.ai.reranking.noop_provider import NoOpRerankProvider

        return NoOpRerankProvider()
    raise AppError(f"Unknown rerank provider: {settings.RERANK_PROVIDER}")
