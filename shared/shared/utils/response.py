"""API response formatting utilities (RFC 7807 Problem Details)."""

from typing import Any

from shared.constants.config import ERROR_TYPE_BASE_URL
from shared.utils.datetime_utils import format_iso, utc_now


def success_response(data: dict[str, Any], status_code: int = 200) -> dict[str, Any]:
    """Create standard success response envelope.

    Args:
        data: Response data dictionary.
        status_code: HTTP status code.

    Returns:
        Formatted success response.
    """
    return {
        "data": data,
        "timestamp": format_iso(utc_now()),
        "status_code": status_code,
    }


def error_response(
    error_type: str,
    title: str,
    status: int,
    detail: str,
    instance: str,
    errors: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Create RFC 7807 Problem Details error response.

    Args:
        error_type: Error type suffix (e.g., 'validation-error').
        title: Human-readable error title.
        status: HTTP status code.
        detail: Detailed explanation of what went wrong.
        instance: Request instance path (e.g., '/api/v1/payments').
        errors: Optional list of field-level validation errors.

    Returns:
        RFC 7807 compliant error dictionary.
    """
    response: dict[str, Any] = {
        "type": f"{ERROR_TYPE_BASE_URL}/{error_type}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": instance,
    }

    if errors:
        response["errors"] = errors

    return response
