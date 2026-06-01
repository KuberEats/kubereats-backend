from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.time import day_bounds, today_in_tz


def test_day_bounds_is_half_open_local_midnight():
    start, end = day_bounds(date(2026, 6, 2), "Asia/Taipei")
    tz = ZoneInfo("Asia/Taipei")
    assert start == datetime(2026, 6, 2, 0, 0, tzinfo=tz)
    assert end == datetime(2026, 6, 3, 0, 0, tzinfo=tz)


def test_day_bounds_maps_to_expected_utc_window():
    # Taipei is UTC+8, so a Taipei day starts at 16:00 UTC the previous day.
    start, end = day_bounds(date(2026, 6, 2), "Asia/Taipei")
    assert start.astimezone(ZoneInfo("UTC")) == datetime(
        2026, 6, 1, 16, 0, tzinfo=ZoneInfo("UTC")
    )
    assert end.astimezone(ZoneInfo("UTC")) == datetime(
        2026, 6, 2, 16, 0, tzinfo=ZoneInfo("UTC")
    )


def test_today_in_tz_returns_a_date():
    assert isinstance(today_in_tz("Asia/Taipei"), date)
