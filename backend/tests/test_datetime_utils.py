from datetime import datetime, timezone

from app.ingestion.datetime_utils import normalize_feed_datetime


def test_normalizes_struct_time_to_utc():
    value = (2026, 7, 21, 10, 30, 0, 1, 202, 0)
    assert normalize_feed_datetime(value) == datetime(
        2026, 7, 21, 10, 30, tzinfo=timezone.utc
    )


def test_invalid_datetime_returns_none():
    assert normalize_feed_datetime((2026,)) is None
