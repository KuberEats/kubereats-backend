from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.rate_limit import check_rate_limit
from app.core.security import ServicePrincipal, authenticate_service
from app.database import get_db
from app.schemas import (
    CreateEmailNotificationRequest,
    CreateEmailNotificationResponse,
    NotificationStatusResponse,
)
from app.services.notification_service import NotificationApplicationService

router = APIRouter(prefix="/internal/v1/notifications", tags=["notifications"])


@router.post("/email", response_model=CreateEmailNotificationResponse, status_code=202)
def create_email_notification(
    request: CreateEmailNotificationRequest,
    principal: ServicePrincipal = Depends(authenticate_service),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-Id"),
):
    if not idempotency_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Idempotency-Key")
    if not correlation_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing X-Correlation-Id")

    check_rate_limit(principal.source_service)
    result = NotificationApplicationService(db).create_email_notification(
        request,
        source_service=principal.source_service,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )
    return CreateEmailNotificationResponse(
        notificationId=result.notification.id,
        status=result.notification.status.value,
        duplicate=result.duplicate,
    )


@router.get("/{notification_id}", response_model=NotificationStatusResponse)
def get_notification_status(
    notification_id: str,
    principal: ServicePrincipal = Depends(authenticate_service),
    db: Session = Depends(get_db),
):
    notification = NotificationApplicationService(db).get_notification(
        notification_id, principal.source_service
    )
    return NotificationStatusResponse(
        notificationId=notification.id,
        templateKey=notification.template_key,
        templateVersion=notification.template_version,
        sourceService=notification.source_service,
        recipientType=notification.recipient_type,
        status=notification.status,
        attemptCount=notification.attempt_count,
        providerMessageId=notification.provider_message_id,
        createdAt=notification.created_at,
        sentAt=notification.sent_at,
    )
