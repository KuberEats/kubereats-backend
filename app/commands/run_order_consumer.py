import logging
import signal
import time

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


def _handle_shutdown(signum, frame):
    global _shutdown
    _shutdown = True
    logger.info("order_consumer_shutdown_requested", extra={"signal": signum})


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

    while not _shutdown:
        try:
            result = _poll_once()
            if result["processed"] or result["failed"]:
                logger.info("reservation_poll_completed", extra=result)
        except Exception:
            logger.exception("reservation_poll_failed")

        if not _shutdown:
            time.sleep(settings.order_consumer_poll_interval_seconds)

    logger.info("order_consumer_stopped")


if __name__ == "__main__":
    main()
