"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.ai.vectorstore.factory import get_vector_store
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    logger.info("app_startup", env=settings.APP_ENV)
    try:
        await get_vector_store().ensure_collection()
    except Exception as exc:  # noqa: BLE001 — startup must not crash if Qdrant isn't up yet
        logger.warning("vector_store_bootstrap_failed", error=str(exc))
    yield
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # `should_exclude_streaming_duration` keeps the chat SSE endpoint's
    # multi-second stream lifetime out of the request-latency histogram
    # (it would otherwise dominate the p95/p99 buckets); in-progress-request
    # tracking is opt-in upstream, and worth having for the Grafana dashboard.
    Instrumentator(
        should_instrument_requests_inprogress=True,
        should_exclude_streaming_duration=True,
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    return app


app = create_app()
