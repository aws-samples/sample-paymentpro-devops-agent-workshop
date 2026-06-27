"""Date and time utility functions."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Get current UTC timestamp.

    Returns:
        Timezone-aware datetime in UTC.
    """
    return datetime.now(timezone.utc)


def format_iso(dt: datetime) -> str:
    """Format datetime as ISO 8601 string.

    Args:
        dt: Datetime object to format.

    Returns:
        ISO 8601 formatted string (e.g., '2026-05-23T10:30:00Z').
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
