"""Payment validation orchestrator — dispatches to type-specific validators."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

from shared.enums.types import PaymentType
from shared.models.validation import ValidationError, ValidationResult

from app.models.requests import PaymentValidationRequest
from app.services.amount_validator import validate_amount
from app.services.card_validator import validate_card
from app.services.upi_validator import validate_upi
from app.services.wallet_validator import validate_wallet


class PaymentValidationResult(BaseModel):
    """Extended validation result with payment context."""

    valid: bool
    errors: list[ValidationError] = []
    payment_type: Optional[PaymentType] = None
    validated_at: Optional[datetime] = None


# Required fields per payment type
REQUIRED_FIELDS: dict[PaymentType, list[str]] = {
    PaymentType.CREDIT_CARD: ["card_number", "card_expiry", "cvv"],
    PaymentType.DEBIT_CARD: ["card_number", "card_expiry", "cvv"],
    PaymentType.UPI: ["upi_id"],
    PaymentType.WALLET: ["wallet_id", "wallet_balance"],
}


def _check_required_fields(request: PaymentValidationRequest) -> list[ValidationError]:
    """Check that required fields for the payment type are present.

    Args:
        request: Payment validation request.

    Returns:
        List of missing field errors.
    """
    errors: list[ValidationError] = []
    required = REQUIRED_FIELDS.get(request.payment_type, [])

    for field_name in required:
        value = getattr(request, field_name, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(
                ValidationError(
                    field=field_name,
                    code="MISSING_REQUIRED_FIELD",
                    message=f"Field '{field_name}' is required for {request.payment_type.value} payments.",
                )
            )

    return errors


def validate_payment(request: PaymentValidationRequest) -> PaymentValidationResult:
    """Validate a full payment request by dispatching to type-specific validators.

    All validators run regardless of earlier failures (fail-open pattern).
    All errors are aggregated and returned together.

    Args:
        request: Full payment validation request.

    Returns:
        PaymentValidationResult with pass/fail and all errors.
    """
    errors: list[ValidationError] = []

    # Check required fields first
    missing_errors = _check_required_fields(request)
    errors.extend(missing_errors)

    # Always validate amount
    amount_errors = validate_amount(request.amount)
    errors.extend(amount_errors)

    # Dispatch to type-specific validator (only if required fields are present)
    if not missing_errors:
        type_errors = _dispatch_type_validator(request)
        errors.extend(type_errors)

    return PaymentValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        payment_type=request.payment_type,
        validated_at=datetime.now(timezone.utc),
    )


def _dispatch_type_validator(request: PaymentValidationRequest) -> list[ValidationError]:
    """Dispatch to the appropriate type-specific validator.

    Args:
        request: Payment validation request with all required fields present.

    Returns:
        List of type-specific validation errors.
    """
    match request.payment_type:
        case PaymentType.CREDIT_CARD | PaymentType.DEBIT_CARD:
            return validate_card(
                card_number=request.card_number,  # type: ignore[arg-type]
                card_expiry=request.card_expiry,  # type: ignore[arg-type]
                cvv=request.cvv,  # type: ignore[arg-type]
            )
        case PaymentType.UPI:
            return validate_upi(upi_id=request.upi_id)  # type: ignore[arg-type]
        case PaymentType.WALLET:
            return validate_wallet(
                wallet_id=request.wallet_id,  # type: ignore[arg-type]
                wallet_balance=request.wallet_balance,  # type: ignore[arg-type]
                amount=request.amount,
            )
        case _:
            return [
                ValidationError(
                    field="payment_type",
                    code="UNSUPPORTED_PAYMENT_TYPE",
                    message=f"Unsupported payment type: {request.payment_type}.",
                )
            ]
