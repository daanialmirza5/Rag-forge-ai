"""Redis fixed-window rate limiter, keyed by API key (if present) or client
IP. Fixed-window is simpler than a sliding log/token bucket and is sufficient
here since the bound is advisory (protects shared LLM/embedding budgets, not
a strict SLA) — swap for a sliding-window Lua script if stricter fairness is
ever needed."""

import time

import redis.asyncio as redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

_EXEMPT_PATHS = {"/api/v1/health", "/api/v1/health/ready", "/metrics", "/docs", "/openapi.json"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client: redis.Redis | None = None) -> None:
        super().__init__(app)
        self._redis = redis_client or redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        client_key = self._identify_client(request)
        window = int(time.time() // 60)
        redis_key = f"ratelimit:{client_key}:{window}"

        current = await self._redis.incr(redis_key)
        if current == 1:
            await self._redis.expire(redis_key, 60)

        if current > settings.RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Rate limit exceeded. Try again shortly.",
                    }
                },
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = str(
            max(settings.RATE_LIMIT_PER_MINUTE - current, 0)
        )
        return response

    @staticmethod
    def _identify_client(request: Request) -> str:
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key[:16]}"
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return f"token:{hash(auth_header) & 0xFFFFFFFF}"
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
