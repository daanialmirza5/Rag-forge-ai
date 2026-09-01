"""Aggregates the `usage_records` ledger into daily rollups for the
analytics dashboard.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage import UsageRecord

DEFAULT_LOOKBACK_DAYS = 30


@dataclass(frozen=True, slots=True)
class UsageDailyPoint:
    day: date
    event_type: str
    event_count: int
    tokens_input: int
    tokens_output: int
    cost_usd: float


@dataclass(frozen=True, slots=True)
class UsageSummary:
    points: list[UsageDailyPoint]
    total_events: int
    total_tokens_input: int
    total_tokens_output: int
    total_cost_usd: float


async def get_usage_summary(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> UsageSummary:
    """Aggregates usage for one organization, or platform-wide when
    `organization_id` is omitted (admin-only — see `admin_service.py`)."""
    since = datetime.now(UTC) - timedelta(days=lookback_days)
    day_col = cast(UsageRecord.created_at, Date)

    query = (
        select(
            day_col.label("day"),
            UsageRecord.event_type,
            func.count().label("event_count"),
            func.coalesce(func.sum(UsageRecord.tokens_input), 0).label("tokens_input"),
            func.coalesce(func.sum(UsageRecord.tokens_output), 0).label("tokens_output"),
            func.coalesce(func.sum(UsageRecord.cost_usd), 0).label("cost_usd"),
        )
        .where(UsageRecord.created_at >= since)
        .group_by(day_col, UsageRecord.event_type)
        .order_by(day_col)
    )
    if organization_id is not None:
        query = query.where(UsageRecord.organization_id == organization_id)
    if workspace_id is not None:
        query = query.where(UsageRecord.workspace_id == workspace_id)

    rows = (await db.execute(query)).all()

    points = [
        UsageDailyPoint(
            day=row.day,
            event_type=row.event_type,
            event_count=row.event_count,
            tokens_input=row.tokens_input,
            tokens_output=row.tokens_output,
            cost_usd=float(row.cost_usd),
        )
        for row in rows
    ]

    return UsageSummary(
        points=points,
        total_events=sum(p.event_count for p in points),
        total_tokens_input=sum(p.tokens_input for p in points),
        total_tokens_output=sum(p.tokens_output for p in points),
        total_cost_usd=sum(p.cost_usd for p in points),
    )
