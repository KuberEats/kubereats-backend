import logging
import signal
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread

from app.config import get_settings
from app.database import SessionLocal
from app.repo.reservation_repo import ReservationRepository
from app.services.reservation_service import ReservationService
from app.services.reservation_worker import ReservationDbPollingWorker


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

_shutdown = False


class _Metrics:
    def __init__(self):
        self._lock = Lock()
        self.poll_total = 0
        self.processed_total = 0
        self.failed_total = 0
        self.last_poll_timestamp = 0.0

    def record_poll(self, result: dict):
        with self._lock:
            self.poll_total += 1
            self.processed_total += result["processed"]
            self.failed_total += result["failed"]
            self.last_poll_timestamp = time.time()

    def render(self):
        with self._lock:
            lines = [
                "# HELP order_consumer_up Whether the order consumer process is running.",
                "# TYPE order_consumer_up gauge",
                "order_consumer_up 1",
                "# HELP order_consumer_poll_total Total reservation polling cycles.",
                "# TYPE order_consumer_poll_total counter",
                f"order_consumer_poll_total {self.poll_total}",
                "# HELP order_consumer_reservation_processed_total Total reservations processed by the worker.",
                "# TYPE order_consumer_reservation_processed_total counter",
                f"order_consumer_reservation_processed_total {self.processed_total}",
                "# HELP order_consumer_reservation_failed_total Total reservation processing failures.",
                "# TYPE order_consumer_reservation_failed_total counter",
                f"order_consumer_reservation_failed_total {self.failed_total}",
                "# HELP order_consumer_last_poll_timestamp_seconds Unix timestamp of the last polling cycle.",
                "# TYPE order_consumer_last_poll_timestamp_seconds gauge",
                f"order_consumer_last_poll_timestamp_seconds {self.last_poll_timestamp}",
            ]
        return "\n".join(lines) + "\n"


metrics = _Metrics()


def _handle_shutdown(signum, frame):
    global _shutdown
    _shutdown = True
    logger.info("order_consumer_shutdown_requested", extra={"signal": signum})


class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return

        body = metrics.render().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        logger.debug("metrics_request", extra={"message": format % args})


def _start_metrics_server():
    settings = get_settings()
    server = ThreadingHTTPServer(
        (settings.order_consumer_metrics_address, settings.order_consumer_metrics_port),
        _MetricsHandler,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(
        "order_consumer_metrics_started",
        extra={
            "address": settings.order_consumer_metrics_address,
            "port": settings.order_consumer_metrics_port,
        },
    )
    return server


def _poll_once():
    db = SessionLocal()
    try:
        repo = ReservationRepository(db)
        service = ReservationService(repo)
        worker = ReservationDbPollingWorker(repo, service)
        return worker.poll_once()
    finally:
        db.close()


def main():
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    settings = get_settings()
    logger.info(
        "order_consumer_started",
        extra={
            "poll_interval_seconds": settings.order_consumer_poll_interval_seconds,
            "batch_size": settings.reservation_db_polling_batch_size,
        },
    )
    metrics_server = _start_metrics_server()

    while not _shutdown:
        try:
            result = _poll_once()
            metrics.record_poll(result)
            if result["processed"] or result["failed"]:
                logger.info("reservation_poll_completed", extra=result)
        except Exception:
            logger.exception("reservation_poll_failed")

        if not _shutdown:
            time.sleep(settings.order_consumer_poll_interval_seconds)

    metrics_server.shutdown()
    logger.info("order_consumer_stopped")


if __name__ == "__main__":
    main()
