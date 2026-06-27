"""Tests for payment processing endpoints."""

import pytest
import respx
from httpx import AsyncClient, Response


VALID_CARD_PAYMENT = {
    "payment_type": "CREDIT_CARD",
    "amount": "100.00",
    "merchant_id": "merchant_1",
    "card_number": "4111111111111111",
    "card_expiry": "12/30",
    "cvv": "123",
}


@pytest.fixture(autouse=True)
def mock_services():
    """Mock downstream service calls."""
    with respx.mock(assert_all_called=False) as respx_mock:
        # Mock Fraud Service — valid by default
        respx_mock.post("http://fraud-mock/api/v1/validate/payment").mock(
            return_value=Response(200, json={"valid": True, "errors": []})
        )
        # Mock Routing Service
        respx_mock.post("http://routing-mock/api/v1/routing/route").mock(
            return_value=Response(
                200,
                json={
                    "route_target": "razorpay",
                    "rule_id": "rule-1",
                    "priority": 1,
                    "is_default": False,
                },
            )
        )
        yield respx_mock


@pytest.mark.asyncio
async def test_create_payment_success(
    client: AsyncClient, auth_headers: dict, mock_services: respx.MockRouter
) -> None:
    """Successful payment should return 201 with transaction ID."""
    # Force success by setting high success rate
    import app.services.payment_processor as pp
    original_rate = pp.settings.success_rate
    pp.settings.success_rate = 1.0  # Always succeed

    response = await client.post("/api/v1/payments", json=VALID_CARD_PAYMENT, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "transaction_id" in data
    assert data["route_target"] == "razorpay"

    pp.settings.success_rate = original_rate


@pytest.mark.asyncio
async def test_create_payment_validation_failure(
    client: AsyncClient, auth_headers: dict, mock_services: respx.MockRouter
) -> None:
    """Payment with validation errors should fail."""
    # Override fraud mock to return invalid
    mock_services.post("http://fraud-mock/api/v1/validate/payment").mock(
        return_value=Response(
            200,
            json={
                "valid": False,
                "errors": [
                    {"field": "card_number", "code": "LUHN_CHECK_FAILED", "message": "Invalid card"}
                ],
            },
        )
    )

    response = await client.post("/api/v1/payments", json=VALID_CARD_PAYMENT, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "FAILED"
    assert "validation failed" in data["message"].lower()


@pytest.mark.asyncio
async def test_create_payment_fraud_service_down(
    client: AsyncClient, auth_headers: dict, mock_services: respx.MockRouter
) -> None:
    """If fraud service is unavailable, payment should fail (fail closed)."""
    mock_services.post("http://fraud-mock/api/v1/validate/payment").mock(
        side_effect=Exception("Connection refused")
    )

    response = await client.post("/api/v1/payments", json=VALID_CARD_PAYMENT, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "FAILED"
    assert "unavailable" in data["message"].lower()


@pytest.mark.asyncio
async def test_create_payment_routing_service_down(
    client: AsyncClient, auth_headers: dict, mock_services: respx.MockRouter
) -> None:
    """If routing service is down, payment should still proceed with default route."""
    import app.services.payment_processor as pp
    original_rate = pp.settings.success_rate
    pp.settings.success_rate = 1.0

    mock_services.post("http://routing-mock/api/v1/routing/route").mock(
        side_effect=Exception("Connection refused")
    )

    response = await client.post("/api/v1/payments", json=VALID_CARD_PAYMENT, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    # Should succeed with default gateway
    assert data["status"] == "SUCCESS"

    pp.settings.success_rate = original_rate


@pytest.mark.asyncio
async def test_get_transaction(client: AsyncClient, auth_headers: dict) -> None:
    """Should retrieve a transaction by ID."""
    import app.services.payment_processor as pp
    original_rate = pp.settings.success_rate
    pp.settings.success_rate = 1.0

    # Create a payment first
    create_resp = await client.post(
        "/api/v1/payments", json=VALID_CARD_PAYMENT, headers=auth_headers
    )
    txn_id = create_resp.json()["transaction_id"]

    # Get it
    response = await client.get(f"/api/v1/payments/{txn_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == txn_id
    assert data["merchant_id"] == "merchant_1"
    assert data["payment_type"] == "CREDIT_CARD"

    pp.settings.success_rate = original_rate


@pytest.mark.asyncio
async def test_get_transaction_not_found(client: AsyncClient, auth_headers: dict) -> None:
    """Non-existent transaction should return 404."""
    response = await client.get("/api/v1/payments/nonexistent", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_transactions(client: AsyncClient, auth_headers: dict) -> None:
    """Should list transactions with pagination."""
    import app.services.payment_processor as pp
    original_rate = pp.settings.success_rate
    pp.settings.success_rate = 1.0

    # Create two payments
    await client.post("/api/v1/payments", json=VALID_CARD_PAYMENT, headers=auth_headers)
    await client.post("/api/v1/payments", json=VALID_CARD_PAYMENT, headers=auth_headers)

    response = await client.get(
        "/api/v1/payments?merchant_id=merchant_1", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["page"] == 1

    pp.settings.success_rate = original_rate


@pytest.mark.asyncio
async def test_list_transactions_filter_by_status(
    client: AsyncClient, auth_headers: dict
) -> None:
    """Should filter transactions by status."""
    import app.services.payment_processor as pp
    original_rate = pp.settings.success_rate
    pp.settings.success_rate = 1.0

    await client.post("/api/v1/payments", json=VALID_CARD_PAYMENT, headers=auth_headers)

    response = await client.get(
        "/api/v1/payments?status=SUCCESS", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert all(item["status"] == "SUCCESS" for item in data["items"])

    pp.settings.success_rate = original_rate


@pytest.mark.asyncio
async def test_public_endpoint_no_auth_needed(client: AsyncClient) -> None:
    """Payment creation is a public-facing endpoint — no auth required."""
    response = await client.post("/api/v1/payments", json=VALID_CARD_PAYMENT)
    # Should not get 401 — payments endpoint is public
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """Health check should work without auth."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "payment-service"
