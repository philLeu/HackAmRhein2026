"""One human-readable timestamp format across tables, captions and charts."""

from datetime import UTC, datetime

TIMESTAMP_FORMAT = "%d.%m.%Y · %H:%M UTC"
DATE_INPUT_FORMAT = "DD.MM.YYYY"


def format_timestamp(value: datetime | None) -> str:
    """Display an aware instant in UTC; preserve unknown as unknown."""
    if value is None:
        return "Unknown"
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Display timestamps must be timezone-aware.")
    return value.astimezone(UTC).strftime(TIMESTAMP_FORMAT)
