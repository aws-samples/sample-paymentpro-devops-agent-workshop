"""HTTP clients for calling downstream services (Fraud, Routing, Merchant)."""

from decimal import Decimal
from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


async def call_fraud_service(payment_data: dict[str, Any]) -> dict[str, Any]:
    """Call Fraud Service to validate payment inputs.

    Returns validation result dict with 'valid' and 'errors' keys.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{settings.fraud_service_url}/api/v1/validate/payment",
            json=payment_data,
            headers={"X-Service-Key": settings.service_secret},
        )
        response.raise_for_status()
        return response.json()


async def call_routing_service(
    payment_type: str, amount: str, merchant_id: str
) -> dict[str, Any]:
    """Call Routing Service to determine payment route.

    Returns routing decision dict with 'route_target' and 'is_default' keys.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{settings.routing_service_url}/api/v1/routing/route",
            json={
                "payment_type": payment_type,
                "amount": amount,
                "merchant_id": merchant_id,
            },
            headers={"X-Service-Key": settings.service_secret},
        )
        response.raise_for_status()
        return response.json()


async def call_merchant_validate_key(api_key: str) -> dict[str, Any]:
    """Call Merchant Service to validate an API key.

    Returns dict with 'valid' and 'merchant_id' keys.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{settings.merchant_service_url}/api/v1/merchants/validate-key",
            params={"api_key": api_key},
            headers={"X-Service-Key": settings.service_secret},
        )
        response.raise_for_status()
        return response.json()
