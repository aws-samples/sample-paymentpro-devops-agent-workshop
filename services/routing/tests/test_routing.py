"""Tests for routing engine and API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_route_default_upi(client: AsyncClient, auth_headers: dict) -> None:
    """No rules configured — should return default UPI provider."""
    payload = {"payment_type": "UPI", "amount": "100.00", "merchant_id": "merchant_1"}
    response = await client.post("/api/v1/routing/route", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["route_target"] == "default_upi_provider"
    assert data["is_default"] is True
    assert data["rule_id"] is None


@pytest.mark.asyncio
async def test_get_route_default_card(client: AsyncClient, auth_headers: dict) -> None:
    """No rules — should return default card provider."""
    payload = {"payment_type": "CREDIT_CARD", "amount": "500.00", "merchant_id": "merchant_1"}
    response = await client.post("/api/v1/routing/route", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["route_target"] == "default_card_provider"
    assert data["is_default"] is True


@pytest.mark.asyncio
async def test_create_rule(client: AsyncClient, auth_headers: dict) -> None:
    """Create a routing rule."""
    payload = {
        "merchant_id": "merchant_1",
        "payment_type": "UPI",
        "amount_min": "0.00",
        "amount_max": "10000.00",
        "priority": 1,
        "route_target": "razorpay",
    }
    response = await client.post("/api/v1/routing/rules", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["route_target"] == "razorpay"
    assert data["priority"] == 1
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_get_route_matches_merchant_rule(client: AsyncClient, auth_headers: dict) -> None:
    """Created rule should be matched for routing."""
    # Create a rule
    rule_payload = {
        "merchant_id": "merchant_1",
        "payment_type": "UPI",
        "amount_min": "0.00",
        "amount_max": "10000.00",
        "priority": 1,
        "route_target": "razorpay",
    }
    await client.post("/api/v1/routing/rules", json=rule_payload, headers=auth_headers)

    # Route should match
    route_payload = {"payment_type": "UPI", "amount": "500.00", "merchant_id": "merchant_1"}
    response = await client.post("/api/v1/routing/route", json=route_payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["route_target"] == "razorpay"
    assert data["is_default"] is False


@pytest.mark.asyncio
async def test_get_route_priority_ordering(client: AsyncClient, auth_headers: dict) -> None:
    """Lower priority value should win."""
    # Create two rules — priority 2 and priority 1
    rule1 = {
        "merchant_id": "merchant_1",
        "payment_type": "UPI",
        "amount_min": "0.00",
        "amount_max": "10000.00",
        "priority": 2,
        "route_target": "payu",
    }
    rule2 = {
        "merchant_id": "merchant_1",
        "payment_type": "UPI",
        "amount_min": "0.00",
        "amount_max": "10000.00",
        "priority": 1,
        "route_target": "razorpay",
    }
    await client.post("/api/v1/routing/rules", json=rule1, headers=auth_headers)
    await client.post("/api/v1/routing/rules", json=rule2, headers=auth_headers)

    # Route should match priority 1 (razorpay)
    route_payload = {"payment_type": "UPI", "amount": "500.00", "merchant_id": "merchant_1"}
    response = await client.post("/api/v1/routing/route", json=route_payload, headers=auth_headers)
    data = response.json()
    assert data["route_target"] == "razorpay"


@pytest.mark.asyncio
async def test_get_route_amount_range_filtering(client: AsyncClient, auth_headers: dict) -> None:
    """Rule should only match if amount is within range."""
    rule = {
        "merchant_id": "merchant_1",
        "payment_type": "UPI",
        "amount_min": "1000.00",
        "amount_max": "5000.00",
        "priority": 1,
        "route_target": "stripe",
    }
    await client.post("/api/v1/routing/rules", json=rule, headers=auth_headers)

    # Amount 500 is outside range — should get default
    route_payload = {"payment_type": "UPI", "amount": "500.00", "merchant_id": "merchant_1"}
    response = await client.post("/api/v1/routing/route", json=route_payload, headers=auth_headers)
    data = response.json()
    assert data["is_default"] is True

    # Amount 2000 is within range — should match
    route_payload = {"payment_type": "UPI", "amount": "2000.00", "merchant_id": "merchant_1"}
    response = await client.post("/api/v1/routing/route", json=route_payload, headers=auth_headers)
    data = response.json()
    assert data["route_target"] == "stripe"
    assert data["is_default"] is False


@pytest.mark.asyncio
async def test_list_rules(client: AsyncClient, auth_headers: dict) -> None:
    """List rules for a merchant."""
    rule = {
        "merchant_id": "merchant_1",
        "payment_type": "UPI",
        "amount_min": "0.00",
        "amount_max": "10000.00",
        "priority": 1,
        "route_target": "razorpay",
    }
    await client.post("/api/v1/routing/rules", json=rule, headers=auth_headers)

    response = await client.get("/api/v1/routing/rules/merchant_1", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["route_target"] == "razorpay"


@pytest.mark.asyncio
async def test_update_rule(client: AsyncClient, auth_headers: dict) -> None:
    """Update an existing rule."""
    # Create
    rule = {
        "merchant_id": "merchant_1",
        "payment_type": "UPI",
        "amount_min": "0.00",
        "amount_max": "10000.00",
        "priority": 1,
        "route_target": "razorpay",
    }
    create_resp = await client.post("/api/v1/routing/rules", json=rule, headers=auth_headers)
    rule_id = create_resp.json()["id"]

    # Update
    update_payload = {"route_target": "stripe", "priority": 2}
    response = await client.patch(
        f"/api/v1/routing/rules/{rule_id}", json=update_payload, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["route_target"] == "stripe"
    assert data["priority"] == 2


@pytest.mark.asyncio
async def test_delete_rule(client: AsyncClient, auth_headers: dict) -> None:
    """Delete a rule."""
    rule = {
        "merchant_id": "merchant_1",
        "payment_type": "UPI",
        "amount_min": "0.00",
        "amount_max": "10000.00",
        "priority": 1,
        "route_target": "razorpay",
    }
    create_resp = await client.post("/api/v1/routing/rules", json=rule, headers=auth_headers)
    rule_id = create_resp.json()["id"]

    # Delete
    response = await client.delete(f"/api/v1/routing/rules/{rule_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify gone
    list_resp = await client.get("/api/v1/routing/rules/merchant_1", headers=auth_headers)
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_delete_rule_not_found(client: AsyncClient, auth_headers: dict) -> None:
    """Delete non-existent rule returns 404."""
    response = await client.delete("/api/v1/routing/rules/nonexistent", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_rule_not_found(client: AsyncClient, auth_headers: dict) -> None:
    """Update non-existent rule returns 404."""
    response = await client.patch(
        "/api/v1/routing/rules/nonexistent", json={"priority": 5}, headers=auth_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_rule_invalid_amount_range(client: AsyncClient, auth_headers: dict) -> None:
    """amount_min >= amount_max should return 400."""
    rule = {
        "merchant_id": "merchant_1",
        "payment_type": "UPI",
        "amount_min": "5000.00",
        "amount_max": "1000.00",
        "priority": 1,
        "route_target": "razorpay",
    }
    response = await client.post("/api/v1/routing/rules", json=rule, headers=auth_headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_auth_required(client: AsyncClient) -> None:
    """Requests without auth should be rejected."""
    payload = {"payment_type": "UPI", "amount": "100.00", "merchant_id": "merchant_1"}
    response = await client.post("/api/v1/routing/route", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_global_rule_fallback(client: AsyncClient, auth_headers: dict) -> None:
    """Global rule should be used when no merchant-specific rule matches."""
    # Create global rule (no merchant_id)
    rule = {
        "payment_type": "CREDIT_CARD",
        "amount_min": "0.00",
        "amount_max": "10000000.00",
        "priority": 1,
        "route_target": "global_card_provider",
    }
    await client.post("/api/v1/routing/rules", json=rule, headers=auth_headers)

    # Route for a merchant with no specific rules
    route_payload = {
        "payment_type": "CREDIT_CARD",
        "amount": "500.00",
        "merchant_id": "merchant_99",
    }
    response = await client.post("/api/v1/routing/route", json=route_payload, headers=auth_headers)
    data = response.json()
    assert data["route_target"] == "global_card_provider"
    assert data["is_default"] is False
