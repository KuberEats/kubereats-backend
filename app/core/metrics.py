from prometheus_client import Counter, Histogram

committee_merchant_approved_total = Counter(
    "committee_merchant_approved_total",
    "Merchant applications approved",
)
committee_merchant_rejected_total = Counter(
    "committee_merchant_rejected_total",
    "Merchant applications rejected",
)
committee_request_duration_seconds = Histogram(
    "committee_request_duration_seconds",
    "Committee endpoint request duration",
    ["endpoint"],
)
