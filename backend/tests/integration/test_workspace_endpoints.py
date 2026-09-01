import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_login(client: AsyncClient, payload: dict) -> dict:
    await client.post("/api/v1/auth/register", json=payload)
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": payload["email"], "password": payload["password"]},
    )
    tokens = login_resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_workspace_create_and_rbac(client: AsyncClient, registration_payload: dict):
    headers = await _register_and_login(client, registration_payload)

    orgs_resp = await client.get("/api/v1/organizations", headers=headers)
    assert orgs_resp.status_code == 200
    orgs = orgs_resp.json()
    assert len(orgs) == 1
    org_id = orgs[0]["id"]

    create_resp = await client.post(
        f"/api/v1/organizations/{org_id}/workspaces",
        json={"name": "Research KB", "description": "Internal research docs"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    workspace = create_resp.json()
    assert workspace["slug"] == "research-kb"

    list_resp = await client.get(
        f"/api/v1/organizations/{org_id}/workspaces", headers=headers
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    members_resp = await client.get(
        f"/api/v1/organizations/{org_id}/workspaces/{workspace['id']}/members", headers=headers
    )
    assert members_resp.status_code == 200
    assert members_resp.json()[0]["role"] == "owner"


async def test_second_user_cannot_access_foreign_workspace(
    client: AsyncClient, registration_payload: dict
):
    owner_headers = await _register_and_login(client, registration_payload)
    orgs = (await client.get("/api/v1/organizations", headers=owner_headers)).json()
    org_id = orgs[0]["id"]
    workspace = (
        await client.post(
            f"/api/v1/organizations/{org_id}/workspaces",
            json={"name": "Private KB"},
            headers=owner_headers,
        )
    ).json()

    other_user = {
        "email": "intruder@example.com",
        "password": "supersecret123",
        "full_name": "Eve Intruder",
        "organization_name": "Eve Co",
    }
    intruder_headers = await _register_and_login(client, other_user)

    resp = await client.get(
        f"/api/v1/organizations/{org_id}/workspaces/{workspace['id']}",
        headers=intruder_headers,
    )
    assert resp.status_code == 403
