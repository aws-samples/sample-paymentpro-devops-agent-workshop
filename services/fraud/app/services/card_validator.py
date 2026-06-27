"""Card validation logic — Luhn algorithm, expiry, CVV, network detection."""

import re
from datetime import datetime, timezone
from enum import Enum

from shared.models.validation import ValidationError


class CardNetwork(str, Enum):
    """Detected card network."""

    AMEX = "amex"
    VISA = "visa"
    MASTERCARD = "mastercard"
    GENERIC = "generic"


def detect_card_network(card_number: str) -> CardNetwork:
    """Detect card network from card number prefix.

    Args:
        card_number: Cleaned card number (digits only).

    Returns:
        Detected card network.
    """
    if not card_number:
        return CardNetwork.GENERIC

    if card_number[:2] in ("34", "37"):
        return CardNetwork.AMEX

    if card_number[0] == "4":
        return CardNetwork.VISA

    # Mastercard: 51-55 or 2221-2720
    if len(card_number) >= 2:
        prefix2 = int(card_number[:2])
        if 51 <= prefix2 <= 55:
            return CardNetwork.MASTERCARD

    if len(card_number) >= 4:
        prefix4 = int(card_number[:4])
        if 2221 <= prefix4 <= 2720:
            return CardNetwork.MASTERCARD

    return CardNetwork.GENERIC


def _validate_luhn(card_number: str) -> bool:
    """Apply Luhn algorithm to card number.

    Args:
        card_number: Digits-only card number string.

    Returns:
        True if passes Luhn check.
    """
    digits = [int(d) for d in card_number]
    # Double every second digit from the right
    for i in range(len(digits) - 2, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    return sum(digits) % 10 == 0


def validate_card(card_number: str, card_expiry: str, cvv: str) -> list[ValidationError]:
    """Validate card details: number (Luhn), expiry, and CVV.

    Args:
        card_number: Card number (may contain spaces/dashes).
        card_expiry: Expiry in MM/YY format.
        cvv: CVV code.

    Returns:
        List of validation errors (empty if valid).
    """
    errors: list[ValidationError] = []

    # Clean card number — strip spaces and dashes
    cleaned_number = re.sub(r"[\s\-]", "", card_number)

    # Validate card number format
    if not cleaned_number.isdigit():
        errors.append(
            ValidationError(
                field="card_number",
                code="INVALID_CARD_FORMAT",
                message="Card number must contain only digits.",
            )
        )
    elif len(cleaned_number) < 13 or len(cleaned_number) > 19:
        errors.append(
            ValidationError(
                field="card_number",
                code="INVALID_CARD_LENGTH",
                message="Card number must be 13-19 digits.",
            )
        )
    else:
        # Luhn check
        if not _validate_luhn(cleaned_number):
            errors.append(
                ValidationError(
                    field="card_number",
                    code="LUHN_CHECK_FAILED",
                    message="Card number fails Luhn validation.",
                )
            )

    # Detect network for CVV validation
    network = detect_card_network(cleaned_number) if cleaned_number.isdigit() else CardNetwork.GENERIC

    # Validate CVV
    if not cvv or not cvv.isdigit():
        errors.append(
            ValidationError(
                field="cvv",
                code="INVALID_CVV",
                message="CVV must contain only digits.",
            )
        )
    else:
        expected_length = 4 if network == CardNetwork.AMEX else 3
        if len(cvv) != expected_length:
            errors.append(
                ValidationError(
                    field="cvv",
                    code="INVALID_CVV",
                    message=f"CVV must be {expected_length} digits for {network.value} cards.",
                )
            )

    # Validate expiry
    expiry_errors = _validate_expiry(card_expiry)
    errors.extend(expiry_errors)

    return errors


def _validate_expiry(card_expiry: str) -> list[ValidationError]:
    """Validate card expiry date.

    Args:
        card_expiry: Expiry string in MM/YY format.

    Returns:
        List of validation errors.
    """
    errors: list[ValidationError] = []

    pattern = r"^(0[1-9]|1[0-2])/(\d{2})$"
    match = re.match(pattern, card_expiry)

    if not match:
        errors.append(
            ValidationError(
                field="card_expiry",
                code="INVALID_EXPIRY_FORMAT",
                message="Card expiry must be in MM/YY format.",
            )
        )
        return errors

    month = int(match.group(1))
    year = int(match.group(2)) + 2000

    now = datetime.now(timezone.utc)

    # Card is valid through the end of the expiry month (current month is valid)
    if year < now.year or (year == now.year and month < now.month):
        errors.append(
            ValidationError(
                field="card_expiry",
                code="EXPIRED_CARD",
                message="Card has expired.",
            )
        )

    return errors
