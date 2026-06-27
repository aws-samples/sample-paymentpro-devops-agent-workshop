"""Tests for service authentication middleware."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_missing_service_key_returns_401(client: AsyncClient) -> None:
    """Request without X-Service-Key should be rejected."""
    payload = {"amount": "100.00"}
    response = await client.post("/api/v1/validate/amount", json=payload)
    assert response.status_code == 401
    assert "Missing" in response.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_service_key_returns_401(client: AsyncClient) -> None:
    """Request with wrong X-Service-Key should be rejected."""
    headers = {"X-Service-Key": "wrong-secret"}
    payload = {"amount": "100.00"}
    response = await client.post("/api/v1/validate/amount", json=payload, headers=headers)
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


@pytest.mark.asyncio
async def test_valid_service_key_passes(client: AsyncClient, auth_headers: dict) -> None:
    """Request with correct X-Service-Key should pass through."""
    payload = {"amount": "100.00"}
    response = await client.post("/api/v1/validate/amount", json=payload, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_skips_auth(client: AsyncClient) -> None:
    """Health endpoint should not require authentication."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_empty_service_key_returns_401(client: AsyncClient) -> None:
    """Empty X-Service-Key header should be rejected."""
    headers = {"X-Service-Key": ""}
    payload = {"amount": "100.00"}
    response = await client.post("/api/v1/validate/amount", json=payload, headers=headers)
    assert response.status_code == 401
