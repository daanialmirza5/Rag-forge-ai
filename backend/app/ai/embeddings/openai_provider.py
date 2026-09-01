"""OpenAI embedding provider — alternative to Voyage, selected via
`EMBEDDING_PROVIDER=openai`. The `openai` package is not a hard dependency of
this project (Voyage is the default and the only one installed by default);
it's imported lazily so choosing Voyage never requires installing it.
"""

from app.ai.embeddings.base import EmbeddingProvider, EmbeddingResult
from app.core.config import settings
from app.core.exceptions import UpstreamProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)

_MAX_TEXTS_PER_REQUEST = 2048  # OpenAI's documented per-request array limit


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=openai requires the `openai` package: "
                "pip install openai"
            ) from exc

        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.EMBEDDING_MODEL
        self._dimensions = settings.EMBEDDING_DIMENSIONS

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(vectors=[], total_tokens=0)

        import openai

        vectors: list[list[float]] = []
        total_tokens = 0
        for i in range(0, len(texts), _MAX_TEXTS_PER_REQUEST):
            batch = texts[i : i + _MAX_TEXTS_PER_REQUEST]
            try:
                response = await self._client.embeddings.create(
                    input=batch, model=self._model, dimensions=self._dimensions
                )
            except openai.OpenAIError as exc:
                logger.error("openai_embed_documents_failed", error=str(exc))
                raise UpstreamProviderError(f"Embedding provider error: {exc}") from exc
            vectors.extend(item.embedding for item in response.data)
            total_tokens += response.usage.total_tokens

        return EmbeddingResult(vectors=vectors, total_tokens=total_tokens)

    async def embed_query(self, text: str) -> list[float]:
        import openai

        try:
            response = await self._client.embeddings.create(
                input=[text], model=self._model, dimensions=self._dimensions
            )
        except openai.OpenAIError as exc:
            logger.error("openai_embed_query_failed", error=str(exc))
            raise UpstreamProviderError(f"Embedding provider error: {exc}") from exc
        return response.data[0].embedding
