"""Routing API endpoints."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schemas import (
    RoutingDecision,
    RoutingRequest,
    RoutingRuleCreate,
    RoutingRuleResponse,
    RoutingRuleUpdate,
)
from app.services.routing_engine import (
    create_rule,
    delete_rule,
    get_route,
    list_rules,
    update_rule,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/routing", tags=["routing"])


@router.post("/route", response_model=RoutingDecision)
async def get_route_endpoint(
    request: RoutingRequest, db: AsyncSession = Depends(get_db)
) -> RoutingDecision:
    """Determine payment route based on configured rules."""
    logger.info(
        "routing_request",
        payment_type=request.payment_type.value,
        merchant_id=request.merchant_id,
        amount=str(request.amount),
    )
    decision = await get_route(request, db)
    logger.info(
        "routing_decision",
        route_target=decision.route_target,
        is_default=decision.is_default,
    )
    return decision


@router.post("/rules", response_model=RoutingRuleResponse, status_code=201)
async def create_rule_endpoint(
    rule: RoutingRuleCreate, db: AsyncSession = Depends(get_db)
) -> RoutingRuleResponse:
    """Create a new routing rule."""
    if rule.amount_min >= rule.amount_max:
        raise HTTPException(status_code=400, detail="amount_min must be less than amount_max")
    created = await create_rule(rule, db)
    logger.info("rule_created", rule_id=created.id)
    return created


@router.get("/rules/{merchant_id}", response_model=list[RoutingRuleResponse])
async def list_rules_endpoint(
    merchant_id: str, db: AsyncSession = Depends(get_db)
) -> list[RoutingRuleResponse]:
    """List routing rules for a merchant (includes global rules)."""
    return await list_rules(merchant_id, db)


@router.patch("/rules/{rule_id}", response_model=RoutingRuleResponse)
async def update_rule_endpoint(
    rule_id: str, updates: RoutingRuleUpdate, db: AsyncSession = Depends(get_db)
) -> RoutingRuleResponse:
    """Update an existing routing rule."""
    result = await update_rule(rule_id, updates, db)
    if not result:
        raise HTTPException(status_code=404, detail="Rule not found")
    logger.info("rule_updated", rule_id=rule_id)
    return result


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule_endpoint(
    rule_id: str, db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a routing rule."""
    deleted = await delete_rule(rule_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    logger.info("rule_deleted", rule_id=rule_id)
