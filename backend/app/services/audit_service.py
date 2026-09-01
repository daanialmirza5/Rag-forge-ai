"""Records security-sensitive actions to the append-only `audit_logs` table,
surfaced to superusers via the admin panel (`admin_service.py`).
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

DEFAULT_PAGE_SIZE = 50


async def record_audit_event(
    db: AsyncSession,
    *,
    action: str,
    resource_type: str,
    actor_user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    resource_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    record = AuditLog(
        organization_id=organization_id,
        user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        audit_metadata=metadata or {},
    )
    db.add(record)
    await db.flush()
    return record


async def list_audit_logs(
    db: AsyncSession, *, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0
) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def count_audit_logs(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(AuditLog.id)))
    return result.scalar_one()
