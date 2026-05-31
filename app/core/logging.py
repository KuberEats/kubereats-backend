"""
Structured JSON logging for Google Cloud Logging.

GCP expects the field to be named `severity` (not `level`), and automatically
maps it to the correct log severity in Cloud Console.  Call setup_logging()
once at application startup.

Usage:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("User registered", extra={"user_id": 42})
"""

import json
import logging
import sys
from datetime import datetime, timezone

from app.core.config import get_settings


class _GCPFormatter(logging.Formatter):
    """Emit one JSON line per log record, compatible with GCP Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "service": get_settings().service_name,
            "logger": record.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        # Allow callers to attach extra structured fields via extra={...}
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                entry[key] = value
        return json.dumps(entry, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger to emit structured JSON to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_GCPFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Reduce noise from libraries that log at INFO by default
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
