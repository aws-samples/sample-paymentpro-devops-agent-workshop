"""Pydantic schemas for Payment Service API."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from shared.enums.types import PaymentType


class PaymentRequest(BaseModel):
    """Incoming payment request."""

    payment_type: PaymentType
    amount: Decimal = Field(gt=0)
    currency: str = "INR"
    merchant_id: str = Field(min_length=1)
    # Type-specific fields
    card_number: Optional[str] = None
    card_expiry: Optional[str] = None
    cvv: Optional[str] = None
    upi_id: Optional[str] = None
    wallet_id: Optional[str] = None
    wallet_balance: Optional[Decimal] = None


class PaymentResponse(BaseModel):
    """Payment processing response."""

    transaction_id: str
    status: str
    message: str
    route_target: Optional[str] = None
    created_at: datetime


class TransactionDetail(BaseModel):
    """Full transaction detail."""

    id: str
    merchant_id: str
    payment_type: str
    amount: Decimal
    currency: str
    status: str
    route_target: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransactionFilters(BaseModel):
    """Query filters for listing transactions."""

    merchant_id: Optional[str] = None
    status: Optional[str] = None
    payment_type: Optional[str] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedTransactions(BaseModel):
    """Paginated transaction list."""

    items: list[TransactionDetail]
    total: int
    page: int
    limit: int
