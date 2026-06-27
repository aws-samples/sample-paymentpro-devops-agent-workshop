"""Amount validation logic."""

from decimal import Decimal, InvalidOperation

from shared.constants.config import MAX_AMOUNT, MIN_AMOUNT
from shared.models.validation import ValidationError


def validate_amount(amount: Decimal) -> list[ValidationError]:
    """Validate payment amount is positive, within limits, and has valid precision.

    Args:
        amount: Payment amount to validate.

    Returns:
        List of validation errors (empty if valid).
    """
    errors: list[ValidationError] = []

    try:
        decimal_amount = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError):
        errors.append(
            ValidationError(
                field="amount",
                code="INVALID_AMOUNT",
                message="Amount is not a valid number.",
            )
        )
        return errors

    if decimal_amount <= 0:
        errors.append(
            ValidationError(
                field="amount",
                code="INVALID_AMOUNT",
                message="Amount must be positive.",
            )
        )
        return errors

    if decimal_amount < MIN_AMOUNT:
        errors.append(
            ValidationError(
                field="amount",
                code="AMOUNT_TOO_LOW",
                message=f"Amount must be at least {MIN_AMOUNT}.",
            )
        )

    if decimal_amount > MAX_AMOUNT:
        errors.append(
            ValidationError(
                field="amount",
                code="AMOUNT_TOO_HIGH",
                message=f"Amount must not exceed {MAX_AMOUNT}.",
            )
        )

    # Check max 2 decimal places
    if decimal_amount != decimal_amount.quantize(Decimal("0.01")):
        errors.append(
            ValidationError(
                field="amount",
                code="INVALID_AMOUNT",
                message="Amount must have at most 2 decimal places.",
            )
        )

    return errors
