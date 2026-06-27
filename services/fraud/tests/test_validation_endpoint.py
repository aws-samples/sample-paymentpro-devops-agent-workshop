"""Tests for validation API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_validate_payment_valid_card(client: AsyncClient, auth_headers: dict) -> None:
    """Valid card payment should return valid=True."""
    payload = {
        "payment_type": "CREDIT_CARD",
        "amount": "100.00",
        "merchant_id": "merchant_1",
        "card_number": "4111111111111111",
        "card_expiry": "12/30",
        "cvv": "123",
    }
    response = await client.post("/api/v1/validate/payment", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["errors"] == []


@pytest.mark.asyncio
async def test_validate_payment_invalid_card(client: AsyncClient, auth_headers: dict) -> None:
    """Invalid card number should return valid=False with errors."""
    payload = {
        "payment_type": "CREDIT_CARD",
        "amount": "100.00",
        "merchant_id": "merchant_1",
        "card_number": "1234567890123456",
        "card_expiry": "12/30",
        "cvv": "123",
    }
    response = await client.post("/api/v1/validate/payment", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0


@pytest.mark.asyncio
async def test_validate_payment_valid_upi(client: AsyncClient, auth_headers: dict) -> None:
    """Valid UPI payment should return valid=True."""
    payload = {
        "payment_type": "UPI",
        "amount": "500.00",
        "merchant_id": "merchant_1",
        "upi_id": "user@paytm",
    }
    response = await client.post("/api/v1/validate/payment", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


@pytest.mark.asyncio
async def test_validate_payment_valid_wallet(client: AsyncClient, auth_headers: dict) -> None:
    """Valid wallet payment should return valid=True."""
    payload = {
        "payment_type": "WALLET",
        "amount": "200.00",
        "merchant_id": "merchant_1",
        "wallet_id": "wallet12345678",
        "wallet_balance": "500.00",
    }
    response = await client.post("/api/v1/validate/payment", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


@pytest.mark.asyncio
async def test_validate_payment_missing_fields(client: AsyncClient, auth_headers: dict) -> None:
    """Missing required fields should return errors."""
    payload = {
        "payment_type": "CREDIT_CARD",
        "amount": "100.00",
        "merchant_id": "merchant_1",
        # Missing card fields
    }
    response = await client.post("/api/v1/validate/payment", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert any(e["code"] == "MISSING_REQUIRED_FIELD" for e in data["errors"])


@pytest.mark.asyncio
async def test_validate_card_endpoint(client: AsyncClient, auth_headers: dict) -> None:
    """Card-only validation endpoint should work."""
    payload = {
        "card_number": "4111111111111111",
        "card_expiry": "12/30",
        "cvv": "123",
    }
    response = await client.post("/api/v1/validate/card", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


@pytest.mark.asyncio
async def test_validate_upi_endpoint(client: AsyncClient, auth_headers: dict) -> None:
    """UPI-only validation endpoint should work."""
    payload = {"upi_id": "user@paytm"}
    response = await client.post("/api/v1/validate/upi", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


@pytest.mark.asyncio
async def test_validate_amount_endpoint(client: AsyncClient, auth_headers: dict) -> None:
    """Amount-only validation endpoint should work."""
    payload = {"amount": "100.00"}
    response = await client.post("/api/v1/validate/amount", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


@pytest.mark.asyncio
async def test_validate_amount_invalid(client: AsyncClient, auth_headers: dict) -> None:
    """Invalid amount should return errors."""
    payload = {"amount": "0.001"}
    response = await client.post("/api/v1/validate/amount", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False


@pytest.mark.asyncio
async def test_response_includes_request_id(client: AsyncClient, auth_headers: dict) -> None:
    """Response should include X-Request-ID header."""
    response = await client.get("/health")
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_passes_through_request_id(client: AsyncClient, auth_headers: dict) -> None:
    """Provided X-Request-ID should be echoed back."""
    headers = {**auth_headers, "X-Request-ID": "test-correlation-123"}
    payload = {"amount": "100.00"}
    response = await client.post("/api/v1/validate/amount", json=payload, headers=headers)
    assert response.headers.get("X-Request-ID") == "test-correlation-123"
