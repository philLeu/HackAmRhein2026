"""One human-readable timestamp format across tables, captions and charts."""

from datetime import UTC, date, datetime

TIMESTAMP_FORMAT = "%d.%m.%Y · %H:%M UTC"
DATE_INPUT_FORMAT = "DD.MM.YYYY"


def format_date(value: date) -> str:
    """Use the date portion of the shared timestamp convention for trip days."""
    return value.strftime(TIMESTAMP_FORMAT.split(" · ", 1)[0])


def format_timestamp(value: datetime | None) -> str:
    """Display an aware instant in UTC; preserve unknown as unknown."""
    if value is None:
        return "Unknown"
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Display timestamps must be timezone-aware.")
    return value.astimezone(UTC).strftime(TIMESTAMP_FORMAT)
