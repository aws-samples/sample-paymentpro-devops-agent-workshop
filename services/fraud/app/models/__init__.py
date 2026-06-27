"""Request and response models for the Fraud Service."""

from app.models.requests import (
    AmountValidationRequest,
    CardValidationRequest,
    PaymentValidationRequest,
    UpiValidationRequest,
    WalletValidationRequest,
)

__all__ = [
    "AmountValidationRequest",
    "CardValidationRequest",
    "PaymentValidationRequest",
    "UpiValidationRequest",
    "WalletValidationRequest",
]
