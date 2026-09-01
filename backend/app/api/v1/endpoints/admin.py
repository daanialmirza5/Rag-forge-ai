import uuid

from fastapi import APIRouter, Query, Request

from app.api.deps import CurrentSuperuser, DBSession
from app.core.exceptions import PermissionDeniedError
from app.schemas.admin import (
    AdminAuditLogRead,
    AdminOrganizationPlanUpdate,
    AdminOrganizationRead,
    AdminUserActiveUpdate,
    AdminUserRead,
    AdminUserSuperuserUpdate,
)
from app.schemas.analytics import UsageDailyPointRead, UsageSummaryRead
from app.schemas.common import Paginated
from app.services import admin_service, analytics_service, audit_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/organizations", response_model=list[AdminOrganizationRead])
async def list_organizations(_admin: CurrentSuperuser, db: DBSession) -> list[AdminOrganizationRead]:
    summaries = await admin_service.list_organizations(db)
    return [
        AdminOrganizationRead(
            id=s.organization.id,
            name=s.organization.name,
            slug=s.organization.slug,
            plan_tier=s.organization.plan_tier,
            member_count=s.member_count,
            workspace_count=s.workspace_count,
            created_at=s.organization.created_at,
        )
        for s in summaries
    ]


@router.patch("/organizations/{organization_id}/plan", response_model=AdminOrganizationRead)
async def update_organization_plan(
    organization_id: uuid.UUID,
    payload: AdminOrganizationPlanUpdate,
    admin: CurrentSuperuser,
    db: DBSession,
    request: Request,
) -> AdminOrganizationRead:
    org = await admin_service.update_organization_plan(
        db, organization_id=organization_id, plan_tier=payload.plan_tier
    )
    await audit_service.record_audit_event(
        db,
        action="admin.organization.plan_updated",
        resource_type="organization",
        actor_user_id=admin.id,
        organization_id=organization_id,
        resource_id=organization_id,
        ip_address=request.client.host if request.client else None,
        metadata={"plan_tier": payload.plan_tier},
    )
    await db.commit()

    summary = await admin_service.get_organization_summary(db, organization_id)
    return AdminOrganizationRead(
        id=org.id,
        name=org.name,
        slug=org.slug,
        plan_tier=org.plan_tier,
        member_count=summary.member_count,
        workspace_count=summary.workspace_count,
        created_at=org.created_at,
    )


@router.get("/users", response_model=list[AdminUserRead])
async def list_users(_admin: CurrentSuperuser, db: DBSession) -> list[AdminUserRead]:
    users = await admin_service.list_users(db)
    return [AdminUserRead.model_validate(u) for u in users]


@router.patch("/users/{user_id}/active", response_model=AdminUserRead)
async def update_user_active(
    user_id: uuid.UUID,
    payload: AdminUserActiveUpdate,
    admin: CurrentSuperuser,
    db: DBSession,
    request: Request,
) -> AdminUserRead:
    if user_id == admin.id and not payload.is_active:
        raise PermissionDeniedError("You cannot deactivate your own account")
    user = await admin_service.set_user_active(db, user_id=user_id, is_active=payload.is_active)
    await audit_service.record_audit_event(
        db,
        action="admin.user.active_updated",
        resource_type="user",
        actor_user_id=admin.id,
        resource_id=user_id,
        ip_address=request.client.host if request.client else None,
        metadata={"is_active": payload.is_active},
    )
    await db.commit()
    return AdminUserRead.model_validate(user)


@router.patch("/users/{user_id}/superuser", response_model=AdminUserRead)
async def update_user_superuser(
    user_id: uuid.UUID,
    payload: AdminUserSuperuserUpdate,
    admin: CurrentSuperuser,
    db: DBSession,
    request: Request,
) -> AdminUserRead:
    if user_id == admin.id and not payload.is_superuser:
        raise PermissionDeniedError("You cannot revoke your own superuser access")
    user = await admin_service.set_user_superuser(
        db, user_id=user_id, is_superuser=payload.is_superuser
    )
    await audit_service.record_audit_event(
        db,
        action="admin.user.superuser_updated",
        resource_type="user",
        actor_user_id=admin.id,
        resource_id=user_id,
        ip_address=request.client.host if request.client else None,
        metadata={"is_superuser": payload.is_superuser},
    )
    await db.commit()
    return AdminUserRead.model_validate(user)


@router.get("/usage", response_model=UsageSummaryRead)
async def get_platform_usage(
    _admin: CurrentSuperuser,
    db: DBSession,
    lookback_days: int = Query(default=analytics_service.DEFAULT_LOOKBACK_DAYS, ge=1, le=365),
) -> UsageSummaryRead:
    summary = await analytics_service.get_usage_summary(db, lookback_days=lookback_days)
    return UsageSummaryRead(
        points=[
            UsageDailyPointRead(
                day=p.day,
                event_type=p.event_type,
                event_count=p.event_count,
                tokens_input=p.tokens_input,
                tokens_output=p.tokens_output,
                cost_usd=p.cost_usd,
            )
            for p in summary.points
        ],
        total_events=summary.total_events,
        total_tokens_input=summary.total_tokens_input,
        total_tokens_output=summary.total_tokens_output,
        total_cost_usd=summary.total_cost_usd,
    )


@router.get("/audit-logs", response_model=Paginated[AdminAuditLogRead])
async def list_audit_logs(
    _admin: CurrentSuperuser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> Paginated[AdminAuditLogRead]:
    logs = await audit_service.list_audit_logs(
        db, limit=page_size, offset=(page - 1) * page_size
    )
    total = await audit_service.count_audit_logs(db)
    items = [AdminAuditLogRead.model_validate(log) for log in logs]
    return Paginated(items=items, total=total, page=page, page_size=page_size)
