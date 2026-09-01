"""Shared async Redis client accessor. A single connection pool per process,
reused by rate limiting, BM25 cache versioning, and anything else that needs
cheap shared state across the web/worker processes.
"""

from functools import lru_cache

import redis.asyncio as redis

from app.core.config import settings


@lru_cache
def get_redis_client() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)
