import pytest
from httpx import AsyncClient

from app.services import document_service

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _stub_celery_enqueue(monkeypatch):
    """Document upload/reingest enqueue a Celery task — actually dispatching
    it requires a live Redis broker, which this endpoint-level test isn't
    concerned with (the ingestion pipeline itself is covered separately).
    Stub it so the test only exercises the HTTP + DB-write contract."""
    monkeypatch.setattr(document_service, "enqueue_ingestion", lambda document_id: None)


async def _register_and_login(client: AsyncClient, payload: dict) -> dict:
    await client.post("/api/v1/auth/register", json=payload)
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": payload["email"], "password": payload["password"]},
    )
    tokens = login_resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_workspace(client: AsyncClient, headers: dict) -> tuple[str, str]:
    org_id = (await client.get("/api/v1/organizations", headers=headers)).json()[0]["id"]
    workspace = (
        await client.post(
            f"/api/v1/organizations/{org_id}/workspaces",
            json={"name": "Docs KB"},
            headers=headers,
        )
    ).json()
    return org_id, workspace["id"]


async def test_upload_list_and_delete_document(client: AsyncClient, registration_payload: dict):
    headers = await _register_and_login(client, registration_payload)
    _, workspace_id = await _create_workspace(client, headers)

    upload_resp = await client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=headers,
        files={"file": ("notes.txt", b"Some plain text content.", "text/plain")},
    )
    assert upload_resp.status_code == 202
    body = upload_resp.json()
    document_id = body["document"]["id"]
    assert body["document"]["status"] == "pending"
    assert body["document"]["original_filename"] == "notes.txt"

    list_resp = await client.get(f"/api/v1/workspaces/{workspace_id}/documents", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    status_resp = await client.get(
        f"/api/v1/workspaces/{workspace_id}/documents/{document_id}/status", headers=headers
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "pending"

    delete_resp = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/documents/{document_id}", headers=headers
    )
    assert delete_resp.status_code == 204

    get_after_delete = await client.get(
        f"/api/v1/workspaces/{workspace_id}/documents/{document_id}", headers=headers
    )
    assert get_after_delete.status_code == 404


async def test_upload_rejects_unsupported_file_type(
    client: AsyncClient, registration_payload: dict
):
    headers = await _register_and_login(client, registration_payload)
    _, workspace_id = await _create_workspace(client, headers)

    resp = await client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=headers,
        files={"file": ("archive.zip", b"PK\x03\x04fake", "application/zip")},
    )
    # ValidationAppError.status_code is 422 (Unprocessable Entity), the same
    # status every other validation failure in this app uses — this test's
    # assertion was simply wrong and had never been executed to catch it.
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_document_from_other_workspace_is_not_accessible(
    client: AsyncClient, registration_payload: dict
):
    headers = await _register_and_login(client, registration_payload)
    org_id, workspace_a = await _create_workspace(client, headers)

    workspace_b = (
        await client.post(
            f"/api/v1/organizations/{org_id}/workspaces",
            json={"name": "Second KB"},
            headers=headers,
        )
    ).json()["id"]

    upload_resp = await client.post(
        f"/api/v1/workspaces/{workspace_a}/documents",
        headers=headers,
        files={"file": ("a.txt", b"content", "text/plain")},
    )
    document_id = upload_resp.json()["document"]["id"]

    # Same user, but the document belongs to workspace_a, not workspace_b —
    # must 404, not leak the document across the workspace boundary.
    cross_resp = await client.get(
        f"/api/v1/workspaces/{workspace_b}/documents/{document_id}", headers=headers
    )
    assert cross_resp.status_code == 404
