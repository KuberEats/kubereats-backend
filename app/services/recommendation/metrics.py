from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import UTC, datetime
from threading import Lock


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

    def record_fallback(self, operation: str):
        with self._lock:
            self._openrouter["fallback_count"] += 1
            self._openrouter["by_operation"][operation]["fallback_count"] += 1

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

    def _rate(self, count: int, total: int):
        if total == 0:
            return None

        return round(count / total, 4)

    def _average_latency_ms(self, total_latency_seconds: float, total_requests: int):
        if total_requests == 0:
            return None

        return round(total_latency_seconds / total_requests * 1000, 2)


recommendation_metrics = RecommendationMetrics()
