from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class OrganizationRead(ORMBase):
    id: UUID
    name: str
    slug: str
    plan_tier: str


class OrganizationMemberRead(ORMBase):
    id: UUID
    user_id: UUID
    user_email: str
    user_full_name: str
    role: str


class OrganizationMemberInvite(BaseModel):
    email: str
    role: str = Field(default="member", pattern="^(owner|admin|member)$")
