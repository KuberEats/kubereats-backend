from datetime import datetime

from sqlalchemy.orm import Session

from app.models.notification import (
    NotificationDeliveryAttempt,
    NotificationRequest,
    NotificationStatus,
    utc_now,
)


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, notification_id: str) -> NotificationRequest | None:
        return self.db.get(NotificationRequest, notification_id)

    def get_by_idempotency_key(self, key: str) -> NotificationRequest | None:
        return (
            self.db.query(NotificationRequest)
            .filter(NotificationRequest.idempotency_key == key)
            .one_or_none()
        )

    def create(self, notification: NotificationRequest) -> NotificationRequest:
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def set_status(
        self,
        notification: NotificationRequest,
        status: NotificationStatus,
        *,
        provider_message_id: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> NotificationRequest:
        notification.status = status
        if status == NotificationStatus.SENT:
            notification.sent_at = utc_now()
            notification.provider_message_id = provider_message_id
            notification.last_error_code = None
            notification.last_error_message = None
        elif status in {NotificationStatus.FAILED, NotificationStatus.DEAD_LETTER}:
            notification.failed_at = utc_now()
            notification.last_error_code = error_code
            notification.last_error_message = error_message
        elif status == NotificationStatus.RETRYING:
            notification.last_error_code = error_code
            notification.last_error_message = error_message
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def increment_attempt_count(self, notification: NotificationRequest) -> int:
        notification.attempt_count += 1
        self.db.commit()
        self.db.refresh(notification)
        return notification.attempt_count

    def add_attempt(
        self,
        notification_id: str,
        attempt_no: int,
        provider: str,
        status: str,
        started_at: datetime,
        finished_at: datetime | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> NotificationDeliveryAttempt:
        attempt = NotificationDeliveryAttempt(
            notification_id=notification_id,
            attempt_no=attempt_no,
            provider=provider,
            status=status,
            error_code=error_code,
            error_message=error_message,
            started_at=started_at,
            finished_at=finished_at,
        )
        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        return attempt
