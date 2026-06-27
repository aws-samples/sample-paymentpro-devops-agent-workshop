"""Routing-related models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from shared.enums.types import PaymentType
from shared.utils.datetime_utils import utc_now
from shared.utils.id_generator import generate_id


class RoutingRule(BaseModel):
    """Routing rule definition."""

    id: str = Field(default_factory=generate_id)
    merchant_id: str
    payment_type: Optional[PaymentType] = None
    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None
    priority: int = Field(ge=1, le=100)
    route_target: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class RoutingRequest(BaseModel):
    """Request to evaluate routing rules."""

    payment_type: PaymentType
    amount: Decimal
    merchant_id: str


class RoutingDecision(BaseModel):
    """Result of routing rule evaluation."""

    route_id: str
    provider: str
    priority: int
