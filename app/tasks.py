from time import monotonic

from app.core.logging import get_logger
from app.core.metrics import (
    notification_delivery_duration_seconds,
    notification_failed_total,
    notification_queue_processing_duration_seconds,
    notification_retry_total,
    notification_sent_total,
)
from app.database import SessionLocal
from app.models.notification import NotificationStatus, utc_now
from app.repositories.notification_repository import NotificationRepository
from app.services.email_provider import Email, EmailProviderError, build_email_provider
from app.services.retry_policy import retry_delay_seconds
from app.templates.registry import Recipient, get_template
from app.worker import celery_app

logger = get_logger(__name__)


@celery_app.task(name="notification.send_email", bind=True)
def send_email_notification(self, notification_id: str, correlation_id: str) -> str:
    db = SessionLocal()
    try:
        return process_email_notification(
            db=db,
            notification_id=notification_id,
            correlation_id=correlation_id,
            schedule_retry=lambda delay: self.apply_async(
                kwargs={"notification_id": notification_id, "correlation_id": correlation_id},
                countdown=delay,
            ),
        )
    finally:
        db.close()


def process_email_notification(db, notification_id: str, correlation_id: str, schedule_retry) -> str:
    started = monotonic()
    repository = NotificationRepository(db)
    provider = build_email_provider()
    try:
        notification = repository.get_by_id(notification_id)
        if notification is None:
            logger.warning("notification missing", extra={"notificationId": notification_id})
            return "missing"
        if notification.status == NotificationStatus.SENT:
            return "already_sent"

        repository.set_status(notification, NotificationStatus.PROCESSING)
        attempt_no = repository.increment_attempt_count(notification)
        attempt_started = utc_now()
        template = get_template(notification.template_key)
        rendered = template.render(
            Recipient(
                type=notification.recipient_type,
                id=notification.recipient_id,
                email=notification.recipient_email,
                name=notification.recipient_name,
            ),
            notification.payload,
        )

        delivery_started = monotonic()
        try:
            result = provider.send(
                Email(
                    to=notification.recipient_email,
                    subject=rendered["subject"],
                    html_body=rendered["htmlBody"],
                    text_body=rendered["textBody"],
                )
            )
            notification_delivery_duration_seconds.observe(monotonic() - delivery_started)
            repository.add_attempt(
                notification.id,
                attempt_no,
                result.provider,
                "SENT",
                started_at=attempt_started,
                finished_at=utc_now(),
            )
            repository.set_status(
                notification,
                NotificationStatus.SENT,
                provider_message_id=mask_provider_message_id(result.message_id),
            )
            notification_sent_total.labels(notification.template_key).inc()
            logger.info(
                "notification sent",
                extra={
                    "notificationId": notification.id,
                    "correlationId": correlation_id,
                    "sourceService": notification.source_service,
                    "templateKey": notification.template_key,
                    "status": NotificationStatus.SENT.value,
                    "attemptNo": attempt_no,
                    "provider": result.provider,
                },
            )
            return "sent"
        except EmailProviderError as exc:
            repository.add_attempt(
                notification.id,
                attempt_no,
                provider.provider_name,
                "FAILED",
                started_at=attempt_started,
                finished_at=utc_now(),
                error_code=exc.code,
                error_message=safe_error_message(str(exc)),
            )
            delay = retry_delay_seconds(attempt_no)
            if exc.transient and delay is not None:
                repository.set_status(
                    notification,
                    NotificationStatus.RETRYING,
                    error_code=exc.code,
                    error_message=safe_error_message(str(exc)),
                )
                notification_retry_total.labels(notification.template_key).inc()
                schedule_retry(delay)
                return "retrying"

            terminal_status = (
                NotificationStatus.DEAD_LETTER if exc.transient else NotificationStatus.FAILED
            )
            repository.set_status(
                notification,
                terminal_status,
                error_code=exc.code,
                error_message=safe_error_message(str(exc)),
            )
            notification_failed_total.labels(notification.template_key, exc.code).inc()
            return terminal_status.value.lower()
    finally:
        notification_queue_processing_duration_seconds.observe(monotonic() - started)


def mask_provider_message_id(message_id: str) -> str:
    if len(message_id) <= 8:
        return message_id
    return f"{message_id[:4]}...{message_id[-4:]}"


def safe_error_message(message: str) -> str:
    return message[:300]
