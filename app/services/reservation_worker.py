from datetime import datetime, timedelta, timezone
import logging

from app.config import Settings, get_settings
from app.repo.reservation_repo import ReservationRepository
from app.services.reservation_service import ReservationService


logger = logging.getLogger(__name__)


class ReservationDbPollingWorker:
    def __init__(
        self,
        reservation_repo: ReservationRepository,
        reservation_service: ReservationService,
        settings: Settings | None = None,
    ):
        self.reservation_repo = reservation_repo
        self.reservation_service = reservation_service
        self.settings = settings or get_settings()

    def poll_once(self, limit: int | None = None):
        limit = limit or self.settings.reservation_db_polling_batch_size
        lease_until = datetime.now(timezone.utc) + timedelta(
            seconds=self.settings.reservation_processing_lease_seconds
        )

        try:
            reservation_ids = self.reservation_repo.claim_pending_reservation_ids(
                limit=limit,
                lease_until=lease_until,
            )
            self.reservation_repo.commit()
        except Exception:
            self.reservation_repo.rollback()
            raise

        results = {"processed": 0, "failed": 0}
        for reservation_id in reservation_ids:
            try:
                self.reservation_service.process_reservation_by_id(reservation_id)
                results["processed"] += 1
            except Exception:
                logger.exception(
                    "reservation_processing_failed",
                    extra={"reservation_id": reservation_id},
                )
                results["failed"] += 1

        return results
