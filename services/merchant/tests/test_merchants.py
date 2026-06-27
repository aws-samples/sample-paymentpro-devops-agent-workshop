"""Tests for merchant registration, auth, and API key management."""

import pytest
from httpx import AsyncClient


REGISTER_PAYLOAD = {
    "business_name": "Test Shop",
    "email": "test@example.com",
    "password": "securepass123",
    "contact": "+91-9876543210",
}


@pytest.mark.asyncio
async def test_register_merchant(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.post(
        "/api/v1/merchants/register", json=REGISTER_PAYLOAD, headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["business_name"] == "Test Shop"
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, auth_headers: dict) -> None:
    await client.post("/api/v1/merchants/register", json=REGISTER_PAYLOAD, headers=auth_headers)
    response = await client.post(
        "/api/v1/merchants/register", json=REGISTER_PAYLOAD, headers=auth_headers
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, auth_headers: dict) -> None:
    await client.post("/api/v1/merchants/register", json=REGISTER_PAYLOAD, headers=auth_headers)
    login_payload = {"email": "test@example.com", "password": "securepass123"}
    response = await client.post(
        "/api/v1/merchants/login", json=login_payload, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "merchant_id" in data
    assert "expires_at" in data


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, auth_headers: dict) -> None:
    await client.post("/api/v1/merchants/register", json=REGISTER_PAYLOAD, headers=auth_headers)
    login_payload = {"email": "test@example.com", "password": "wrongpassword"}
    response = await client.post(
        "/api/v1/merchants/login", json=login_payload, headers=auth_headers
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient, auth_headers: dict) -> None:
    login_payload = {"email": "nobody@example.com", "password": "whatever"}
    response = await client.post(
        "/api/v1/merchants/login", json=login_payload, headers=auth_headers
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, auth_headers: dict) -> None:
    await client.post("/api/v1/merchants/register", json=REGISTER_PAYLOAD, headers=auth_headers)
    login_resp = await client.post(
        "/api/v1/merchants/login",
        json={"email": "test@example.com", "password": "securepass123"},
        headers=auth_headers,
    )
    session_id = login_resp.json()["session_id"]

    response = await client.post(
        f"/api/v1/merchants/logout?session_id={session_id}", headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_logout_invalid_session(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.post(
        "/api/v1/merchants/logout?session_id=nonexistent", headers=auth_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_api_key(client: AsyncClient, auth_headers: dict) -> None:
    reg_resp = await client.post(
        "/api/v1/merchants/register", json=REGISTER_PAYLOAD, headers=auth_headers
    )
    merchant_id = reg_resp.json()["id"]

    response = await client.post(
        f"/api/v1/merchants/{merchant_id}/api-keys", headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["merchant_id"] == merchant_id
    assert len(data["key_value"]) == 64
    assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_generate_api_key_nonexistent_merchant(
    client: AsyncClient, auth_headers: dict
) -> None:
    response = await client.post(
        "/api/v1/merchants/nonexistent/api-keys", headers=auth_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_revoke_api_key(client: AsyncClient, auth_headers: dict) -> None:
    reg_resp = await client.post(
        "/api/v1/merchants/register", json=REGISTER_PAYLOAD, headers=auth_headers
    )
    merchant_id = reg_resp.json()["id"]

    key_resp = await client.post(
        f"/api/v1/merchants/{merchant_id}/api-keys", headers=auth_headers
    )
    key_id = key_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/merchants/{merchant_id}/api-keys/{key_id}", headers=auth_headers
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_validate_api_key_valid(client: AsyncClient, auth_headers: dict) -> None:
    reg_resp = await client.post(
        "/api/v1/merchants/register", json=REGISTER_PAYLOAD, headers=auth_headers
    )
    merchant_id = reg_resp.json()["id"]

    key_resp = await client.post(
        f"/api/v1/merchants/{merchant_id}/api-keys", headers=auth_headers
    )
    key_value = key_resp.json()["key_value"]

    response = await client.post(
        f"/api/v1/merchants/validate-key?api_key={key_value}", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["merchant_id"] == merchant_id


@pytest.mark.asyncio
async def test_validate_api_key_invalid(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.post(
        "/api/v1/merchants/validate-key?api_key=invalid-key", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["merchant_id"] is None


@pytest.mark.asyncio
async def test_validate_revoked_key(client: AsyncClient, auth_headers: dict) -> None:
    reg_resp = await client.post(
        "/api/v1/merchants/register", json=REGISTER_PAYLOAD, headers=auth_headers
    )
    merchant_id = reg_resp.json()["id"]

    key_resp = await client.post(
        f"/api/v1/merchants/{merchant_id}/api-keys", headers=auth_headers
    )
    key_id = key_resp.json()["id"]
    key_value = key_resp.json()["key_value"]

    # Revoke
    await client.delete(
        f"/api/v1/merchants/{merchant_id}/api-keys/{key_id}", headers=auth_headers
    )

    # Validate — should be invalid now
    response = await client.post(
        f"/api/v1/merchants/validate-key?api_key={key_value}", headers=auth_headers
    )
    data = response.json()
    assert data["valid"] is False


@pytest.mark.asyncio
async def test_get_merchant_profile(client: AsyncClient, auth_headers: dict) -> None:
    reg_resp = await client.post(
        "/api/v1/merchants/register", json=REGISTER_PAYLOAD, headers=auth_headers
    )
    merchant_id = reg_resp.json()["id"]

    response = await client.get(f"/api/v1/merchants/{merchant_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["business_name"] == "Test Shop"


@pytest.mark.asyncio
async def test_get_merchant_profile_not_found(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.get("/api/v1/merchants/nonexistent", headers=auth_headers)
    assert response.status_code == 404
