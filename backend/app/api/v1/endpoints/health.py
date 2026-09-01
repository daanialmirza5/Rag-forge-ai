from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DBSession

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — no dependencies checked."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(db: DBSession) -> dict[str, str]:
    """Readiness probe — verifies the database connection is usable."""
    await db.execute(text("SELECT 1"))
    return {"status": "ready"}
