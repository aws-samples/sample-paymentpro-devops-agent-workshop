"""Traffic simulation endpoint for the Admin Dashboard."""

import random
import asyncio
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schemas import PaymentRequest
from app.services.payment_processor import process_payment
from shared.enums.types import PaymentType

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/simulate", tags=["simulate"])

VALID_CARDS = ["4111111111111111", "5500000000000004", "378282246310005"]
VALID_UPI = ["sim_user@paytm", "sim_buyer@oksbi", "sim_shop@ybl", "sim_pay@hdfc"]
WALLET_IDS = ["simwallet1234567", "simwallet7654321", "simwalletABCDEFG"]

PROFILES = {
    "mixed": {"UPI": 40, "CREDIT_CARD": 30, "DEBIT_CARD": 20, "WALLET": 10},
    "cards_only": {"CREDIT_CARD": 50, "DEBIT_CARD": 50},
    "upi_heavy": {"UPI": 80, "CREDIT_CARD": 10, "DEBIT_CARD": 5, "WALLET": 5},
    "burst": {"UPI": 25, "CREDIT_CARD": 25, "DEBIT_CARD": 25, "WALLET": 25},
}


def _pick_type(profile: str) -> str:
    weights = PROFILES.get(profile, PROFILES["mixed"])
    return random.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]


def _generate_request(payment_type: str, merchant_id: str) -> PaymentRequest:
    amount = Decimal(str(round(random.uniform(10, 10000), 2)))
    kwargs: dict = {
        "payment_type": PaymentType(payment_type),
        "amount": amount,
        "currency": "INR",
        "merchant_id": merchant_id,
    }

    if payment_type in ("CREDIT_CARD", "DEBIT_CARD"):
        card = random.choice(VALID_CARDS)
        kwargs["card_number"] = card
        kwargs["card_expiry"] = f"{random.randint(1,12):02d}/30"
        kwargs["cvv"] = "1234" if card.startswith("3") else "123"
    elif payment_type == "UPI":
        kwargs["upi_id"] = random.choice(VALID_UPI)
    elif payment_type == "WALLET":
        kwargs["wallet_id"] = random.choice(WALLET_IDS)
        kwargs["wallet_balance"] = amount + Decimal(str(random.uniform(100, 5000)))

    return PaymentRequest(**kwargs)


@router.post("/traffic")
async def simulate_traffic(
    count: int = 10,
    profile: str = "mixed",
    merchant_id: str = "demo",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate simulated payment traffic.

    Args:
        count: Number of payments to generate (1-100)
        profile: Payment type distribution (mixed, cards_only, upi_heavy, burst)
        merchant_id: Merchant to generate payments for
    """
    count = min(max(count, 1), 100)  # Clamp 1-100

    results = {"total": 0, "success": 0, "failed": 0, "by_type": {}}

    for _ in range(count):
        payment_type = _pick_type(profile)
        request = _generate_request(payment_type, merchant_id)

        try:
            response = await process_payment(request, db)
            results["total"] += 1
            if response.status == "SUCCESS":
                results["success"] += 1
            else:
                results["failed"] += 1
            results["by_type"][payment_type] = results["by_type"].get(payment_type, 0) + 1
        except Exception as e:
            logger.error("simulate_error", error=str(e))
            results["total"] += 1
            results["failed"] += 1

    logger.info("simulation_complete", **results)
    return results
