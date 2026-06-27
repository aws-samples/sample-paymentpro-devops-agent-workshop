"""Tests for health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_returns_200(client: AsyncClient) -> None:
    """Health check should return 200 without authentication."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_check_response_structure(client: AsyncClient) -> None:
    """Health check should return expected fields."""
    response = await client.get("/health")
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "fraud-service"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_check_no_auth_required(client: AsyncClient) -> None:
    """Health check should work without X-Service-Key header."""
    response = await client.get("/health")
    assert response.status_code == 200
