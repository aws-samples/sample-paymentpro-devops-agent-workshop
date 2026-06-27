"""Pydantic schemas for API request/response models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from shared.enums.types import PaymentType


class RoutingRuleCreate(BaseModel):
    """Request model for creating a routing rule."""

    merchant_id: Optional[str] = None
    payment_type: PaymentType
    amount_min: Decimal = Field(default=Decimal("0.00"), ge=0)
    amount_max: Decimal = Field(default=Decimal("10000000.00"), ge=0)
    priority: int = Field(gt=0)
    route_target: str = Field(min_length=1, max_length=100)


class RoutingRuleUpdate(BaseModel):
    """Request model for updating a routing rule (partial)."""

    payment_type: Optional[PaymentType] = None
    amount_min: Optional[Decimal] = Field(default=None, ge=0)
    amount_max: Optional[Decimal] = Field(default=None, ge=0)
    priority: Optional[int] = Field(default=None, gt=0)
    route_target: Optional[str] = Field(default=None, min_length=1, max_length=100)
    is_active: Optional[bool] = None


class RoutingRuleResponse(BaseModel):
    """Response model for a routing rule."""

    id: str
    merchant_id: Optional[str] = None
    payment_type: str
    amount_min: Decimal
    amount_max: Decimal
    priority: int
    route_target: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoutingRequest(BaseModel):
    """Request model for getting a routing decision."""

    payment_type: PaymentType
    amount: Decimal = Field(gt=0)
    merchant_id: str = Field(min_length=1)


class RoutingDecision(BaseModel):
    """Response model for a routing decision."""

    route_target: str
    rule_id: Optional[str] = None
    priority: Optional[int] = None
    is_default: bool = False
