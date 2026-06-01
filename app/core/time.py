"""Timezone-aware helpers for defining a business calendar day.

Orders are stored as ``timestamptz`` (UTC). To answer "today's orders" for a
campus in Taiwan we must anchor the day to the business timezone (Asia/Taipei),
not to UTC or the host's local time. We compute an explicit, timezone-aware
half-open interval [start, end) and compare against it — index-friendly and
correct regardless of the database session or process timezone.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def today_in_tz(tz_name: str) -> date:
    """Return the current calendar date in the given timezone."""
    return datetime.now(ZoneInfo(tz_name)).date()


def day_bounds(local_date: date, tz_name: str) -> tuple[datetime, datetime]:
    """Return tz-aware [start, end) bounds for ``local_date`` in ``tz_name``."""
    tz = ZoneInfo(tz_name)
    start = datetime.combine(local_date, time.min, tzinfo=tz)
    end = start + timedelta(days=1)
    return start, end
