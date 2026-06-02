from prometheus_client import Counter, Gauge, Histogram

merchant_apply_total = Counter(
    "merchant_apply_total",
    "Merchant applications submitted",
)
merchant_menu_created_total = Counter(
    "merchant_menu_created_total",
    "Menu items created",
)
merchant_menu_deleted_total = Counter(
    "merchant_menu_deleted_total",
    "Menu items deleted",
)
merchant_orders_confirmed_total = Counter(
    "merchant_orders_confirmed_total",
    "Today's orders confirmed by merchant",
)
merchant_request_duration_seconds = Histogram(
    "merchant_request_duration_seconds",
    "Merchant endpoint request duration",
    ["endpoint"],
)
kubereats_merchant_available = Gauge(
    "kubereats_merchant_available",
    "Whether a merchant is currently available for ordering.",
    ["campus", "merchant_id"],
)
kubereats_menu_capacity_remaining = Gauge(
    "kubereats_menu_capacity_remaining",
    "Remaining merchant menu capacity for the current service day.",
    ["campus", "merchant_id", "pickup_slot"],
)
