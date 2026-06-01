from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import UTC, datetime
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


api_requests = CounterMetric(
    "recommendation_requests_total",
    "Recommendation API requests by endpoint, method, and status",
    ("endpoint", "method", "status"),
)
api_request_duration = HistogramMetric(
    "recommendation_request_duration_seconds",
    "Recommendation API request duration in seconds",
    ("endpoint", "method"),
)
prompt_requests = CounterMetric(
    "recommendation_prompt_requests_total",
    "Recommendation prompt requests by kind and status",
    ("kind", "status"),
)
results_returned = CounterMetric(
    "recommendation_results_returned_total",
    "Recommendation results returned by kind and source",
    ("kind", "source"),
)
openrouter_calls = CounterMetric(
    "recommendation_openrouter_calls_total",
    "OpenRouter calls by operation and status",
    ("operation", "status"),
)
openrouter_fallbacks = CounterMetric(
    "recommendation_openrouter_fallbacks_total",
    "OpenRouter fallback usage by operation",
    ("operation",),
)
openrouter_tokens = CounterMetric(
    "recommendation_openrouter_tokens_total",
    "OpenRouter token and search unit usage",
    ("operation", "type"),
)


class RecommendationMetrics:
    def __init__(self):
        self._lock = Lock()
        self._started_at = datetime.now(UTC)
        self._api = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_latency_seconds": 0.0,
            "by_endpoint": defaultdict(
                lambda: {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "total_latency_seconds": 0.0,
                }
            ),
        }
        self._openrouter = {
            "successful_calls": 0,
            "failed_calls": 0,
            "fallback_count": 0,
            "by_operation": defaultdict(
                lambda: {
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "fallback_count": 0,
                }
            ),
        }
        self._openrouter_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "rerank_search_units": 0,
            "last_usage": None,
        }

    def record_api_request(
        self,
        endpoint: str,
        method: str,
        status: str,
        latency_seconds: float,
    ):
        key = f"{method} {endpoint}"
        is_success = status == "success"

        with self._lock:
            self._api["total_requests"] += 1
            self._api["total_latency_seconds"] += latency_seconds

            endpoint_metrics = self._api["by_endpoint"][key]
            endpoint_metrics["total_requests"] += 1
            endpoint_metrics["total_latency_seconds"] += latency_seconds

            if is_success:
                self._api["successful_requests"] += 1
                endpoint_metrics["successful_requests"] += 1
            else:
                self._api["failed_requests"] += 1
                endpoint_metrics["failed_requests"] += 1

        api_requests.inc(endpoint, method, status)
        api_request_duration.observe(endpoint, method, value=latency_seconds)

    def record_openrouter_call(
        self,
        operation: str,
        status: str,
        usage: dict | None = None,
    ):
        is_success = status == "success"

        with self._lock:
            operation_metrics = self._openrouter["by_operation"][operation]

            if is_success:
                self._openrouter["successful_calls"] += 1
                operation_metrics["successful_calls"] += 1
                self._record_openrouter_usage(operation, usage)
            else:
                self._openrouter["failed_calls"] += 1
                operation_metrics["failed_calls"] += 1

        openrouter_calls.inc(operation, status)

    def record_fallback(self, operation: str):
        with self._lock:
            self._openrouter["fallback_count"] += 1
            self._openrouter["by_operation"][operation]["fallback_count"] += 1
        openrouter_fallbacks.inc(operation)

    def record_prompt_request(self, kind: str, status: str):
        prompt_requests.inc(kind, status)

    def record_results(self, kind: str, source: str, count: int):
        results_returned.inc(kind, source, amount=count)

    def snapshot(self):
        with self._lock:
            api = deepcopy(dict(self._api))
            api["by_endpoint"] = {
                endpoint: dict(metrics)
                for endpoint, metrics in self._api["by_endpoint"].items()
            }
            openrouter = deepcopy(dict(self._openrouter))
            openrouter["by_operation"] = {
                operation: dict(metrics)
                for operation, metrics in self._openrouter["by_operation"].items()
            }
            usage = deepcopy(self._openrouter_usage)

        total_requests = api["total_requests"]
        openrouter_total_calls = (
            openrouter["successful_calls"] + openrouter["failed_calls"]
        )

        return {
            "service": "recommendation",
            "status": "ok",
            "startedAt": self._started_at.isoformat(),
            "timestamp": datetime.now(UTC).isoformat(),
            "api": {
                "totalRequests": total_requests,
                "successfulRequests": api["successful_requests"],
                "failedRequests": api["failed_requests"],
                "successRate": self._rate(api["successful_requests"], total_requests),
                "errorRate": self._rate(api["failed_requests"], total_requests),
                "averageLatencyMs": self._average_latency_ms(
                    api["total_latency_seconds"],
                    total_requests,
                ),
                "byEndpoint": {
                    endpoint: {
                        "totalRequests": metrics["total_requests"],
                        "successfulRequests": metrics["successful_requests"],
                        "failedRequests": metrics["failed_requests"],
                        "successRate": self._rate(
                            metrics["successful_requests"],
                            metrics["total_requests"],
                        ),
                        "errorRate": self._rate(
                            metrics["failed_requests"],
                            metrics["total_requests"],
                        ),
                        "averageLatencyMs": self._average_latency_ms(
                            metrics["total_latency_seconds"],
                            metrics["total_requests"],
                        ),
                    }
                    for endpoint, metrics in api["by_endpoint"].items()
                },
            },
            "openRouter": {
                "totalCalls": openrouter_total_calls,
                "successfulCalls": openrouter["successful_calls"],
                "failedCalls": openrouter["failed_calls"],
                "successRate": self._rate(
                    openrouter["successful_calls"],
                    openrouter_total_calls,
                ),
                "failureRate": self._rate(
                    openrouter["failed_calls"],
                    openrouter_total_calls,
                ),
                "fallbackCount": openrouter["fallback_count"],
                "byOperation": {
                    operation: {
                        "totalCalls": (
                            metrics["successful_calls"] + metrics["failed_calls"]
                        ),
                        "successfulCalls": metrics["successful_calls"],
                        "failedCalls": metrics["failed_calls"],
                        "successRate": self._rate(
                            metrics["successful_calls"],
                            metrics["successful_calls"] + metrics["failed_calls"],
                        ),
                        "failureRate": self._rate(
                            metrics["failed_calls"],
                            metrics["successful_calls"] + metrics["failed_calls"],
                        ),
                        "fallbackCount": metrics["fallback_count"],
                    }
                    for operation, metrics in openrouter["by_operation"].items()
                },
            },
            "openRouterUsage": {
                "promptTokens": usage["prompt_tokens"],
                "completionTokens": usage["completion_tokens"],
                "totalTokens": usage["total_tokens"],
                "rerankSearchUnits": usage["rerank_search_units"],
                "lastUsage": usage["last_usage"],
            },
        }

    def _record_openrouter_usage(self, operation: str, usage: dict | None):
        if not usage:
            return

        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or 0)
        search_units = int(usage.get("search_units") or 0)

        self._openrouter_usage["prompt_tokens"] += prompt_tokens
        self._openrouter_usage["completion_tokens"] += completion_tokens
        self._openrouter_usage["total_tokens"] += total_tokens
        self._openrouter_usage["rerank_search_units"] += search_units
        self._openrouter_usage["last_usage"] = {
            "operation": operation,
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "totalTokens": total_tokens,
            "rerankSearchUnits": search_units,
            "raw": usage,
        }
        openrouter_tokens.inc(operation, "prompt", amount=prompt_tokens)
        openrouter_tokens.inc(operation, "completion", amount=completion_tokens)
        openrouter_tokens.inc(operation, "total", amount=total_tokens)
        openrouter_tokens.inc(operation, "rerank_search_units", amount=search_units)

    def _rate(self, count: int, total: int):
        if total == 0:
            return None

        return round(count / total, 4)

    def _average_latency_ms(self, total_latency_seconds: float, total_requests: int):
        if total_requests == 0:
            return None

        return round(total_latency_seconds / total_requests * 1000, 2)


recommendation_metrics = RecommendationMetrics()


def metrics_response() -> Response:
    lines: list[str] = []
    for metric in (
        api_requests,
        api_request_duration,
        prompt_requests,
        results_returned,
        openrouter_calls,
        openrouter_fallbacks,
        openrouter_tokens,
    ):
        lines.extend(metric.collect())
    return Response("\n".join(lines) + "\n", media_type=CONTENT_TYPE_LATEST)
