from functools import lru_cache

from app.ai.vectorstore.base import VectorStore
from app.ai.vectorstore.qdrant_store import QdrantVectorStore


@lru_cache
def get_vector_store() -> VectorStore:
    return QdrantVectorStore()
