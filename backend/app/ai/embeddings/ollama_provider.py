"""Ollama embedding provider — a free, fully local alternative to Voyage AI.

Unlike Voyage, Ollama embedding models don't support an `input_type`
query/document distinction or arbitrary `output_dimension` truncation — the
vector size is fixed per model (e.g. 768 for `nomic-embed-text`). Whoever sets
`EMBEDDING_PROVIDER=ollama` must also set `EMBEDDING_DIMENSIONS` to match the
chosen model, since that's what `QdrantVectorStore` creates its collection
with.
"""

import httpx

from app.ai.embeddings.base import EmbeddingProvider, EmbeddingResult
from app.core.config import settings
from app.core.exceptions import UpstreamProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.OLLAMA_BASE_URL, timeout=120.0)
        self._model = settings.EMBEDDING_MODEL
        self._dimensions = settings.EMBEDDING_DIMENSIONS

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def _embed(self, texts: list[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(vectors=[], total_tokens=0)
        try:
            response = await self._client.post(
                "/api/embed", json={"model": self._model, "input": texts}
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("ollama_embed_failed", error=str(exc))
            raise UpstreamProviderError(f"Embedding provider error: {exc}") from exc

        data = response.json()
        vectors = [[float(x) for x in vec] for vec in data["embeddings"]]
        total_tokens = data.get("prompt_eval_count", 0)
        return EmbeddingResult(vectors=vectors, total_tokens=total_tokens)

    async def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        return await self._embed(texts)

    async def embed_query(self, text: str) -> list[float]:
        result = await self._embed([text])
        return result.vectors[0]
