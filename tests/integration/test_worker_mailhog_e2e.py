import os
import time
import uuid

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("LIVE_API_BASE_URL") or not os.getenv("MAILHOG_API_URL"),
    reason="LIVE_API_BASE_URL and MAILHOG_API_URL are required for worker E2E tests",
)


def test_worker_delivers_email_to_mailhog():
    api_base_url = os.environ["LIVE_API_BASE_URL"].rstrip("/")
    mailhog_api_url = os.environ["MAILHOG_API_URL"].rstrip("/")
    recipient_email = f"employee-{uuid.uuid4()}@example.com"
    idem = f"e2e-{uuid.uuid4()}"

    payload = {
        "templateKey": "employee.order.confirmed",
        "recipient": {
            "type": "EMPLOYEE",
            "id": "EMP001",
            "email": recipient_email,
            "name": "王小明",
        },
        "locale": "zh-TW",
        "payload": {
            "orderId": f"ORD-{uuid.uuid4()}",
            "vendorName": "健康便當",
            "pickupDate": "2026-06-03",
            "pickupTime": "12:00-12:30",
            "pickupLocation": "A 廠一樓領餐區",
            "amount": 120,
            "detailUrl": "https://food.example.com/orders/example",
        },
    }

    with httpx.Client(timeout=10) as client:
        response = client.post(
            f"{api_base_url}/internal/v1/notifications/email",
            json=payload,
            headers={
                "Authorization": "Bearer dev-order-token",
                "Idempotency-Key": idem,
                "X-Correlation-Id": f"corr-{uuid.uuid4()}",
            },
        )
        assert response.status_code == 202
        notification_id = response.json()["notificationId"]

        terminal_status = None
        for _ in range(30):
            status_response = client.get(
                f"{api_base_url}/internal/v1/notifications/{notification_id}",
                headers={"Authorization": "Bearer dev-order-token"},
            )
            assert status_response.status_code == 200
            terminal_status = status_response.json()["status"]
            if terminal_status == "SENT":
                break
            time.sleep(1)

        assert terminal_status == "SENT"

        mailhog_response = client.get(f"{mailhog_api_url}/api/v2/messages")
        assert mailhog_response.status_code == 200
        messages = mailhog_response.json()["items"]
        matching_messages = [
            item
            for item in messages
            if any(to["Mailbox"] + "@" + to["Domain"] == recipient_email for to in item["To"])
        ]
        assert len(matching_messages) == 1
