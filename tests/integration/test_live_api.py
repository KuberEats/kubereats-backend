import os
import uuid

import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models.notification import NotificationRequest, NotificationStatus

pytestmark = pytest.mark.skipif(
    not os.getenv("LIVE_API_BASE_URL"),
    reason="LIVE_API_BASE_URL is required for live API integration tests",
)


def api_base_url() -> str:
    return os.environ["LIVE_API_BASE_URL"].rstrip("/")


def headers(token: str = "dev-order-token", idem: str | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": idem or f"idem-{uuid.uuid4()}",
        "X-Correlation-Id": f"corr-{uuid.uuid4()}",
    }


def order_confirmed_payload(amount: int = 120) -> dict:
    return {
        "templateKey": "employee.order.confirmed",
        "recipient": {
            "type": "EMPLOYEE",
            "id": "EMP001",
            "email": "employee@example.com",
            "name": "王小明",
        },
        "locale": "zh-TW",
        "payload": {
            "orderId": f"ORD-{uuid.uuid4()}",
            "vendorName": "健康便當",
            "pickupDate": "2026-06-03",
            "pickupTime": "12:00-12:30",
            "pickupLocation": "A 廠一樓領餐區",
            "amount": amount,
            "detailUrl": "https://food.example.com/orders/example",
        },
    }


def test_live_api_post_get_auth_and_idempotency():
    idem = f"live-{uuid.uuid4()}"
    payload = order_confirmed_payload()

    with httpx.Client(base_url=api_base_url(), timeout=10) as client:
        created = client.post(
            "/internal/v1/notifications/email",
            json=payload,
            headers=headers(idem=idem),
        )
        assert created.status_code == 202
        created_body = created.json()
        assert created_body["duplicate"] is False

        status_response = client.get(
            f"/internal/v1/notifications/{created_body['notificationId']}",
            headers={"Authorization": "Bearer dev-order-token"},
        )
        assert status_response.status_code == 200
        assert status_response.json()["notificationId"] == created_body["notificationId"]

        duplicate = client.post(
            "/internal/v1/notifications/email",
            json=payload,
            headers=headers(idem=idem),
        )
        assert duplicate.status_code == 202
        assert duplicate.json()["duplicate"] is True

        conflict_payload = order_confirmed_payload(amount=999)
        conflict = client.post(
            "/internal/v1/notifications/email",
            json=conflict_payload,
            headers=headers(idem=idem),
        )
        assert conflict.status_code == 409

        unauthorized = client.post(
            "/internal/v1/notifications/email",
            json=payload,
            headers=headers(token="bad-token", idem=f"bad-{uuid.uuid4()}"),
        )
        assert unauthorized.status_code == 401

        forbidden = client.post(
            "/internal/v1/notifications/email",
            json=payload,
            headers=headers(token="dev-merchant-token", idem=f"forbidden-{uuid.uuid4()}"),
        )
        assert forbidden.status_code == 403

    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        count = session.scalar(
            select(func.count()).select_from(NotificationRequest).where(
                NotificationRequest.idempotency_key == idem
            )
        )
        assert count == 1
    finally:
        session.close()
        engine.dispose()


def test_database_unique_constraint_blocks_duplicate_idempotency_key():
    idem = f"constraint-{uuid.uuid4()}"
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        first = NotificationRequest(
            template_key="employee.order.confirmed",
            template_version=1,
            source_service="order-service",
            recipient_type="EMPLOYEE",
            recipient_id="EMP001",
            recipient_email="employee@example.com",
            recipient_name="王小明",
            locale="zh-TW",
            payload={"orderId": "ORD-1"},
            idempotency_key=idem,
            payload_hash="a" * 64,
            correlation_id="corr-1",
            status=NotificationStatus.QUEUED,
        )
        second = NotificationRequest(
            template_key="employee.order.confirmed",
            template_version=1,
            source_service="order-service",
            recipient_type="EMPLOYEE",
            recipient_id="EMP002",
            recipient_email="employee2@example.com",
            recipient_name="王小華",
            locale="zh-TW",
            payload={"orderId": "ORD-2"},
            idempotency_key=idem,
            payload_hash="b" * 64,
            correlation_id="corr-2",
            status=NotificationStatus.QUEUED,
        )
        session.add(first)
        session.commit()
        session.add(second)
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.close()
        engine.dispose()
