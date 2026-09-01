"""Application configuration, loaded from environment variables / .env file.

Single source of truth for all tunables — nothing in the codebase should read
`os.environ` directly outside of this module.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The exact placeholder from .env.example / the root .env.example — if this
# ever ends up in a production deployment, every JWT is forgeable by anyone
# who can read a public repo. Refusing to boot is cheaper than a leaked key.
_PLACEHOLDER_SECRET_KEY = "change-me-to-a-random-64-char-string"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "RAGForge AI"
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = True
    SECRET_KEY: str = Field(min_length=16)
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- Auth / JWT ---
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- Database ---
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # --- Vector store ---
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION_NAME: str = "document_chunks"

    # --- LLM ---
    LLM_PROVIDER: Literal["anthropic", "ollama"] = "anthropic"
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "claude-opus-4-8"
    LLM_MAX_TOKENS: int = 4096
    LLM_ENABLE_THINKING: bool = True
    LLM_EFFORT: Literal["low", "medium", "high", "xhigh", "max"] = "high"
    LLM_REQUEST_TIMEOUT_SECONDS: float = 120.0

    # --- Embeddings ---
    VOYAGE_API_KEY: str = ""
    EMBEDDING_MODEL: str = "voyage-3-large"
    EMBEDDING_DIMENSIONS: int = 1024
    EMBEDDING_PROVIDER: Literal["voyage", "openai", "ollama"] = "voyage"
    OPENAI_API_KEY: str = ""

    # --- Reranking ---
    RERANK_MODEL: str = "rerank-2"
    # "none" is a free-tier fallback (see app/ai/reranking/noop_provider.py) —
    # hybrid retrieval's RRF fusion still gives a reasonable order without a
    # cross-encoder reranking pass, it's just not refined by one.
    RERANK_PROVIDER: Literal["voyage", "none"] = "voyage"

    # --- Ollama (free local LLM/embedding path — no API keys required) ---
    # From inside Docker Compose, this needs to be http://host.docker.internal:11434
    # (Ollama runs on the host, not in a container); native/non-Docker runs use
    # the default http://localhost:11434.
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # --- Retrieval tuning ---
    RETRIEVAL_DENSE_TOP_K: int = 50
    RETRIEVAL_SPARSE_TOP_K: int = 50
    RETRIEVAL_FUSED_TOP_K: int = 30
    RETRIEVAL_RERANK_TOP_N: int = 8
    RETRIEVAL_HISTORY_TURNS_FOR_REWRITE: int = 6

    # --- Chunking (char-based; ~4 chars/token approximation, not exact
    # Claude tokenization — good enough for sizing chunk boundaries) ---
    CHUNK_SIZE_CHARS: int = 2000
    CHUNK_OVERLAP_CHARS: int = 200

    # --- File storage ---
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_LOCAL_PATH: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 50
    S3_BUCKET: str = ""
    S3_REGION: str = ""
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""

    # --- Rate limiting ---
    RATE_LIMIT_PER_MINUTE: int = 60

    # --- Observability ---
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"
    SENTRY_DSN: str | None = None

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, v: object) -> object:
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def cors_origins(self) -> list[str]:
        return self.BACKEND_CORS_ORIGINS

    @model_validator(mode="after")
    def _reject_placeholder_secret_in_production(self) -> "Settings":
        if self.is_production and self.SECRET_KEY == _PLACEHOLDER_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY is still the .env.example placeholder value with "
                "APP_ENV=production — set a real random secret before deploying."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — safe to call repeatedly (e.g. as a FastAPI dependency)."""
    return Settings()


settings = get_settings()
