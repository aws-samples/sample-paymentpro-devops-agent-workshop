"""Tests for analytics endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "analytics-service"


@pytest.mark.asyncio
async def test_get_volume_empty(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.get("/api/v1/analytics/volume", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["data"] == []


@pytest.mark.asyncio
async def test_get_volume_with_data(
    client: AsyncClient, auth_headers: dict, seed_transactions: None
) -> None:
    response = await client.get("/api/v1/analytics/volume", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4


@pytest.mark.asyncio
async def test_get_success_rates_empty(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.get("/api/v1/analytics/success-rates", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["success_rate"] == 0.0


@pytest.mark.asyncio
async def test_get_success_rates_with_data(
    client: AsyncClient, auth_headers: dict, seed_transactions: None
) -> None:
    response = await client.get("/api/v1/analytics/success-rates", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success_count"] == 3
    assert data["failure_count"] == 1
    assert data["total"] == 4
    assert data["success_rate"] == 75.0


@pytest.mark.asyncio
async def test_get_distribution(
    client: AsyncClient, auth_headers: dict, seed_transactions: None
) -> None:
    response = await client.get("/api/v1/analytics/distribution", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4
    types = {item["payment_type"]: item["count"] for item in data["data"]}
    assert types["UPI"] == 2
    assert types["CREDIT_CARD"] == 1
    assert types["WALLET"] == 1


@pytest.mark.asyncio
async def test_get_summary(
    client: AsyncClient, auth_headers: dict, seed_transactions: None
) -> None:
    response = await client.get("/api/v1/analytics/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_transactions"] == 4
    assert data["success_rate"] == 75.0
    assert float(data["total_volume"]) == 850.0
    assert data["payment_types"] == 3


@pytest.mark.asyncio
async def test_filter_by_merchant(
    client: AsyncClient, auth_headers: dict, seed_transactions: None
) -> None:
    response = await client.get(
        "/api/v1/analytics/summary?merchant_id=m1", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_transactions"] == 3


@pytest.mark.asyncio
async def test_public_endpoint_no_auth_needed(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
