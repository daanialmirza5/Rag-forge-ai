"""Shared pytest fixtures.

Integration tests run against a real Postgres database (set via `.env.test` /
`DATABASE_URL`) — our models use Postgres-only types (JSONB, native UUID), so
SQLite is not a viable substitute. The schema is created fresh and dropped
per test function for isolation; see `docs/PROGRESS.md` for the CI wiring
that provisions this database (Phase 8).
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    # `ASGITransport` doesn't run ASGI lifespan events on its own — unlike a
    # real server, it skips straight to request/response — so `create_app`'s
    # lifespan (which calls `ensure_collection()`) never ran under it. That
    # left Qdrant's collection uninitialized for every test, surfacing as a
    # real 502 from `delete_by_document()` the moment a real Qdrant became
    # available to test against. Driving the lifespan context manager
    # ourselves matches what actually happens in production.
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def registration_payload() -> dict:
    return {
        "email": "founder@example.com",
        "password": "supersecret123",
        "full_name": "Ada Founder",
        "organization_name": "Acme Research",
    }
