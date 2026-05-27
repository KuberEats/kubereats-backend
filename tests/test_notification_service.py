import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.notification import NotificationStatus
from app.repositories.notification_repository import NotificationRepository
from app.schemas import CreateEmailNotificationRequest
from app.services.notification_service import NotificationApplicationService


class FakeQueue:
    def __init__(self):
        self.messages = []

    def enqueue_email(self, notification_id: str, correlation_id: str) -> None:
        self.messages.append({"notificationId": notification_id, "correlationId": correlation_id})


def test_idempotency_same_payload_returns_duplicate(db_session, order_confirmed_payload):
    queue = FakeQueue()
    service = NotificationApplicationService(db_session, queue=queue)
    request = CreateEmailNotificationRequest.model_validate(order_confirmed_payload)

    first = service.create_email_notification(
        request,
        source_service="order-service",
        idempotency_key="idem-1",
        correlation_id="corr-1",
    )
    second = service.create_email_notification(
        request,
        source_service="order-service",
        idempotency_key="idem-1",
        correlation_id="corr-1",
    )

    assert first.notification.id == second.notification.id
    assert second.duplicate is True
    assert len(queue.messages) == 1


def test_idempotency_same_key_different_payload_conflicts(db_session, order_confirmed_payload):
    service = NotificationApplicationService(db_session, queue=FakeQueue())
    request = CreateEmailNotificationRequest.model_validate(order_confirmed_payload)
    service.create_email_notification(
        request,
        source_service="order-service",
        idempotency_key="idem-1",
        correlation_id="corr-1",
    )

    changed = dict(order_confirmed_payload)
    changed["payload"] = dict(order_confirmed_payload["payload"])
    changed["payload"]["amount"] = 999

    with pytest.raises(HTTPException) as exc:
        service.create_email_notification(
            CreateEmailNotificationRequest.model_validate(changed),
            source_service="order-service",
            idempotency_key="idem-1",
            correlation_id="corr-1",
        )

    assert exc.value.status_code == 409


def test_merchant_cannot_use_employee_template(db_session, order_confirmed_payload):
    service = NotificationApplicationService(db_session, queue=FakeQueue())

    with pytest.raises(HTTPException) as exc:
        service.create_email_notification(
            CreateEmailNotificationRequest.model_validate(order_confirmed_payload),
            source_service="merchant-service",
            idempotency_key="idem-1",
            correlation_id="corr-1",
        )

    assert exc.value.status_code == 403


def test_create_sets_queued_status_and_enqueues(db_session, order_confirmed_payload):
    queue = FakeQueue()
    service = NotificationApplicationService(db_session, queue=queue)

    result = service.create_email_notification(
        CreateEmailNotificationRequest.model_validate(order_confirmed_payload),
        source_service="order-service",
        idempotency_key="idem-1",
        correlation_id="corr-1",
    )

    assert result.notification.status == NotificationStatus.QUEUED
    assert queue.messages == [
        {"notificationId": result.notification.id, "correlationId": "corr-1"},
    ]


def test_database_unique_constraint_blocks_duplicate_idempotency_key(
    db_session, order_confirmed_payload
):
    service = NotificationApplicationService(db_session, queue=FakeQueue())
    request = CreateEmailNotificationRequest.model_validate(order_confirmed_payload)
    first = service.create_email_notification(
        request,
        source_service="order-service",
        idempotency_key="idem-unique",
        correlation_id="corr-1",
    )
    duplicate = type(first.notification)(
        template_key=first.notification.template_key,
        template_version=first.notification.template_version,
        source_service=first.notification.source_service,
        recipient_type=first.notification.recipient_type,
        recipient_id="EMP002",
        recipient_email="employee2@example.com",
        recipient_name="王小華",
        locale=first.notification.locale,
        payload=first.notification.payload,
        idempotency_key=first.notification.idempotency_key,
        payload_hash="b" * 64,
        correlation_id="corr-2",
        status=NotificationStatus.QUEUED,
    )

    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert NotificationRepository(db_session).get_by_id(first.notification.id) is not None
