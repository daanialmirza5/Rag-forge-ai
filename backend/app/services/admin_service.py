"""Cross-organization operations for the superuser-only admin panel."""

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.models.workspace import Workspace


@dataclass(frozen=True, slots=True)
class OrganizationSummary:
    organization: Organization
    member_count: int
    workspace_count: int


def _counts_query() -> Select[tuple[Organization, int, int]]:
    member_count = (
        select(func.count(OrganizationMember.id))
        .where(OrganizationMember.organization_id == Organization.id)
        .correlate(Organization)
        .scalar_subquery()
    )
    workspace_count = (
        select(func.count(Workspace.id))
        .where(Workspace.organization_id == Organization.id)
        .correlate(Organization)
        .scalar_subquery()
    )
    return select(Organization, member_count, workspace_count)


async def list_organizations(db: AsyncSession) -> list[OrganizationSummary]:
    result = await db.execute(_counts_query().order_by(Organization.created_at.desc()))
    return [
        OrganizationSummary(organization=org, member_count=member_count_val, workspace_count=workspace_count_val)
        for org, member_count_val, workspace_count_val in result.all()
    ]


async def get_organization_summary(
    db: AsyncSession, organization_id: uuid.UUID
) -> OrganizationSummary:
    result = await db.execute(_counts_query().where(Organization.id == organization_id))
    row = result.first()
    if row is None:
        raise NotFoundError("Organization not found")
    org, member_count_val, workspace_count_val = row
    return OrganizationSummary(
        organization=org, member_count=member_count_val, workspace_count=workspace_count_val
    )


async def update_organization_plan(
    db: AsyncSession, *, organization_id: uuid.UUID, plan_tier: str
) -> Organization:
    org = await db.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("Organization not found")
    org.plan_tier = plan_tier
    await db.flush()
    return org


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


async def set_user_active(db: AsyncSession, *, user_id: uuid.UUID, is_active: bool) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    user.is_active = is_active
    await db.flush()
    return user


async def set_user_superuser(db: AsyncSession, *, user_id: uuid.UUID, is_superuser: bool) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    user.is_superuser = is_superuser
    await db.flush()
    return user
