from prometheus_client import Counter, Histogram

auth_register_total = Counter(
    "auth_register_total",
    "User registrations",
)
auth_login_total = Counter(
    "auth_login_total",
    "Login attempts",
    ["outcome"],  # success | failure
)
auth_token_refresh_total = Counter(
    "auth_token_refresh_total",
    "Token refresh attempts",
    ["outcome"],  # success | failure
)
auth_request_duration_seconds = Histogram(
    "auth_request_duration_seconds",
    "Auth endpoint request duration",
    ["endpoint"],
)
