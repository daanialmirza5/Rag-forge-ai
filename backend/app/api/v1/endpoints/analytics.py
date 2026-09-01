import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DBSession, require_workspace_role
from app.models.organization import OrgRole
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.analytics import UsageDailyPointRead, UsageSummaryRead
from app.services import analytics_service, organization_service, workspace_service

organization_router = APIRouter(prefix="/organizations/{organization_id}/analytics", tags=["analytics"])
workspace_router = APIRouter(prefix="/workspaces/{workspace_id}/analytics", tags=["analytics"])

LookbackDays = Annotated[int, Query(ge=1, le=365)]


def _to_schema(summary: analytics_service.UsageSummary) -> UsageSummaryRead:
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


@organization_router.get("/usage", response_model=UsageSummaryRead)
async def get_organization_usage(
    organization_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    lookback_days: LookbackDays = analytics_service.DEFAULT_LOOKBACK_DAYS,
) -> UsageSummaryRead:
    await organization_service.require_role(
        db,
        organization_id=organization_id,
        user_id=current_user.id,
        minimum_role=OrgRole.ADMIN.value,
    )
    summary = await analytics_service.get_usage_summary(
        db, organization_id=organization_id, lookback_days=lookback_days
    )
    return _to_schema(summary)


@workspace_router.get("/usage", response_model=UsageSummaryRead)
async def get_workspace_usage(
    workspace_id: uuid.UUID,
    db: DBSession,
    _membership: Annotated[WorkspaceMember, Depends(require_workspace_role(WorkspaceRole.VIEWER.value))],
    lookback_days: LookbackDays = analytics_service.DEFAULT_LOOKBACK_DAYS,
) -> UsageSummaryRead:
    workspace = await workspace_service.get_workspace(db, workspace_id)
    summary = await analytics_service.get_usage_summary(
        db,
        organization_id=workspace.organization_id,
        workspace_id=workspace_id,
        lookback_days=lookback_days,
    )
    return _to_schema(summary)
