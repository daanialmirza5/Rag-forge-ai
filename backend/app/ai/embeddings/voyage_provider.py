"""Voyage AI embedding provider — Anthropic's recommended embedding partner.

Batches requests at Voyage's documented per-request text limit (128) since
ingestion can pass in an arbitrarily large chunk list.
"""

import voyageai

from app.ai.embeddings.base import EmbeddingProvider, EmbeddingResult
from app.core.config import settings
from app.core.exceptions import UpstreamProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)

_MAX_TEXTS_PER_REQUEST = 128


class VoyageEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self._client = voyageai.AsyncClient(api_key=settings.VOYAGE_API_KEY)
        self._model = settings.EMBEDDING_MODEL
        self._dimensions = settings.EMBEDDING_DIMENSIONS

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(vectors=[], total_tokens=0)

        vectors: list[list[float]] = []
        total_tokens = 0
        for i in range(0, len(texts), _MAX_TEXTS_PER_REQUEST):
            batch = texts[i : i + _MAX_TEXTS_PER_REQUEST]
            try:
                result = await self._client.embed(
                    texts=batch,
                    model=self._model,
                    input_type="document",
                    output_dimension=self._dimensions,
                )
            except voyageai.error.VoyageError as exc:
                logger.error("voyage_embed_documents_failed", error=str(exc))
                raise UpstreamProviderError(f"Embedding provider error: {exc}") from exc
            # `result.embeddings` is `list[list[float]] | list[list[int]]` in the SDK's
            # typing to account for quantized `output_dtype`s; we never set that, so
            # values are always float, but normalize explicitly to keep our own
            # interface's type (`list[list[float]]`) honest.
            vectors.extend([float(x) for x in vec] for vec in result.embeddings)
            total_tokens += result.total_tokens

        return EmbeddingResult(vectors=vectors, total_tokens=total_tokens)

    async def embed_query(self, text: str) -> list[float]:
        try:
            result = await self._client.embed(
                texts=[text],
                model=self._model,
                input_type="query",
                output_dimension=self._dimensions,
            )
        except voyageai.error.VoyageError as exc:
            logger.error("voyage_embed_query_failed", error=str(exc))
            raise UpstreamProviderError(f"Embedding provider error: {exc}") from exc
        return [float(x) for x in result.embeddings[0]]
