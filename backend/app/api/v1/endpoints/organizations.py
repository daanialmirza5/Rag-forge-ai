import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import PermissionDeniedError
from app.models.organization import OrganizationMember, OrgRole
from app.schemas.organization import OrganizationMemberRead, OrganizationRead
from app.services import organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("", response_model=list[OrganizationRead])
async def list_my_organizations(current_user: CurrentUser, db: DBSession) -> list[OrganizationRead]:
    orgs = await organization_service.list_user_organizations(db, current_user.id)
    return [OrganizationRead.model_validate(o) for o in orgs]


@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_organization(
    organization_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> OrganizationRead:
    await organization_service.require_membership(
        db, organization_id=organization_id, user_id=current_user.id
    )
    org = await organization_service.get_organization(db, organization_id)
    return OrganizationRead.model_validate(org)


@router.get("/{organization_id}/members", response_model=list[OrganizationMemberRead])
async def list_members(
    organization_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> list[OrganizationMemberRead]:
    await organization_service.require_membership(
        db, organization_id=organization_id, user_id=current_user.id
    )
    members = await organization_service.list_members(db, organization_id)
    return [OrganizationMemberRead.model_validate(m) for m in members]


@router.delete("/{organization_id}/members/{member_id}", status_code=204)
async def remove_member(
    organization_id: uuid.UUID, member_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> None:
    caller_membership = await organization_service.require_membership(
        db, organization_id=organization_id, user_id=current_user.id
    )
    if caller_membership.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value):
        raise PermissionDeniedError("Only owners/admins can remove members")

    member = await db.get(OrganizationMember, member_id)
    if member is not None and member.organization_id == organization_id:
        await db.delete(member)
        await db.flush()
    await db.commit()
