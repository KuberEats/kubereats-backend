from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, status

from app.core.config import get_settings

WINDOW_SECONDS = 60
_requests: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(source_service: str) -> None:
    now = monotonic()
    bucket = _requests[source_service]
    while bucket and now - bucket[0] > WINDOW_SECONDS:
        bucket.popleft()

    if len(bucket) >= get_settings().rate_limit_per_minute:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    bucket.append(now)
