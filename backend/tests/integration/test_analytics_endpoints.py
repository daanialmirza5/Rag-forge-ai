import uuid

import pytest
from httpx import AsyncClient

from app.models.organization import OrganizationMember, OrgRole
from app.models.usage import UsageEventType, UsageRecord

pytestmark = pytest.mark.asyncio


async def _register_and_login(client: AsyncClient, payload: dict) -> dict:
    register_resp = await client.post("/api/v1/auth/register", json=payload)
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": payload["email"], "password": payload["password"]},
    )
    tokens = login_resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    return {"headers": headers, "user_id": register_resp.json()["id"]}


async def _create_workspace(client: AsyncClient, headers: dict) -> tuple[str, str]:
    org_id = (await client.get("/api/v1/organizations", headers=headers)).json()[0]["id"]
    workspace = (
        await client.post(
            f"/api/v1/organizations/{org_id}/workspaces",
            json={"name": "Analytics KB"},
            headers=headers,
        )
    ).json()
    return org_id, workspace["id"]


async def test_workspace_and_org_usage_reflect_seeded_records(
    client: AsyncClient, db_session, registration_payload: dict
):
    owner = await _register_and_login(client, registration_payload)
    org_id, workspace_id = await _create_workspace(client, owner["headers"])

    db_session.add(
        UsageRecord(
            organization_id=uuid.UUID(org_id),
            workspace_id=uuid.UUID(workspace_id),
            user_id=uuid.UUID(owner["user_id"]),
            event_type=UsageEventType.CHAT_MESSAGE.value,
            tokens_input=100,
            tokens_output=50,
            cost_usd=0.0025,
        )
    )
    db_session.add(
        UsageRecord(
            organization_id=uuid.UUID(org_id),
            workspace_id=uuid.UUID(workspace_id),
            user_id=None,
            event_type=UsageEventType.DOCUMENT_INGESTED.value,
            tokens_input=200,
            tokens_output=0,
            cost_usd=0.0,
        )
    )
    await db_session.commit()

    workspace_resp = await client.get(
        f"/api/v1/workspaces/{workspace_id}/analytics/usage", headers=owner["headers"]
    )
    assert workspace_resp.status_code == 200
    workspace_summary = workspace_resp.json()
    assert workspace_summary["total_events"] == 2
    assert workspace_summary["total_tokens_input"] == 300
    assert workspace_summary["total_tokens_output"] == 50
    assert workspace_summary["total_cost_usd"] == pytest.approx(0.0025)
    event_types = {p["event_type"] for p in workspace_summary["points"]}
    assert event_types == {"chat_message", "document_ingested"}

    org_resp = await client.get(
        f"/api/v1/organizations/{org_id}/analytics/usage", headers=owner["headers"]
    )
    assert org_resp.status_code == 200
    org_summary = org_resp.json()
    assert org_summary["total_events"] == 2
    assert org_summary["total_tokens_input"] == 300


async def test_org_analytics_denied_for_non_admin_member(
    client: AsyncClient, db_session, registration_payload: dict
):
    owner = await _register_and_login(client, registration_payload)
    org_id, _ = await _create_workspace(client, owner["headers"])

    plain_member = await _register_and_login(
        client,
        {
            "email": "member@example.com",
            "password": "supersecret123",
            "full_name": "Mia Member",
            "organization_name": "Mia Co",
        },
    )
    db_session.add(
        OrganizationMember(
            organization_id=uuid.UUID(org_id),
            user_id=uuid.UUID(plain_member["user_id"]),
            role=OrgRole.MEMBER.value,
        )
    )
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/organizations/{org_id}/analytics/usage", headers=plain_member["headers"]
    )
    assert resp.status_code == 403


async def test_analytics_denied_for_non_member(client: AsyncClient, registration_payload: dict):
    owner = await _register_and_login(client, registration_payload)
    org_id, workspace_id = await _create_workspace(client, owner["headers"])

    intruder = await _register_and_login(
        client,
        {
            "email": "intruder@example.com",
            "password": "supersecret123",
            "full_name": "Eve Intruder",
            "organization_name": "Eve Co",
        },
    )

    workspace_resp = await client.get(
        f"/api/v1/workspaces/{workspace_id}/analytics/usage", headers=intruder["headers"]
    )
    assert workspace_resp.status_code == 403

    org_resp = await client.get(
        f"/api/v1/organizations/{org_id}/analytics/usage", headers=intruder["headers"]
    )
    assert org_resp.status_code == 403
