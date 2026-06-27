"""Validation API endpoints."""

from decimal import Decimal

import structlog
from fastapi import APIRouter

from shared.models.validation import ValidationError, ValidationResult

from app.models.requests import (
    AmountValidationRequest,
    CardValidationRequest,
    PaymentValidationRequest,
    UpiValidationRequest,
    WalletValidationRequest,
)
from app.services.amount_validator import validate_amount
from app.services.card_validator import validate_card
from app.services.upi_validator import validate_upi
from app.services.validator import PaymentValidationResult, validate_payment
from app.services.wallet_validator import validate_wallet

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/validate", tags=["validation"])


@router.post("/payment", response_model=PaymentValidationResult)
async def validate_payment_endpoint(request: PaymentValidationRequest) -> PaymentValidationResult:
    """Validate a full payment request.

    This is the primary endpoint called by the Payment Service before processing.
    Dispatches to type-specific validators and returns all errors at once.
    """
    logger.info(
        "validation_request",
        payment_type=request.payment_type.value,
        merchant_id=request.merchant_id,
    )

    result = validate_payment(request)

    logger.info(
        "validation_complete",
        payment_type=request.payment_type.value,
        merchant_id=request.merchant_id,
        valid=result.valid,
        error_count=len(result.errors),
    )

    return result


@router.post("/card", response_model=ValidationResult)
async def validate_card_endpoint(request: CardValidationRequest) -> ValidationResult:
    """Validate card details only (utility endpoint)."""
    errors = validate_card(request.card_number, request.card_expiry, request.cvv)
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
    )


@router.post("/upi", response_model=ValidationResult)
async def validate_upi_endpoint(request: UpiValidationRequest) -> ValidationResult:
    """Validate UPI ID only (utility endpoint)."""
    errors = validate_upi(request.upi_id)
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
    )


@router.post("/wallet", response_model=ValidationResult)
async def validate_wallet_endpoint(request: WalletValidationRequest) -> ValidationResult:
    """Validate wallet details only (utility endpoint)."""
    errors = validate_wallet(request.wallet_id, request.wallet_balance, request.amount)
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
    )


@router.post("/amount", response_model=ValidationResult)
async def validate_amount_endpoint(request: AmountValidationRequest) -> ValidationResult:
    """Validate amount only (utility endpoint)."""
    errors = validate_amount(request.amount)
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
    )
