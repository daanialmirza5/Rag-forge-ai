from functools import lru_cache

from app.ai.embeddings.base import EmbeddingProvider
from app.core.config import settings
from app.core.exceptions import AppError


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    if settings.EMBEDDING_PROVIDER == "voyage":
        from app.ai.embeddings.voyage_provider import VoyageEmbeddingProvider

        return VoyageEmbeddingProvider()
    if settings.EMBEDDING_PROVIDER == "openai":
        from app.ai.embeddings.openai_provider import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider()
    if settings.EMBEDDING_PROVIDER == "ollama":
        from app.ai.embeddings.ollama_provider import OllamaEmbeddingProvider

        return OllamaEmbeddingProvider()
    raise AppError(f"Unknown embedding provider: {settings.EMBEDDING_PROVIDER}")
