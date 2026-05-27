from app.models.notification import NotificationStatus
from app.repositories.notification_repository import NotificationRepository
from app.services.email_provider import InMemoryEmailProvider
from app.services.notification_service import NotificationApplicationService
from app.schemas import CreateEmailNotificationRequest
from app.tasks import process_email_notification


class FakeQueue:
    def enqueue_email(self, notification_id: str, correlation_id: str) -> None:
        return None


def create_notification(db_session, order_confirmed_payload):
    result = NotificationApplicationService(db_session, queue=FakeQueue()).create_email_notification(
        CreateEmailNotificationRequest.model_validate(order_confirmed_payload),
        source_service="order-service",
        idempotency_key="idem-worker",
        correlation_id="corr-worker",
    )
    return result.notification.id


def test_worker_sends_email_and_updates_sent(db_session, order_confirmed_payload, monkeypatch):
    provider = InMemoryEmailProvider()
    monkeypatch.setattr("app.tasks.build_email_provider", lambda: provider)

    notification_id = create_notification(db_session, order_confirmed_payload)

    result = process_email_notification(
        db_session,
        notification_id=notification_id,
        correlation_id="corr-worker",
        schedule_retry=lambda _delay: None,
    )

    db_session.expire_all()
    notification = NotificationRepository(db_session).get_by_id(notification_id)
    assert result == "sent"
    assert notification.status == NotificationStatus.SENT
    assert notification.attempt_count == 1
    assert len(provider.sent) == 1


def test_worker_transient_failure_sets_retrying(db_session, order_confirmed_payload, monkeypatch):
    provider = InMemoryEmailProvider(fail_times=1, transient=True)
    scheduled = []
    monkeypatch.setattr("app.tasks.build_email_provider", lambda: provider)

    notification_id = create_notification(db_session, order_confirmed_payload)

    result = process_email_notification(
        db_session,
        notification_id=notification_id,
        correlation_id="corr-worker",
        schedule_retry=lambda delay: scheduled.append({"countdown": delay}),
    )

    db_session.expire_all()
    notification = NotificationRepository(db_session).get_by_id(notification_id)
    assert result == "retrying"
    assert notification.status == NotificationStatus.RETRYING
    assert scheduled[0]["countdown"] == 60


def test_worker_exceeds_retries_goes_dead_letter(db_session, order_confirmed_payload, monkeypatch):
    provider = InMemoryEmailProvider(fail_times=1, transient=True)
    monkeypatch.setattr("app.tasks.build_email_provider", lambda: provider)

    notification_id = create_notification(db_session, order_confirmed_payload)
    notification = NotificationRepository(db_session).get_by_id(notification_id)
    notification.attempt_count = 3
    db_session.commit()

    result = process_email_notification(
        db_session,
        notification_id=notification_id,
        correlation_id="corr-worker",
        schedule_retry=lambda _delay: None,
    )

    db_session.expire_all()
    notification = NotificationRepository(db_session).get_by_id(notification_id)
    assert result == "dead_letter"
    assert notification.status == NotificationStatus.DEAD_LETTER
