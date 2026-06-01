from prometheus_client import Counter, Histogram

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
