from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.models.kubereats import Menu, MerchantInfo, UserInfo
from app.queues.fake import FakeTaskQueue
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.order_service import OrderService
from app.services.outbox_dispatcher import OutboxDispatcher


class FakeMenuRepository:
    def __init__(self, menus):
        self.menus = menus

    def get_by_id(self, menu_id):
        return self.menus.get(menu_id)


class FakeOrderRepository:
    def __init__(self):
        self.users = {1: UserInfo(id=1, username="buyer", role="staff")}
        self.orders = {}
        self.order_items = []
        self.finance_records = []
        self.outbox_events = []
        self.capacities = {}
        self.menus = {}
        self.next_order_id = 1
        self.commits = 0
        self.rollbacks = 0

    def get_user_by_id(self, user_id):
        return self.users.get(user_id)

    def create_order(self, order):
        order.id = self.next_order_id
        self.next_order_id += 1
        order.order_time = datetime.now(timezone.utc)
        order.created_at = order.order_time
        order.updated_at = order.order_time
        self.orders[order.id] = order
        return order

    def create_order_items(self, order_items):
        for index, item in enumerate(order_items, start=len(self.order_items) + 1):
            item.id = index
            item.order = self.orders[item.order_id]
            item.menu = self.menus[item.menu_id]
            self.order_items.append(item)
        return order_items

    def create_finance_records(self, finance_records):
        for index, finance in enumerate(
            finance_records,
            start=len(self.finance_records) + 1,
        ):
            finance.id = index
            finance.order = self.orders[finance.order_id]
            finance.merchant = self.menus[1].merchant
            self.finance_records.append(finance)
        return finance_records

    def get_by_user_id_and_idempotency_key(self, user_id, idempotency_key):
        for order in self.orders.values():
            if order.user_id == user_id and order.idempotency_key == idempotency_key:
                return order
        return None

    def get_by_id(self, order_id):
        order = self.orders.get(order_id)
        if not order:
            return None

        order.items = [item for item in self.order_items if item.order_id == order_id]
        order.finance_records = [
            finance for finance in self.finance_records if finance.order_id == order_id
        ]
        return order

    def get_by_id_for_update(self, order_id):
        return self.get_by_id(order_id)

    def list_by_user_id(self, user_id):
        return [order for order in self.orders.values() if order.user_id == user_id]

    def ensure_menu_daily_capacities(self, menus, target_date):
        for menu in menus:
            self.capacities.setdefault(
                (menu.id, target_date),
                {
                    "max_quantity": menu.max_daily_quantity,
                    "remaining_quantity": menu.max_daily_quantity,
                },
            )

    def deduct_menu_daily_capacity(self, menu_id, target_date, quantity):
        capacity = self.capacities[(menu_id, target_date)]
        if capacity["remaining_quantity"] < quantity:
            return False
        capacity["remaining_quantity"] -= quantity
        return True

    def restore_menu_daily_capacity(self, menu_id, target_date, quantity):
        capacity = self.capacities[(menu_id, target_date)]
        capacity["remaining_quantity"] += quantity
        return True

    def create_outbox_event(self, event):
        event.id = len(self.outbox_events) + 1
        event.published_at = None
        event.retry_count = 0
        event.last_error = None
        self.outbox_events.append(event)
        return event

    def list_unpublished_outbox_events(self, limit=100):
        now = datetime.now(timezone.utc)
        return [
            event
            for event in self.outbox_events
            if event.published_at is None and event.available_at <= now
        ][:limit]

    def mark_outbox_event_published(self, event):
        event.published_at = datetime.now(timezone.utc)
        event.last_error = None

    def mark_outbox_event_failed(self, event, error):
        event.retry_count += 1
        event.last_error = error

    def flush(self):
        return None

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, instance):
        return instance

    def is_integrity_error(self, error):
        return False


def build_menu(menu_id=1, quantity=2):
    merchant = MerchantInfo(
        id=1,
        merchant_name="Test Bento",
        min_order=Decimal("80.00"),
        audit_status=1,
    )
    menu = Menu(
        id=menu_id,
        merchant_id=1,
        item_name="Chicken Bento",
        max_daily_quantity=quantity,
        price=Decimal("120.00"),
    )
    menu.merchant = merchant
    return menu


def build_service(menu=None):
    menu = menu or build_menu()
    order_repo = FakeOrderRepository()
    order_repo.menus = {menu.id: menu}
    service = OrderService(
        order_repo=order_repo,
        menu_repo=FakeMenuRepository({menu.id: menu}),
        settings=Settings(
            dispatch_lead_minutes=30,
            max_schedule_days=30,
            queue_backend="fake",
        ),
    )
    return service, order_repo, menu


def order_payload(quantity=1, scheduled_for=None):
    return OrderCreate(
        user_id=1,
        items=[OrderItemCreate(menu_id=1, quantity=quantity)],
        scheduled_for=scheduled_for,
    )


def test_create_immediate_order_keeps_existing_flow():
    service, repo, menu = build_service()

    order = service.create_order(order_payload())

    assert order["order_status"] == 0
    assert order["schedule_status"] == "not_scheduled"
    assert order["order_number"].startswith(f"ORD-{date.today():%Y%m%d}-")
    assert repo.capacities[(menu.id, date.today())]["remaining_quantity"] == 1
    assert repo.outbox_events == []


def test_create_scheduled_order_reserves_capacity_and_writes_outbox():
    service, repo, menu = build_service()
    scheduled_for = datetime.now(timezone.utc) + timedelta(days=1)

    order = service.create_order(order_payload(scheduled_for=scheduled_for))

    assert order["schedule_status"] == "scheduled"
    assert order["order_number"].startswith(
        f"ORD-{scheduled_for.date():%Y%m%d}-"
    )
    assert repo.capacities[(menu.id, scheduled_for.date())]["remaining_quantity"] == 1
    assert len(repo.outbox_events) == 1
    assert repo.outbox_events[0].event_type == "order.release_requested"


def test_rejects_scheduled_for_in_the_past():
    service, _repo, _menu = build_service()
    scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=1)

    with pytest.raises(HTTPException) as error:
        service.create_order(order_payload(scheduled_for=scheduled_for))

    assert error.value.status_code == 422


def test_idempotency_key_reuses_same_order_without_double_capacity_or_outbox():
    service, repo, menu = build_service()
    scheduled_for = datetime.now(timezone.utc) + timedelta(days=1)
    payload = order_payload(scheduled_for=scheduled_for)

    first = service.create_order(payload, idempotency_key="same-key")
    second = service.create_order(payload, idempotency_key="same-key")

    assert second["id"] == first["id"]
    assert repo.capacities[(menu.id, scheduled_for.date())]["remaining_quantity"] == 1
    assert len(repo.outbox_events) == 1


def test_idempotency_key_rejects_different_payload():
    service, _repo, _menu = build_service()
    scheduled_for = datetime.now(timezone.utc) + timedelta(days=1)

    service.create_order(order_payload(scheduled_for=scheduled_for), idempotency_key="k")

    with pytest.raises(HTTPException) as error:
        service.create_order(
            order_payload(quantity=2, scheduled_for=scheduled_for),
            idempotency_key="k",
        )

    assert error.value.status_code == 409


def test_only_one_order_can_take_last_capacity():
    service, repo, menu = build_service(build_menu(quantity=1))
    scheduled_for = datetime.now(timezone.utc) + timedelta(days=1)

    service.create_order(order_payload(scheduled_for=scheduled_for))

    with pytest.raises(HTTPException) as error:
        service.create_order(order_payload(scheduled_for=scheduled_for))

    assert error.value.status_code == 400
    assert repo.capacities[(menu.id, scheduled_for.date())]["remaining_quantity"] == 0


def test_dispatcher_marks_published_after_successful_enqueue():
    service, repo, _menu = build_service()
    scheduled_for = datetime.now(timezone.utc) + timedelta(minutes=5)
    service.create_order(order_payload(scheduled_for=scheduled_for))
    event = repo.outbox_events[0]
    expected_execute_at = datetime.fromisoformat(event.payload_json["execute_at"])
    event.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    queue = FakeTaskQueue()

    result = OutboxDispatcher(repo, queue).dispatch_once()

    assert result == {"published": 1, "failed": 0}
    assert event.published_at is not None
    assert queue.tasks[0].order_id == 1
    assert queue.tasks[0].execute_at == expected_execute_at


def test_dispatcher_keeps_event_unpublished_after_enqueue_failure():
    service, repo, _menu = build_service()
    scheduled_for = datetime.now(timezone.utc) + timedelta(minutes=5)
    service.create_order(order_payload(scheduled_for=scheduled_for))
    event = repo.outbox_events[0]
    event.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    result = OutboxDispatcher(repo, FakeTaskQueue(fail=True)).dispatch_once()

    assert result == {"published": 0, "failed": 1}
    assert event.published_at is None
    assert event.retry_count == 1


def test_release_handler_is_idempotent_and_writes_released_event_once():
    service, repo, _menu = build_service()
    scheduled_for = datetime.now(timezone.utc) + timedelta(minutes=5)
    order = service.create_order(order_payload(scheduled_for=scheduled_for))

    first = service.release_scheduled_order(order["id"], "task-1", "corr-1")
    second = service.release_scheduled_order(order["id"], "task-1", "corr-1")

    assert first == {"status": "released"}
    assert second == {"status": "released"}
    assert repo.orders[order["id"]].released_at is not None
    assert [event.event_type for event in repo.outbox_events].count("order.released") == 1


def test_cancel_scheduled_order_restores_capacity_and_late_release_is_noop():
    service, repo, menu = build_service()
    scheduled_for = datetime.now(timezone.utc) + timedelta(days=1)
    order = service.create_order(order_payload(scheduled_for=scheduled_for))

    cancelled = service.cancel_order(order["id"], reason="user changed plans")
    release = service.release_scheduled_order(order["id"], "task-1", "corr-1")

    assert cancelled["order_status"] == 2
    assert cancelled["schedule_status"] == "cancelled"
    assert repo.capacities[(menu.id, scheduled_for.date())]["remaining_quantity"] == 2
    assert release == {"status": "cancelled"}
    assert [event.event_type for event in repo.outbox_events].count("order.released") == 0


def test_status_cancel_for_scheduled_order_uses_cancel_flow():
    service, repo, menu = build_service()
    scheduled_for = datetime.now(timezone.utc) + timedelta(days=1)
    order = service.create_order(order_payload(scheduled_for=scheduled_for))

    cancelled = service.update_order_status(order["id"], 2)

    assert cancelled["schedule_status"] == "cancelled"
    assert repo.capacities[(menu.id, scheduled_for.date())]["remaining_quantity"] == 2


def test_fake_queue_records_payload_and_execute_at():
    queue = FakeTaskQueue()
    execute_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    queue.enqueue_order_release(
        order_id=42,
        task_key="order-release-42",
        execute_at=execute_at,
        correlation_id="corr",
    )

    assert queue.tasks[0].order_id == 42
    assert queue.tasks[0].task_key == "order-release-42"
    assert queue.tasks[0].execute_at == execute_at
    assert queue.tasks[0].correlation_id == "corr"
