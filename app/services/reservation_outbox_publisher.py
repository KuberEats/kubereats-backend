from datetime import datetime, timedelta, timezone
import logging

from app.config import Settings, get_settings
from app.queues.reservation import ReservationEventPublisher
from app.repo.reservation_repo import ReservationRepository

logger = logging.getLogger(__name__)


class ReservationOutboxPublisher:
    def __init__(
        self,
        reservation_repo: ReservationRepository,
        publisher: ReservationEventPublisher,
        settings: Settings | None = None,
    ):
        self.reservation_repo = reservation_repo
        self.publisher = publisher
        self.settings = settings or get_settings()

    def publish_once(self, limit: int = 100):
        events = self.reservation_repo.list_publishable_outbox_events(limit=limit)
        results = {"published": 0, "failed": 0, "dead_lettered": 0}

        for event in events:
            try:
                if event.event_type == "ReservationRequested":
                    self.publisher.publish_reservation_requested(
                        payload=event.payload,
                        ordering_key=event.ordering_key,
                    )
                event.status = "PUBLISHED"
                event.published_at = datetime.now(timezone.utc)
                event.last_error = None
                event.next_retry_at = None
                self.reservation_repo.commit()
                results["published"] += 1
                logger.info(
                    "reservation_outbox_publish_success",
                    extra={
                        "event_id": event.id,
                        "aggregate_id": event.aggregate_id,
                        "ordering_key": event.ordering_key,
                    },
                )
            except Exception as error:
                event.retry_count += 1
                event.last_error = str(error)[:1000]
                if event.retry_count >= self.settings.reservation_outbox_max_retries:
                    event.status = "DEAD_LETTER"
                    event.next_retry_at = None
                    results["dead_lettered"] += 1
                else:
                    event.status = "FAILED_RETRYABLE"
                    event.next_retry_at = datetime.now(timezone.utc) + timedelta(
                        seconds=min(3600, 2 ** min(event.retry_count, 10))
                    )
                    results["failed"] += 1
                self.reservation_repo.commit()
                logger.info(
                    "reservation_outbox_publish_failed",
                    extra={
                        "event_id": event.id,
                        "aggregate_id": event.aggregate_id,
                        "retry_count": event.retry_count,
                        "status": event.status,
                        "error": event.last_error,
                    },
                )

        return results
