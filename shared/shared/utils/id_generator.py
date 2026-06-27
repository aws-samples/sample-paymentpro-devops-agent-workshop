"""ID generation utilities."""

import secrets
import uuid


def generate_id() -> str:
    """Generate a new UUID v4 string.

    Returns:
        UUID v4 as lowercase string with hyphens.
    """
    return str(uuid.uuid4())


def generate_api_key_value() -> str:
    """Generate a cryptographically secure 64-character hex API key.

    Returns:
        64-character lowercase hexadecimal string.
    """
    return secrets.token_hex(32)
