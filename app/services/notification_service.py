from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.metrics import notification_requests_total
from app.models.notification import NotificationRequest, NotificationStatus
from app.repositories.notification_repository import NotificationRepository
from app.schemas import CreateEmailNotificationRequest
from app.services.hash import stable_payload_hash
from app.services.queue import QueueProducer
from app.templates.registry import TemplateValidationError, get_template

logger = get_logger(__name__)


@dataclass(frozen=True)
class CreateNotificationResult:
    notification: NotificationRequest
    duplicate: bool


class NotificationApplicationService:
    def __init__(self, db: Session, queue: QueueProducer | None = None):
        self.repository = NotificationRepository(db)
        self.queue = queue or QueueProducer()

    def create_email_notification(
        self,
        request: CreateEmailNotificationRequest,
        *,
        source_service: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> CreateNotificationResult:
        try:
            template = get_template(request.templateKey)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown templateKey") from exc

        if source_service not in template.allowed_source_services:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Template not allowed")
        if request.recipient.type not in template.allowed_recipient_types:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Recipient type not allowed")

        try:
            template.validate_payload(request.payload)
        except TemplateValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        payload_hash = stable_payload_hash(
            {
                "templateKey": request.templateKey,
                "recipient": request.recipient.model_dump(),
                "locale": request.locale,
                "payload": request.payload,
            }
        )
        existing = self.repository.get_by_idempotency_key(idempotency_key)
        if existing:
            if existing.payload_hash != payload_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key reused with different payload",
                )
            return CreateNotificationResult(notification=existing, duplicate=True)

        notification = NotificationRequest(
            template_key=template.key,
            template_version=template.version,
            source_service=source_service,
            recipient_type=request.recipient.type,
            recipient_id=request.recipient.id,
            recipient_email=request.recipient.email,
            recipient_name=request.recipient.name,
            locale=request.locale,
            payload=request.payload,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            correlation_id=correlation_id,
            status=NotificationStatus.QUEUED,
        )
        created = self.repository.create(notification)
        self.queue.enqueue_email(created.id, correlation_id)
        notification_requests_total.labels(template.key, source_service).inc()
        logger.info(
            "notification queued",
            extra={
                "notificationId": created.id,
                "correlationId": correlation_id,
                "sourceService": source_service,
                "templateKey": template.key,
                "status": created.status.value,
            },
        )
        return CreateNotificationResult(notification=created, duplicate=False)

    def get_notification(self, notification_id: str, source_service: str) -> NotificationRequest:
        notification = self.repository.get_by_id(notification_id)
        if notification is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        if source_service != "admin-service" and notification.source_service != source_service:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Notification not allowed")
        return notification
