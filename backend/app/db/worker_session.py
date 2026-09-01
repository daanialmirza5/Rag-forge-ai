"""Dedicated DB session factory for Celery tasks.

Celery task bodies run inside a fresh `asyncio.run(...)` call per task
invocation (see `app/workers/tasks/ingestion_tasks.py`) — each call gets its
own event loop. SQLAlchemy's async engine pools `asyncpg` connections, and
`asyncpg` connections are bound to the event loop they were created on, so
reusing the app's request-scoped pooled engine (`app/db/session.py`) across
multiple `asyncio.run()` calls in the same worker process would eventually
hand out a connection created on a now-closed loop.

`NullPool` sidesteps this entirely: every checkout opens a fresh connection
and closes it on return, so there's never a cross-loop-lifetime connection to
go stale. It costs a new TCP handshake per task, which is a fine trade for
Celery's already-coarse task granularity (this is not a hot per-request path).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

_worker_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    poolclass=NullPool,
)

WorkerSessionLocal = async_sessionmaker(
    bind=_worker_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


@asynccontextmanager
async def worker_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with WorkerSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
