"""Transaction-related models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from shared.constants.config import CURRENCY
from shared.enums.types import PaymentType, TransactionStatus
from shared.utils.datetime_utils import utc_now
from shared.utils.id_generator import generate_id


class PaymentRequest(BaseModel):
    """Incoming payment request DTO."""

    payment_type: PaymentType
    amount: Decimal = Field(gt=0)
    card_number: Optional[str] = None
    card_expiry: Optional[str] = None
    card_cvv: Optional[str] = None
    upi_id: Optional[str] = None
    wallet_id: Optional[str] = None


class PaymentResponse(BaseModel):
    """Payment processing response DTO."""

    transaction_id: str
    status: TransactionStatus
    amount: Decimal
    currency: str = CURRENCY
    timestamp: str
    message: str


class Transaction(BaseModel):
    """Transaction record."""

    id: str = Field(default_factory=generate_id)
    merchant_id: str
    payment_type: PaymentType
    amount: Decimal
    currency: str = CURRENCY
    status: TransactionStatus = TransactionStatus.PENDING
    route_id: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
