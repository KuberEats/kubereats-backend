from app.models.notification import NotificationRequest
from app.services.queue import QueueProducer


def headers(token: str = "dev-order-token", idem: str = "idem-1") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": idem,
        "X-Correlation-Id": "corr-1",
    }


def test_post_notification_creates_record_and_returns_202(
    client, db_session, order_confirmed_payload, monkeypatch
):
    queued = []
    monkeypatch.setattr(
        QueueProducer,
        "enqueue_email",
        lambda _self, notification_id, correlation_id: queued.append(
            {"notificationId": notification_id, "correlationId": correlation_id}
        ),
    )

    response = client.post(
        "/internal/v1/notifications/email",
        json=order_confirmed_payload,
        headers=headers(),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["duplicate"] is False
    assert queued == [{"notificationId": body["notificationId"], "correlationId": "corr-1"}]
    assert db_session.get(NotificationRequest, body["notificationId"]) is not None


def test_duplicate_request_returns_duplicate_true(client, order_confirmed_payload, monkeypatch):
    monkeypatch.setattr(QueueProducer, "enqueue_email", lambda *_args, **_kwargs: None)

    first = client.post(
        "/internal/v1/notifications/email",
        json=order_confirmed_payload,
        headers=headers(),
    )
    second = client.post(
        "/internal/v1/notifications/email",
        json=order_confirmed_payload,
        headers=headers(),
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["duplicate"] is True


def test_invalid_token_returns_401(client, order_confirmed_payload):
    response = client.post(
        "/internal/v1/notifications/email",
        json=order_confirmed_payload,
        headers=headers(token="bad-token"),
    )

    assert response.status_code == 401


def test_unauthorized_template_returns_403(client, order_confirmed_payload, monkeypatch):
    monkeypatch.setattr(QueueProducer, "enqueue_email", lambda *_args, **_kwargs: None)
    response = client.post(
        "/internal/v1/notifications/email",
        json=order_confirmed_payload,
        headers=headers(token="dev-merchant-token"),
    )

    assert response.status_code == 403


def test_status_query_rejects_different_source_service(client, order_confirmed_payload, monkeypatch):
    monkeypatch.setattr(QueueProducer, "enqueue_email", lambda *_args, **_kwargs: None)
    created = client.post(
        "/internal/v1/notifications/email",
        json=order_confirmed_payload,
        headers=headers(),
    )

    response = client.get(
        f"/internal/v1/notifications/{created.json()['notificationId']}",
        headers={"Authorization": "Bearer dev-merchant-token"},
    )

    assert response.status_code == 403
