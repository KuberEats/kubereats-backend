from prometheus_client import Counter, Histogram
from prometheus_client import REGISTRY as _REGISTRY


def _counter(name: str, doc: str, labelnames: list[str] | None = None):
    """Create a Counter, or return existing if already registered.

    The fallback handles test fixtures that delete and re-import app
    modules without resetting the prometheus global registry.
    """
    try:
        return Counter(name, doc, labelnames or [])
    except ValueError:
        return _REGISTRY._names_to_collectors[name]


def _histogram(name: str, doc: str, labelnames: list[str] | None = None):
    """Create a Histogram, or return existing if already registered."""
    try:
        return Histogram(name, doc, labelnames or [])
    except ValueError:
        return _REGISTRY._names_to_collectors[name]


auth_register_total = _counter(
    "auth_register_total",
    "User registrations",
)
auth_login_total = _counter(
    "auth_login_total",
    "Login attempts",
    ["outcome"],  # success | failure
)
auth_token_refresh_total = _counter(
    "auth_token_refresh_total",
    "Token refresh attempts",
    ["outcome"],  # success | failure
)
auth_request_duration_seconds = _histogram(
    "auth_request_duration_seconds",
    "Auth endpoint request duration",
    ["endpoint"],
)
