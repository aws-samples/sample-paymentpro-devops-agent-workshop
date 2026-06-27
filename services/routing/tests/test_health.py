"""Tests for health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_returns_200(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_check_response_structure(client: AsyncClient) -> None:
    response = await client.get("/health")
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "routing-service"
    assert "version" in data
    assert "timestamp" in data
