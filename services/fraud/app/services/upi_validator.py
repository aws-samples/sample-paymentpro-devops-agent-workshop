"""UPI ID validation logic — format and known provider check."""

import re

from shared.models.validation import ValidationError

# Known valid UPI providers
KNOWN_UPI_PROVIDERS: set[str] = {
    "upi",
    "paytm",
    "oksbi",
    "ybl",
    "ibl",
    "axl",
    "sbi",
    "icici",
    "hdfc",
    "kotak",
    "apl",
    "freecharge",
    "okhdfcbank",
    "okaxis",
    "okicici",
    "jupiteraxis",
}


def validate_upi(upi_id: str) -> list[ValidationError]:
    """Validate UPI ID format and provider.

    Args:
        upi_id: UPI ID string (expected format: username@provider).

    Returns:
        List of validation errors (empty if valid).
    """
    errors: list[ValidationError] = []

    if not upi_id:
        errors.append(
            ValidationError(
                field="upi_id",
                code="INVALID_UPI_FORMAT",
                message="UPI ID must not be empty.",
            )
        )
        return errors

    # Check format: username@provider
    # Username: 1-50 chars, alphanumeric + dots + underscores
    # Provider: alphanumeric
    pattern = r"^[a-zA-Z0-9._]{1,50}@([a-zA-Z0-9]+)$"
    match = re.match(pattern, upi_id)

    if not match:
        errors.append(
            ValidationError(
                field="upi_id",
                code="INVALID_UPI_FORMAT",
                message="UPI ID must be in format username@provider "
                "(alphanumeric, dots, underscores allowed in username).",
            )
        )
        return errors

    # Check provider against known list
    provider = match.group(1).lower()
    if provider not in KNOWN_UPI_PROVIDERS:
        errors.append(
            ValidationError(
                field="upi_id",
                code="UNKNOWN_UPI_PROVIDER",
                message=f"Unknown UPI provider: '{provider}'. "
                f"Known providers: {', '.join(sorted(KNOWN_UPI_PROVIDERS))}.",
            )
        )

    return errors
