"""Validation utility functions."""

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from shared.constants.config import MAX_AMOUNT, MIN_AMOUNT


def validate_luhn(card_number: str) -> bool:
    """Validate a card number using the Luhn algorithm.

    Args:
        card_number: Card number as string (digits only, 16 characters).

    Returns:
        True if the card number passes Luhn validation.
    """
    if not card_number or not card_number.isdigit() or len(card_number) != 16:
        return False

    if card_number == "0" * 16:
        return False

    digits = [int(d) for d in card_number]
    # Double every second digit from the right
    for i in range(len(digits) - 2, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9

    return sum(digits) % 10 == 0


def validate_email(email: str) -> bool:
    """Validate email format.

    Args:
        email: Email address string.

    Returns:
        True if the email has a valid format.
    """
    if not email or len(email) > 254:
        return False

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_upi_id(upi_id: str) -> bool:
    """Validate UPI ID format (username@provider).

    Args:
        upi_id: UPI ID string.

    Returns:
        True if the UPI ID has a valid format.
    """
    if not upi_id:
        return False

    pattern = r"^[a-zA-Z0-9.]{3,50}@[a-zA-Z0-9]{2,20}$"
    return bool(re.match(pattern, upi_id))


def validate_card_expiry(expiry: str) -> bool:
    """Validate card expiry is in MM/YY format and not expired.

    Args:
        expiry: Expiry string in MM/YY format.

    Returns:
        True if the expiry is valid and not in the past.
    """
    if not expiry:
        return False

    pattern = r"^(0[1-9]|1[0-2])/(\d{2})$"
    match = re.match(pattern, expiry)
    if not match:
        return False

    month = int(match.group(1))
    year = int(match.group(2)) + 2000

    now = datetime.now(timezone.utc)
    # Card is valid through the end of the expiry month
    if year < now.year:
        return False
    if year == now.year and month < now.month:
        return False

    return True


def validate_amount(
    amount: Decimal | str | float,
    max_amount: Decimal = MAX_AMOUNT,
    min_amount: Decimal = MIN_AMOUNT,
) -> bool:
    """Validate payment amount.

    Args:
        amount: Payment amount.
        max_amount: Maximum allowed amount.
        min_amount: Minimum allowed amount.

    Returns:
        True if the amount is valid (positive, within limits, max 2 decimal places).
    """
    try:
        decimal_amount = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError):
        return False

    if decimal_amount < min_amount:
        return False
    if decimal_amount > max_amount:
        return False

    # Check max 2 decimal places
    if decimal_amount != decimal_amount.quantize(Decimal("0.01")):
        return False

    return True
