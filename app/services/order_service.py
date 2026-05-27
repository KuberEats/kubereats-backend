from collections import defaultdict
from decimal import Decimal
from datetime import date, datetime, timezone, timedelta
import hashlib
import json
from uuid import uuid4


from fastapi import HTTPException

from app.config import Settings, get_settings
from app.models.kubereats import Finance, Order, OrderItem, OutboxEvent
from app.repo.menu_repo import MenuRepository
from app.repo.order_repo import OrderRepository
from app.schemas.order import OrderCreate, OrderHistorySortKey


class OrderService:
    PLATFORM_SETTLEMENT_RATE = Decimal("0.90")
    VALID_ORDER_STATUSES = {0, 1, 2}

    def __init__(
        self,
        order_repo: OrderRepository,
        menu_repo: MenuRepository,
        settings: Settings | None = None,
    ):
        self.order_repo = order_repo
        self.menu_repo = menu_repo
        self.settings = settings or get_settings()

    def create_order(self, order_data: OrderCreate, idempotency_key: str | None = None):
        user = self.order_repo.get_user_by_id(order_data.user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        request_hash = self._hash_order_request(order_data)
        if idempotency_key:
            existing = self.order_repo.get_by_user_id_and_idempotency_key(
                order_data.user_id,
                idempotency_key,
            )
            if existing:
                if existing.idempotency_request_hash != request_hash:
                    raise HTTPException(
                        status_code=409,
                        detail="Idempotency-Key was reused with a different payload",
                    )
                return self.get_order_by_id(existing.id)

        menu_quantity_map = self._merge_item_quantities(order_data)
        menus = self._load_menus(menu_quantity_map)
        total_amount = self._calculate_total_amount(menu_quantity_map, menus)
        self._validate_merchant_min_orders(menu_quantity_map, menus)

        scheduled_for, dispatch_at, target_date, schedule_status = (
            self._resolve_schedule(order_data.scheduled_for)
        )

        try:
            # Ensure daily capacity records exist for all involved menu items before proceeding with order creation to prevent concurrency issues.
            self.order_repo.ensure_menu_daily_capacities(
                menus.values(),
                target_date,
            )

            self._deduct_daily_capacities(menu_quantity_map, menus, target_date)

            order = self.order_repo.create_order(
                Order(
                    user_id=order_data.user_id,
                    total_amount=total_amount,
                    order_status=0,
                    service_date=target_date,
                    scheduled_for=scheduled_for,
                    dispatch_at=dispatch_at,
                    schedule_status=schedule_status,
                    idempotency_key=idempotency_key,
                    idempotency_request_hash=request_hash if idempotency_key else None,
                )
            )
            order.order_number = self._generate_order_number(order.id, target_date)
            self.order_repo.flush()

            order_items = [
                OrderItem(
                    order_id=order.id,
                    menu_id=menu.id,
                    quantity=menu_quantity_map[menu.id],
                    unit_price=menu.price,
                    subtotal=menu.price * menu_quantity_map[menu.id],
                )
                for menu in menus.values()
            ]
            self.order_repo.create_order_items(order_items)

            finance_records = self._build_finance_records(
                order.id, menu_quantity_map, menus
            )
            self.order_repo.create_finance_records(finance_records)

            if schedule_status == "scheduled":
                self.order_repo.create_outbox_event(
                    self._build_outbox_event(
                        order=order,
                        event_type="order.release_requested",
                        available_at=dispatch_at,
                        extra_payload={
                            "task_key": self._release_task_key(order.id),
                            "execute_at": dispatch_at.isoformat(),
                        },
                    )
                )

            self.order_repo.commit()
            return self.get_order_by_id(order.id)
        except Exception as error:
            if self.order_repo.is_integrity_error(error) and idempotency_key:
                self.order_repo.rollback()
                existing = self.order_repo.get_by_user_id_and_idempotency_key(
                    order_data.user_id,
                    idempotency_key,
                )
                if existing and existing.idempotency_request_hash == request_hash:
                    return self.get_order_by_id(existing.id)
                if existing:
                    raise HTTPException(
                        status_code=409,
                        detail="Idempotency-Key was reused with a different payload",
                    )
                raise
            self.order_repo.rollback()
            raise

    def get_order_by_id(self, order_id: int):
        order = self.order_repo.get_by_id(order_id)

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        return self._serialize_order(order)

    def list_orders_by_user(self, user_id: int, sort_by: OrderHistorySortKey):
        user = self.order_repo.get_user_by_id(user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        orders = self.order_repo.list_by_user_id(user_id)

        if sort_by == "merchant":
            orders = sorted(orders, key=self._primary_merchant_name)

        return [self._serialize_order(order) for order in orders]

    def update_order_status(self, order_id: int, order_status: int):
        order = self.order_repo.get_by_id(order_id)

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order_status == 2 and order.schedule_status == "scheduled":
            return self.cancel_order(order_id)

        if order_status not in self.VALID_ORDER_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid order status")

        if order.order_status in {1, 2} and order.order_status != order_status:
            raise HTTPException(
                status_code=400,
                detail="Completed or cancelled orders cannot change status",
            )

        order.order_status = order_status
        self.order_repo.commit()
        return self.get_order_by_id(order.id)

    def cancel_order(self, order_id: int, reason: str | None = None):
        try:
            order = self.order_repo.get_by_id_for_update(order_id)

            if not order:
                raise HTTPException(status_code=404, detail="Order not found")

            if order.schedule_status != "scheduled":
                raise HTTPException(
                    status_code=400,
                    detail="Only unreleased scheduled orders can be cancelled",
                )

            if order.order_status == 2:
                raise HTTPException(status_code=400, detail="Order is already cancelled")

            for item in order.items:
                restored = self.order_repo.restore_menu_daily_capacity(
                    item.menu_id,
                    order.service_date,
                    item.quantity,
                )
                if not restored:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to restore menu capacity",
                    )

            now = datetime.now(timezone.utc)
            order.order_status = 2
            order.schedule_status = "cancelled"
            order.cancelled_at = now
            order.cancellation_reason = reason
            self.order_repo.create_outbox_event(
                self._build_outbox_event(
                    order=order,
                    event_type="order.cancelled",
                    available_at=now,
                    extra_payload={"reason": reason},
                )
            )
            self.order_repo.commit()
            return self.get_order_by_id(order.id)
        except Exception:
            self.order_repo.rollback()
            raise

    def release_scheduled_order(self, order_id: int, task_key: str, correlation_id: str):
        try:
            order = self.order_repo.get_by_id_for_update(order_id)

            if not order:
                raise HTTPException(status_code=404, detail="Order not found")

            if order.schedule_status in {"released", "cancelled"}:
                self.order_repo.commit()
                return {"status": order.schedule_status}

            if order.schedule_status != "scheduled":
                raise HTTPException(
                    status_code=400,
                    detail="Order is not scheduled for release",
                )

            now = datetime.now(timezone.utc)
            order.schedule_status = "released"
            order.released_at = now
            self.order_repo.create_outbox_event(
                self._build_outbox_event(
                    order=order,
                    event_type="order.released",
                    available_at=now,
                    extra_payload={
                        "task_key": task_key,
                        "correlation_id": correlation_id,
                    },
                )
            )
            self.order_repo.commit()
            return {"status": "released"}
        except Exception:
            self.order_repo.rollback()
            raise

    def _merge_item_quantities(self, order_data: OrderCreate):
        menu_quantity_map = defaultdict(int)

        for item in order_data.items:
            menu_quantity_map[item.menu_id] += item.quantity

        return dict(menu_quantity_map)

    def _load_menus(self, menu_quantity_map: dict[int, int]):
        menus = {}

        for menu_id in menu_quantity_map:
            menu = self.menu_repo.get_by_id(menu_id)

            if not menu:
                raise HTTPException(
                    status_code=404,
                    detail=f"Menu item {menu_id} not found",
                )

            if menu.merchant.audit_status != 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"Menu item {menu_id} is not available",
                )

            menus[menu_id] = menu

        return menus

    def _calculate_total_amount(self, menu_quantity_map, menus):
        total_amount = Decimal("0.00")

        for menu_id, quantity in menu_quantity_map.items():
            menu = menus[menu_id]

            if quantity > menu.max_daily_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"{menu.item_name} exceeds daily available quantity",
                )

            total_amount += menu.price * quantity

        return total_amount

    def _validate_merchant_min_orders(self, menu_quantity_map, menus):
        merchant_totals = defaultdict(Decimal)

        for menu_id, quantity in menu_quantity_map.items():
            menu = menus[menu_id]
            merchant_totals[menu.merchant_id] += menu.price * quantity

        for merchant_id, merchant_total in merchant_totals.items():
            merchant = next(
                menu.merchant
                for menu in menus.values()
                if menu.merchant_id == merchant_id
            )

            if merchant_total < merchant.min_order:
                raise HTTPException(
                    status_code=400,
                    detail=f"{merchant.merchant_name} minimum order is {merchant.min_order}",
                )

    def _deduct_daily_capacities(self, menu_quantity_map, menus, target_date):
        for menu_id, quantity in menu_quantity_map.items():
            menu = menus[menu_id]
            deducted = self.order_repo.deduct_menu_daily_capacity(
                menu.id,
                target_date,
                quantity,
            )

            if not deducted:
                raise HTTPException(
                    status_code=400,
                    detail=f"{menu.item_name} exceeds remaining daily quantity",
                )

    def _build_finance_records(self, order_id: int, menu_quantity_map, menus):
        merchant_items = defaultdict(list)

        for menu_id, quantity in menu_quantity_map.items():
            menu = menus[menu_id]
            subtotal = menu.price * quantity
            merchant_items[menu.merchant_id].append(
                {
                    "menu_id": menu.id,
                    "name": menu.item_name,
                    "quantity": quantity,
                    "price": float(menu.price),
                    "subtotal": float(subtotal),
                }
            )

        finance_records = []

        for merchant_id, items in merchant_items.items():
            merchant_total = sum(Decimal(str(item["subtotal"])) for item in items)
            settlement_amount = merchant_total * self.PLATFORM_SETTLEMENT_RATE

            finance_records.append(
                Finance(
                    merchant_id=merchant_id,
                    order_id=order_id,
                    report_data={
                        "items": items,
                        "merchant_total": float(merchant_total),
                        "settlement_rate": float(self.PLATFORM_SETTLEMENT_RATE),
                    },
                    settlement_amount=settlement_amount,
                )
            )

        return finance_records

    def _primary_merchant_name(self, order):
        merchant_names = sorted(
            finance.merchant.merchant_name for finance in order.finance_records
        )
        return merchant_names[0] if merchant_names else ""

    def _serialize_order(self, order):
        return {
            "id": order.id,
            "user_id": order.user_id,
            "order_number": order.order_number,
            "total_amount": float(order.total_amount),
            "order_status": order.order_status,
            "schedule_status": order.schedule_status,
            "scheduled_for": order.scheduled_for,
            "dispatch_at": order.dispatch_at,
            "released_at": order.released_at,
            "cancelled_at": order.cancelled_at,
            "order_time": order.order_time,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "items": [
                {
                    "id": item.id,
                    "menu_id": item.menu_id,
                    "item_name": item.menu.item_name,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "subtotal": float(item.subtotal),
                }
                for item in order.items
            ],
            "finance_records": [
                {
                    "id": finance.id,
                    "merchant_id": finance.merchant_id,
                    "merchant_name": finance.merchant.merchant_name,
                    "settlement_amount": float(finance.settlement_amount),
                    "report_data": finance.report_data,
                }
                for finance in order.finance_records
            ],
        }

    def _resolve_schedule(self, scheduled_for: datetime | None):
        if scheduled_for is None:
            return None, None, date.today(), "not_scheduled"

        scheduled_for = self._ensure_aware(scheduled_for)
        now = datetime.now(timezone.utc)

        if scheduled_for <= now:
            raise HTTPException(status_code=422, detail="scheduled_for cannot be in the past")

        if scheduled_for > now + timedelta(days=self.settings.max_schedule_days):
            raise HTTPException(
                status_code=422,
                detail=f"scheduled_for cannot be more than {self.settings.max_schedule_days} days ahead",
            )

        dispatch_at = scheduled_for - timedelta(
            minutes=self.settings.dispatch_lead_minutes
        )
        return scheduled_for, dispatch_at, scheduled_for.date(), "scheduled"

    def _ensure_aware(self, value: datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _hash_order_request(self, order_data: OrderCreate):
        payload = order_data.model_dump(mode="json", by_alias=False)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def _generate_order_number(self, order_id: int, service_date: date):
        return f"ORD-{service_date:%Y%m%d}-{order_id:06d}"

    def _release_task_key(self, order_id: int):
        return f"order-release-{order_id}"

    def _build_outbox_event(
        self,
        *,
        order: Order,
        event_type: str,
        available_at: datetime,
        extra_payload: dict | None = None,
    ):
        payload = {
            "order_id": order.id,
            "order_number": order.order_number,
            "schedule_status": order.schedule_status,
            "correlation_id": str(uuid4()),
        }
        if extra_payload:
            payload.update(extra_payload)

        return OutboxEvent(
            aggregate_type="order",
            aggregate_id=order.id,
            event_type=event_type,
            payload_json=payload,
            available_at=available_at,
        )
