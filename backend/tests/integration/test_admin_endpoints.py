import uuid

import pytest
from httpx import AsyncClient

from app.models.audit import AuditLog
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def _register_and_login(client: AsyncClient, payload: dict) -> dict:
    register_resp = await client.post("/api/v1/auth/register", json=payload)
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": payload["email"], "password": payload["password"]},
    )
    tokens = login_resp.json()
    return {
        "headers": {"Authorization": f"Bearer {tokens['access_token']}"},
        "user_id": register_resp.json()["id"],
    }


async def test_regular_user_cannot_access_admin_endpoints(
    client: AsyncClient, registration_payload: dict
):
    user = await _register_and_login(client, registration_payload)

    resp = await client.get("/api/v1/admin/organizations", headers=user["headers"])
    assert resp.status_code == 403


async def test_superuser_can_manage_organizations_users_and_view_audit_logs(
    client: AsyncClient, db_session, registration_payload: dict
):
    admin = await _register_and_login(client, registration_payload)

    admin_user = await db_session.get(User, uuid.UUID(admin["user_id"]))
    admin_user.is_superuser = True
    await db_session.commit()

    orgs_resp = await client.get("/api/v1/admin/organizations", headers=admin["headers"])
    assert orgs_resp.status_code == 200
    orgs = orgs_resp.json()
    assert len(orgs) == 1
    assert orgs[0]["member_count"] == 1
    assert orgs[0]["workspace_count"] == 0
    org_id = orgs[0]["id"]

    plan_resp = await client.patch(
        f"/api/v1/admin/organizations/{org_id}/plan",
        json={"plan_tier": "enterprise"},
        headers=admin["headers"],
    )
    assert plan_resp.status_code == 200
    assert plan_resp.json()["plan_tier"] == "enterprise"

    other_user = await _register_and_login(
        client,
        {
            "email": "member@example.com",
            "password": "supersecret123",
            "full_name": "Mia Member",
            "organization_name": "Mia Co",
        },
    )

    users_resp = await client.get("/api/v1/admin/users", headers=admin["headers"])
    assert users_resp.status_code == 200
    assert len(users_resp.json()) == 2

    deactivate_resp = await client.patch(
        f"/api/v1/admin/users/{other_user['user_id']}/active",
        json={"is_active": False},
        headers=admin["headers"],
    )
    assert deactivate_resp.status_code == 200
    assert deactivate_resp.json()["is_active"] is False

    self_deactivate_resp = await client.patch(
        f"/api/v1/admin/users/{admin['user_id']}/active",
        json={"is_active": False},
        headers=admin["headers"],
    )
    assert self_deactivate_resp.status_code == 403

    usage_resp = await client.get("/api/v1/admin/usage", headers=admin["headers"])
    assert usage_resp.status_code == 200
    assert usage_resp.json()["total_events"] == 0

    audit_count = (
        await db_session.execute(AuditLog.__table__.select())
    ).all()
    assert len(audit_count) == 2  # plan update + deactivate

    audit_resp = await client.get("/api/v1/admin/audit-logs", headers=admin["headers"])
    assert audit_resp.status_code == 200
    audit_body = audit_resp.json()
    assert audit_body["total"] == 2
    actions = {item["action"] for item in audit_body["items"]}
    assert actions == {"admin.organization.plan_updated", "admin.user.active_updated"}
