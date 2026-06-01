from __future__ import annotations

from collections import defaultdict
from math import inf
from threading import Lock

from fastapi import Response

CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
DEFAULT_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    inf,
)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _labels(names: tuple[str, ...], values: tuple[str, ...]) -> str:
    if not names:
        return ""
    pairs = ",".join(f'{name}="{_escape(value)}"' for name, value in zip(names, values))
    return f"{{{pairs}}}"


def _format_number(value: float) -> str:
    if value == inf:
        return "+Inf"
    return f"{value:g}"


class CounterMetric:
    def __init__(self, name: str, description: str, label_names: tuple[str, ...] = ()):
        self.name = name
        self.description = description
        self.label_names = label_names
        self._values: defaultdict[tuple[str, ...], float] = defaultdict(float)
        self._lock = Lock()

    def inc(self, *label_values: str, amount: float = 1.0):
        if len(label_values) != len(self.label_names):
            raise ValueError(f"{self.name} expects {len(self.label_names)} labels")
        with self._lock:
            self._values[tuple(label_values)] += amount

    def collect(self) -> list[str]:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter",
        ]
        with self._lock:
            values = dict(self._values)
        if not values and not self.label_names:
            values[()] = 0.0
        for label_values, value in sorted(values.items()):
            lines.append(
                f"{self.name}{_labels(self.label_names, label_values)} "
                f"{_format_number(value)}"
            )
        return lines


class HistogramMetric:
    def __init__(
        self,
        name: str,
        description: str,
        label_names: tuple[str, ...] = (),
        buckets: tuple[float, ...] = DEFAULT_BUCKETS,
    ):
        self.name = name
        self.description = description
        self.label_names = label_names
        self.buckets = buckets
        self._values = defaultdict(
            lambda: {"buckets": [0] * len(buckets), "sum": 0.0, "count": 0}
        )
        self._lock = Lock()

    def observe(self, *label_values: str, value: float):
        if len(label_values) != len(self.label_names):
            raise ValueError(f"{self.name} expects {len(self.label_names)} labels")
        with self._lock:
            entry = self._values[tuple(label_values)]
            entry["sum"] += value
            entry["count"] += 1
            for index, bucket in enumerate(self.buckets):
                if value <= bucket:
                    entry["buckets"][index] += 1

    def collect(self) -> list[str]:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram",
        ]
        with self._lock:
            values = {
                labels: {
                    "buckets": list(data["buckets"]),
                    "sum": float(data["sum"]),
                    "count": int(data["count"]),
                }
                for labels, data in self._values.items()
            }
        for label_values, data in sorted(values.items()):
            for bucket, count in zip(self.buckets, data["buckets"]):
                labels = self.label_names + ("le",)
                values_with_bucket = label_values + (_format_number(bucket),)
                lines.append(
                    f"{self.name}_bucket{_labels(labels, values_with_bucket)} "
                    f"{count}"
                )
            lines.append(
                f"{self.name}_sum{_labels(self.label_names, label_values)} "
                f"{_format_number(data['sum'])}"
            )
            lines.append(
                f"{self.name}_count{_labels(self.label_names, label_values)} "
                f"{data['count']}"
            )
        return lines


http_requests = CounterMetric(
    "order_scheduler_http_requests_total",
    "Order scheduler HTTP requests by method, route, and status",
    ("method", "path", "status"),
)
http_request_duration = HistogramMetric(
    "order_scheduler_http_request_duration_seconds",
    "Order scheduler HTTP request duration in seconds",
    ("method", "path"),
)
orders_created = CounterMetric(
    "order_scheduler_orders_created_total",
    "Orders created by schedule status",
    ("schedule_status",),
)
order_items_created = CounterMetric(
    "order_scheduler_order_items_created_total",
    "Order item quantities created by schedule status",
    ("schedule_status",),
)
order_status_updates = CounterMetric(
    "order_scheduler_order_status_updates_total",
    "Order status updates by status",
    ("status",),
)
orders_cancelled = CounterMetric(
    "order_scheduler_orders_cancelled_total",
    "Scheduled orders cancelled by status",
    ("status",),
)
order_release_tasks = CounterMetric(
    "order_scheduler_order_release_tasks_total",
    "Scheduled order release task outcomes",
    ("status",),
)
reservation_requests = CounterMetric(
    "order_scheduler_reservation_requests_total",
    "Reservation requests created by status",
    ("status",),
)
reservation_items_requested = CounterMetric(
    "order_scheduler_reservation_items_requested_total",
    "Reservation item quantities requested",
)
reservation_processing = CounterMetric(
    "order_scheduler_reservation_processing_total",
    "Reservation processing outcomes",
    ("status",),
)
reservations_cancelled = CounterMetric(
    "order_scheduler_reservations_cancelled_total",
    "Reservations cancelled by final status",
    ("status",),
)
reservation_capacity_failures = CounterMetric(
    "order_scheduler_reservation_capacity_failures_total",
    "Reservation capacity failures by reason",
    ("reason",),
)


def order_status_label(status: int) -> str:
    return {0: "pending", 1: "completed", 2: "cancelled"}.get(status, "unknown")


def record_http_request(method: str, path: str, status: int, duration_seconds: float):
    http_requests.inc(method, path, str(status))
    http_request_duration.observe(method, path, value=duration_seconds)


def metrics_response() -> Response:
    lines: list[str] = []
    for metric in (
        http_requests,
        http_request_duration,
        orders_created,
        order_items_created,
        order_status_updates,
        orders_cancelled,
        order_release_tasks,
        reservation_requests,
        reservation_items_requested,
        reservation_processing,
        reservations_cancelled,
        reservation_capacity_failures,
    ):
        lines.extend(metric.collect())
    return Response("\n".join(lines) + "\n", media_type=CONTENT_TYPE_LATEST)
