"""Wallet validation logic — ID format and balance sufficiency."""

import re
from decimal import Decimal

from shared.models.validation import ValidationError


def validate_wallet(
    wallet_id: str, wallet_balance: Decimal, amount: Decimal
) -> list[ValidationError]:
    """Validate wallet ID format and balance sufficiency.

    Args:
        wallet_id: Wallet identifier.
        wallet_balance: Current wallet balance (provided by caller).
        amount: Payment amount to validate against balance.

    Returns:
        List of validation errors (empty if valid).
    """
    errors: list[ValidationError] = []

    # Validate wallet ID format: alphanumeric, 8-32 characters
    if not wallet_id:
        errors.append(
            ValidationError(
                field="wallet_id",
                code="INVALID_WALLET_ID",
                message="Wallet ID must not be empty.",
            )
        )
    elif not re.match(r"^[a-zA-Z0-9]{8,32}$", wallet_id):
        errors.append(
            ValidationError(
                field="wallet_id",
                code="INVALID_WALLET_ID",
                message="Wallet ID must be 8-32 alphanumeric characters.",
            )
        )

    # Validate balance sufficiency
    if wallet_balance < amount:
        errors.append(
            ValidationError(
                field="wallet_balance",
                code="INSUFFICIENT_BALANCE",
                message=f"Insufficient wallet balance: {wallet_balance} < {amount}.",
            )
        )

    return errors
