from prometheus_client import Counter, Histogram

notification_requests_total = Counter(
    "notification_requests_total",
    "Notification requests accepted",
    ["template_key", "source_service"],
)
notification_sent_total = Counter(
    "notification_sent_total",
    "Notifications sent",
    ["template_key"],
)
notification_failed_total = Counter(
    "notification_failed_total",
    "Notifications failed",
    ["template_key", "reason"],
)
notification_retry_total = Counter(
    "notification_retry_total",
    "Notification retries scheduled",
    ["template_key"],
)
notification_queue_processing_duration_seconds = Histogram(
    "notification_queue_processing_duration_seconds",
    "Queue message processing duration",
)
notification_delivery_duration_seconds = Histogram(
    "notification_delivery_duration_seconds",
    "Email provider delivery duration",
)
