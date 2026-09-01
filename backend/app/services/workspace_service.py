import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.services.organization_service import slugify

# Role hierarchy — index = privilege level, higher can do everything a lower role can.
_ROLE_RANK = {
    WorkspaceRole.VIEWER.value: 0,
    WorkspaceRole.EDITOR.value: 1,
    WorkspaceRole.OWNER.value: 2,
}


def role_satisfies(actual: str, minimum: str) -> bool:
    return _ROLE_RANK.get(actual, -1) >= _ROLE_RANK.get(minimum, 999)


async def _unique_slug(db: AsyncSession, organization_id: uuid.UUID, base_slug: str) -> str:
    slug = base_slug
    suffix = 1
    while (
        await db.execute(
            select(Workspace.id).where(
                Workspace.organization_id == organization_id, Workspace.slug == slug
            )
        )
    ).scalar_one_or_none() is not None:
        suffix += 1
        slug = f"{base_slug}-{suffix}"
    return slug


async def create_workspace(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    name: str,
    description: str = "",
) -> Workspace:
    slug = await _unique_slug(db, organization_id, slugify(name))
    workspace = Workspace(
        organization_id=organization_id, name=name, slug=slug, description=description
    )
    db.add(workspace)
    await db.flush()

    db.add(
        WorkspaceMember(
            workspace_id=workspace.id, user_id=owner_user_id, role=WorkspaceRole.OWNER.value
        )
    )
    await db.flush()
    return workspace


async def get_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> Workspace:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise NotFoundError("Workspace not found")
    return workspace


async def list_organization_workspaces(
    db: AsyncSession, organization_id: uuid.UUID
) -> list[Workspace]:
    result = await db.execute(
        select(Workspace).where(Workspace.organization_id == organization_id)
    )
    return list(result.scalars().all())


async def get_workspace_membership(
    db: AsyncSession, *, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> WorkspaceMember | None:
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def require_workspace_role(
    db: AsyncSession, *, workspace_id: uuid.UUID, user_id: uuid.UUID, minimum_role: str
) -> WorkspaceMember:
    membership = await get_workspace_membership(db, workspace_id=workspace_id, user_id=user_id)
    if membership is None or not role_satisfies(membership.role, minimum_role):
        raise PermissionDeniedError("Insufficient permissions for this workspace")
    return membership


async def list_workspace_members(
    db: AsyncSession, workspace_id: uuid.UUID
) -> list[WorkspaceMember]:
    # `WorkspaceMemberRead` exposes user_email/user_full_name via properties
    # on the model that read `self.user` — eager-load it here so those
    # properties don't need a lazy load (unsupported on an async session).
    result = await db.execute(
        select(WorkspaceMember)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .options(selectinload(WorkspaceMember.user))
    )
    return list(result.scalars().all())
