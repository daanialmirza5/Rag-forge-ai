import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.organization import Organization, OrganizationMember, OrgRole
from app.models.user import User


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]


async def _unique_slug(db: AsyncSession, base_slug: str) -> str:
    slug = base_slug
    suffix = 1
    while (
        await db.execute(select(Organization.id).where(Organization.slug == slug))
    ).scalar_one_or_none() is not None:
        suffix += 1
        slug = f"{base_slug}-{suffix}"
    return slug


async def create_organization_with_owner(
    db: AsyncSession, *, name: str, owner: User
) -> Organization:
    slug = await _unique_slug(db, slugify(name))
    org = Organization(name=name, slug=slug)
    db.add(org)
    await db.flush()

    membership = OrganizationMember(
        organization_id=org.id, user_id=owner.id, role=OrgRole.OWNER.value
    )
    db.add(membership)
    await db.flush()
    return org


async def get_organization(db: AsyncSession, organization_id: uuid.UUID) -> Organization:
    org = await db.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("Organization not found")
    return org


async def get_membership(
    db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID
) -> OrganizationMember | None:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def require_membership(
    db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID
) -> OrganizationMember:
    membership = await get_membership(db, organization_id=organization_id, user_id=user_id)
    if membership is None:
        raise PermissionDeniedError("You are not a member of this organization")
    return membership


# Role hierarchy — index = privilege level, higher can do everything a lower role can.
_ROLE_RANK = {
    OrgRole.MEMBER.value: 0,
    OrgRole.ADMIN.value: 1,
    OrgRole.OWNER.value: 2,
}


def role_satisfies(actual: str, minimum: str) -> bool:
    return _ROLE_RANK.get(actual, -1) >= _ROLE_RANK.get(minimum, 999)


async def require_role(
    db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID, minimum_role: str
) -> OrganizationMember:
    membership = await require_membership(db, organization_id=organization_id, user_id=user_id)
    if not role_satisfies(membership.role, minimum_role):
        raise PermissionDeniedError("Insufficient permissions for this organization")
    return membership


async def list_members(
    db: AsyncSession, organization_id: uuid.UUID
) -> list[OrganizationMember]:
    # `OrganizationMemberRead` exposes user_email/user_full_name via
    # properties on the model that read `self.user` — eager-load it here so
    # those properties don't need a lazy load (unsupported on an async session).
    result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == organization_id)
        .options(selectinload(OrganizationMember.user))
    )
    return list(result.scalars().all())


async def list_user_organizations(db: AsyncSession, user_id: uuid.UUID) -> list[Organization]:
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .where(OrganizationMember.user_id == user_id)
    )
    return list(result.scalars().all())
