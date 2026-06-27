"""Request models for validation endpoints."""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from shared.enums.types import PaymentType


class PaymentValidationRequest(BaseModel):
    """Full payment validation request."""

    payment_type: PaymentType
    amount: Decimal = Field(gt=0)
    merchant_id: str = Field(min_length=1)
    card_number: Optional[str] = None
    card_expiry: Optional[str] = None
    cvv: Optional[str] = None
    upi_id: Optional[str] = None
    wallet_id: Optional[str] = None
    wallet_balance: Optional[Decimal] = None


class CardValidationRequest(BaseModel):
    """Card-only validation request."""

    card_number: str
    card_expiry: str
    cvv: str


class UpiValidationRequest(BaseModel):
    """UPI-only validation request."""

    upi_id: str


class WalletValidationRequest(BaseModel):
    """Wallet-only validation request."""

    wallet_id: str
    wallet_balance: Decimal
    amount: Decimal = Field(gt=0)


class AmountValidationRequest(BaseModel):
    """Amount-only validation request."""

    amount: Decimal
