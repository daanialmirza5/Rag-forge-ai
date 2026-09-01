import voyageai

from app.ai.reranking.base import RerankProvider, RerankResult
from app.core.config import settings
from app.core.exceptions import UpstreamProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)


class VoyageRerankProvider(RerankProvider):
    def __init__(self) -> None:
        self._client = voyageai.AsyncClient(api_key=settings.VOYAGE_API_KEY)
        self._model = settings.RERANK_MODEL

    async def rerank(
        self, *, query: str, documents: list[str], top_n: int
    ) -> list[RerankResult]:
        if not documents:
            return []
        try:
            result = await self._client.rerank(
                query=query, documents=documents, model=self._model, top_k=top_n
            )
        except voyageai.error.VoyageError as exc:
            logger.error("voyage_rerank_failed", error=str(exc))
            raise UpstreamProviderError(f"Rerank provider error: {exc}") from exc

        return [
            RerankResult(index=item.index, relevance_score=item.relevance_score)
            for item in result.results
        ]
