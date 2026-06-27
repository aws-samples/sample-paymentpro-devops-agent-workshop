"""Routing engine — rule evaluation and route selection."""

from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.enums.types import PaymentType

from app.models.db_models import RoutingRuleDB
from app.models.schemas import (
    RoutingDecision,
    RoutingRequest,
    RoutingRuleCreate,
    RoutingRuleResponse,
    RoutingRuleUpdate,
)

logger = structlog.get_logger()

# Default providers per payment type
DEFAULT_PROVIDERS: dict[str, str] = {
    "UPI": "default_upi_provider",
    "CREDIT_CARD": "default_card_provider",
    "DEBIT_CARD": "default_card_provider",
    "WALLET": "default_wallet_provider",
}


async def get_route(request: RoutingRequest, db: AsyncSession) -> RoutingDecision:
    """Determine payment route based on rules.

    Priority: merchant-specific rules first, then global rules, then defaults.
    Lowest priority value wins (priority 1 = highest rank).
    """
    # Try merchant-specific rules first
    stmt = (
        select(RoutingRuleDB)
        .where(
            RoutingRuleDB.merchant_id == request.merchant_id,
            RoutingRuleDB.payment_type == request.payment_type.value,
            RoutingRuleDB.amount_min <= request.amount,
            RoutingRuleDB.amount_max >= request.amount,
            RoutingRuleDB.is_active == True,  # noqa: E712
        )
        .order_by(RoutingRuleDB.priority.asc())
        .limit(1)
    )
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()

    if rule:
        logger.info("route_matched", rule_id=rule.id, merchant_id=request.merchant_id)
        return RoutingDecision(
            route_target=rule.route_target,
            rule_id=rule.id,
            priority=rule.priority,
            is_default=False,
        )

    # Try global rules (merchant_id IS NULL)
    stmt = (
        select(RoutingRuleDB)
        .where(
            RoutingRuleDB.merchant_id.is_(None),
            RoutingRuleDB.payment_type == request.payment_type.value,
            RoutingRuleDB.amount_min <= request.amount,
            RoutingRuleDB.amount_max >= request.amount,
            RoutingRuleDB.is_active == True,  # noqa: E712
        )
        .order_by(RoutingRuleDB.priority.asc())
        .limit(1)
    )
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()

    if rule:
        logger.info("route_matched_global", rule_id=rule.id)
        return RoutingDecision(
            route_target=rule.route_target,
            rule_id=rule.id,
            priority=rule.priority,
            is_default=False,
        )

    # Default fallback
    default_target = DEFAULT_PROVIDERS.get(request.payment_type.value, "default_gateway")
    logger.info("route_default", payment_type=request.payment_type.value, target=default_target)
    return RoutingDecision(
        route_target=default_target,
        rule_id=None,
        priority=None,
        is_default=True,
    )


async def create_rule(rule_data: RoutingRuleCreate, db: AsyncSession) -> RoutingRuleResponse:
    """Create a new routing rule."""
    now = datetime.now(timezone.utc)
    db_rule = RoutingRuleDB(
        id=str(uuid4()),
        merchant_id=rule_data.merchant_id,
        payment_type=rule_data.payment_type.value,
        amount_min=rule_data.amount_min,
        amount_max=rule_data.amount_max,
        priority=rule_data.priority,
        route_target=rule_data.route_target,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(db_rule)
    await db.commit()
    await db.refresh(db_rule)
    return RoutingRuleResponse.model_validate(db_rule)


async def list_rules(merchant_id: str, db: AsyncSession) -> list[RoutingRuleResponse]:
    """List routing rules for a merchant (includes global rules)."""
    stmt = (
        select(RoutingRuleDB)
        .where(
            (RoutingRuleDB.merchant_id == merchant_id) | (RoutingRuleDB.merchant_id.is_(None))
        )
        .order_by(RoutingRuleDB.priority.asc())
    )
    result = await db.execute(stmt)
    rules = result.scalars().all()
    return [RoutingRuleResponse.model_validate(r) for r in rules]


async def update_rule(
    rule_id: str, updates: RoutingRuleUpdate, db: AsyncSession
) -> RoutingRuleResponse | None:
    """Update an existing routing rule. Returns None if not found."""
    stmt = select(RoutingRuleDB).where(RoutingRuleDB.id == rule_id)
    result = await db.execute(stmt)
    db_rule = result.scalar_one_or_none()

    if not db_rule:
        return None

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "payment_type" and value is not None:
            setattr(db_rule, field, value.value)
        else:
            setattr(db_rule, field, value)

    db_rule.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_rule)
    return RoutingRuleResponse.model_validate(db_rule)


async def delete_rule(rule_id: str, db: AsyncSession) -> bool:
    """Delete a routing rule. Returns False if not found."""
    stmt = select(RoutingRuleDB).where(RoutingRuleDB.id == rule_id)
    result = await db.execute(stmt)
    db_rule = result.scalar_one_or_none()

    if not db_rule:
        return False

    await db.delete(db_rule)
    await db.commit()
    return True
