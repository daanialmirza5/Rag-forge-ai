import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_register_login_me_flow(client: AsyncClient, registration_payload: dict):
    register_resp = await client.post("/api/v1/auth/register", json=registration_payload)
    assert register_resp.status_code == 201
    body = register_resp.json()
    assert body["email"] == registration_payload["email"]
    assert "hashed_password" not in body

    login_resp = await client.post(
        "/api/v1/auth/login",
        data={
            "username": registration_payload["email"],
            "password": registration_payload["password"],
        },
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    me_resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == registration_payload["email"]


async def test_register_duplicate_email_rejected(client: AsyncClient, registration_payload: dict):
    first = await client.post("/api/v1/auth/register", json=registration_payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/auth/register", json=registration_payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "already_exists"


async def test_login_wrong_password_rejected(client: AsyncClient, registration_payload: dict):
    await client.post("/api/v1/auth/register", json=registration_payload)

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": registration_payload["email"], "password": "not-the-password"},
    )
    assert resp.status_code == 401


async def test_login_nonexistent_email_rejected_with_same_message(
    client: AsyncClient, registration_payload: dict
):
    """Regression test: `authenticate_user` must not skip straight to a 500
    (e.g. a `None.hashed_password` crash) for an email that was never
    registered, and the error message must not reveal whether the email
    exists — both routes return the same generic 401."""
    await client.post("/api/v1/auth/register", json=registration_payload)

    wrong_password_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": registration_payload["email"], "password": "not-the-password"},
    )
    nonexistent_email_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody-registered@example.com", "password": "not-the-password"},
    )

    assert nonexistent_email_resp.status_code == 401
    assert (
        nonexistent_email_resp.json()["error"]["message"]
        == wrong_password_resp.json()["error"]["message"]
    )


async def test_refresh_and_logout_flow(client: AsyncClient, registration_payload: dict):
    await client.post("/api/v1/auth/register", json=registration_payload)
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={
            "username": registration_payload["email"],
            "password": registration_payload["password"],
        },
    )
    tokens = login_resp.json()

    refresh_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert new_tokens["access_token"] != tokens["access_token"]

    # Old refresh token was rotated out — reusing it must fail.
    reuse_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse_resp.status_code == 401

    logout_resp = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert logout_resp.status_code == 204


async def test_unauthenticated_request_rejected(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
