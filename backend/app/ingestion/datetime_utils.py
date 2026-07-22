import calendar
from datetime import datetime, timezone
from time import struct_time
from typing import Sequence


def normalize_feed_datetime(
    value: struct_time | Sequence[int] | None,
) -> datetime | None:
    """Convert feedparser date tuples to timezone-aware UTC datetimes."""
    if value is None:
        return None

    try:
        timestamp = calendar.timegm(tuple(value))
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None
