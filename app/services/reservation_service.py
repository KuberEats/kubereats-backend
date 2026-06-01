from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import logging
from secrets import token_urlsafe
from uuid import uuid4

from fastapi import HTTPException

from app.config import Settings, get_settings
from app.metrics import (
    reservation_capacity_failures,
    reservation_items_requested,
    reservation_processing,
    reservation_requests,
    reservations_cancelled,
)
from app.models.kubereats import (
    ReservationOutboxEvent,
    ReservationRequest,
    ReservationRequestItem,
)
from app.repo.reservation_repo import ReservationRepository
from app.schemas.reservation import ReservationCreate

logger = logging.getLogger(__name__)


TERMINAL_RESERVATION_STATUSES = {
    "RESERVED",
    "SOLD_OUT",
    "CANCELLED",
    "EXPIRED",
    "FAILED",
}


class ReservationSoldOut(Exception):
    pass


class ReservationService:
    def __init__(
        self,
        reservation_repo: ReservationRepository,
        settings: Settings | None = None,
    ):
        self.reservation_repo = reservation_repo
        self.settings = settings or get_settings()

    def create_reservation_request(
        self,
        reservation_data: ReservationCreate,
        idempotency_key: str | None = None,
    ):
        request_hash = self._hash_create_request(reservation_data)
        if idempotency_key:
            existing = self.reservation_repo.get_by_user_id_and_idempotency_key(
                reservation_data.user_id,
                idempotency_key,
            )
            if existing:
                if existing.idempotency_request_hash != request_hash:
                    raise HTTPException(
                        status_code=409,
                        detail="Idempotency-Key was reused with a different payload",
                    )
                return self._serialize_accepted(existing)

        self._validate_user_and_merchant(reservation_data)
        self._validate_service_date(reservation_data.service_date)
        menu_quantity_map = self._merge_item_quantities(reservation_data)
        menus = self._load_and_validate_menus(
            merchant_id=reservation_data.merchant_id,
            menu_quantity_map=menu_quantity_map,
        )

        pickup_slot = self._normalize_pickup_slot(reservation_data.pickup_slot)

        try:
            reservation = ReservationRequest(
                reservation_token=self._generate_reservation_token(),
                user_id=reservation_data.user_id,
                merchant_id=reservation_data.merchant_id,
                service_date=reservation_data.service_date,
                pickup_slot=pickup_slot,
                pickup_option=reservation_data.pickup_option,
                comments=self._normalize_optional_text(reservation_data.comments),
                diner_name=self._normalize_optional_text(reservation_data.diner_name),
                diner_phone=self._normalize_optional_text(reservation_data.diner_phone),
                status="PENDING_RESERVATION",
                idempotency_key=idempotency_key,
                idempotency_request_hash=request_hash if idempotency_key else None,
            )
            self.reservation_repo.create_reservation_request(reservation)

            items = [
                ReservationRequestItem(
                    reservation_request_id=reservation.id,
                    menu_item_id=menu_id,
                    quantity=quantity,
                    unit_price=menus[menu_id].price,
                    subtotal=menus[menu_id].price * quantity,
                )
                for menu_id, quantity in sorted(menu_quantity_map.items())
            ]
            self.reservation_repo.create_reservation_items(items)

            event = self._build_reservation_requested_event(reservation, items)
            self.reservation_repo.create_outbox_event(event)
            logger.info(
                "reservation_request_created",
                extra={
                    "reservation_id": reservation.id,
                    "reservation_token": reservation.reservation_token,
                    "status": reservation.status,
                },
            )
            logger.info(
                "reservation_outbox_event_created",
                extra={
                    "event_id": event.id,
                    "reservation_id": reservation.id,
                    "ordering_key": event.ordering_key,
                },
            )

            self.reservation_repo.commit()
            reservation_requests.inc(reservation.status)
            reservation_items_requested.inc(amount=sum(menu_quantity_map.values()))
            return self._serialize_accepted(reservation)
        except Exception as error:
            if self.reservation_repo.is_integrity_error(error) and idempotency_key:
                self.reservation_repo.rollback()
                existing = self.reservation_repo.get_by_user_id_and_idempotency_key(
                    reservation_data.user_id,
                    idempotency_key,
                )
                if existing and existing.idempotency_request_hash == request_hash:
                    return self._serialize_accepted(existing)
                if existing:
                    raise HTTPException(
                        status_code=409,
                        detail="Idempotency-Key was reused with a different payload",
                    )
            self.reservation_repo.rollback()
            raise

    def get_reservation_by_token(self, reservation_token: str):
        reservation = self.reservation_repo.get_by_token(reservation_token)
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation request not found")

        return self._serialize_reservation(reservation)

    def cancel_reservation(self, reservation_token: str):
        try:
            reservation = self.reservation_repo.get_by_token(reservation_token)
            if not reservation:
                raise HTTPException(
                    status_code=404,
                    detail="Reservation request not found",
                )

            locked = self.reservation_repo.get_by_id_for_update(reservation.id)
            if not locked:
                raise HTTPException(
                    status_code=404,
                    detail="Reservation request not found",
                )

            if locked.status == "CANCELLED":
                self.reservation_repo.commit()
                reservations_cancelled.inc(locked.status)
                return self._serialize_reservation(locked)

            if locked.status == "PENDING_RESERVATION" or locked.status == "PROCESSING":
                self._mark_cancelled(locked)
                self.reservation_repo.commit()
                logger.info(
                    "reservation_cancelled",
                    extra={"reservation_id": locked.id, "status": locked.status},
                )
                reservations_cancelled.inc(locked.status)
                return self._serialize_reservation(locked)

            if locked.status == "RESERVED":
                for item in self._sorted_items(locked):
                    released = self.reservation_repo.release_capacity(
                        merchant_id=locked.merchant_id,
                        menu_item_id=item.menu_item_id,
                        service_date=locked.service_date,
                        pickup_slot=locked.pickup_slot,
                        quantity=item.quantity,
                    )
                    if not released:
                        raise HTTPException(
                            status_code=500,
                            detail="Failed to release reservation capacity",
                        )
                self._mark_cancelled(locked)
                self.reservation_repo.commit()
                logger.info(
                    "reservation_cancelled",
                    extra={"reservation_id": locked.id, "status": locked.status},
                )
                reservations_cancelled.inc(locked.status)
                return self._serialize_reservation(locked)

            self.reservation_repo.commit()
            return self._serialize_reservation(locked)
        except Exception:
            self.reservation_repo.rollback()
            raise

    def process_reservation_requested(self, payload: dict):
        reservation_id = int(payload["reservation_id"])
        started = self._start_processing(reservation_id)
        if started in TERMINAL_RESERVATION_STATUSES:
            reservation_processing.inc(started)
            return {"status": started}

        try:
            result = self._reserve_capacity_transaction(reservation_id)
            reservation_processing.inc(result["status"])
            return result
        except ReservationSoldOut as error:
            self._mark_sold_out(reservation_id, str(error))
            reservation_processing.inc("SOLD_OUT")
            reservation_capacity_failures.inc("sold_out")
            return {"status": "SOLD_OUT"}
        except Exception as error:
            self._mark_retryable_failure(reservation_id, str(error))
            reservation_processing.inc("FAILED")
            raise

    def process_reservation_by_id(self, reservation_id: int):
        return self.process_reservation_requested({"reservation_id": reservation_id})

    def _start_processing(self, reservation_id: int):
        try:
            reservation = self.reservation_repo.get_by_id_for_update(reservation_id)
            if not reservation:
                raise HTTPException(
                    status_code=404, detail="Reservation request not found"
                )

            if reservation.status in TERMINAL_RESERVATION_STATUSES:
                self.reservation_repo.commit()
                return reservation.status

            now = datetime.now(timezone.utc)
            reservation.status = "PROCESSING"
            reservation.lease_until = now + timedelta(
                seconds=self.settings.reservation_processing_lease_seconds
            )
            self.reservation_repo.commit()
            logger.info(
                "reservation_processing_started",
                extra={"reservation_id": reservation.id, "status": reservation.status},
            )
            return reservation.status
        except Exception:
            self.reservation_repo.rollback()
            raise

    def _reserve_capacity_transaction(self, reservation_id: int):
        try:
            reservation = self.reservation_repo.get_by_id_for_update(reservation_id)
            if not reservation:
                raise HTTPException(
                    status_code=404, detail="Reservation request not found"
                )

            if reservation.status in TERMINAL_RESERVATION_STATUSES:
                self.reservation_repo.commit()
                return {"status": reservation.status}
            if reservation.status != "PROCESSING":
                self.reservation_repo.commit()
                return {"status": reservation.status}

            self._ensure_capacity_slots_for_reservation(reservation)

            for item in self._sorted_items(reservation):
                reserved = self.reservation_repo.reserve_capacity(
                    merchant_id=reservation.merchant_id,
                    menu_item_id=item.menu_item_id,
                    service_date=reservation.service_date,
                    pickup_slot=reservation.pickup_slot,
                    quantity=item.quantity,
                )
                if not reserved:
                    raise ReservationSoldOut(
                        f"Insufficient capacity for menu item {item.menu_item_id}"
                    )

            now = datetime.now(timezone.utc)
            reservation.status = "RESERVED"
            reservation.processed_at = now
            reservation.lease_until = None
            reservation.failure_reason = None
            self.reservation_repo.commit()
            logger.info(
                "reservation_reserved",
                extra={"reservation_id": reservation.id, "status": reservation.status},
            )
            return {"status": "RESERVED"}
        except ReservationSoldOut:
            self.reservation_repo.rollback()
            raise
        except Exception:
            self.reservation_repo.rollback()
            raise

    def _mark_sold_out(self, reservation_id: int, reason: str):
        try:
            reservation = self.reservation_repo.get_by_id_for_update(reservation_id)
            if not reservation or reservation.status in TERMINAL_RESERVATION_STATUSES:
                self.reservation_repo.commit()
                return

            now = datetime.now(timezone.utc)
            reservation.status = "SOLD_OUT"
            reservation.processed_at = now
            reservation.lease_until = None
            reservation.failure_reason = reason[:1000]
            self.reservation_repo.commit()
            logger.info(
                "reservation_sold_out",
                extra={"reservation_id": reservation_id, "reason": reason[:1000]},
            )
        except Exception:
            self.reservation_repo.rollback()
            raise

    def _mark_retryable_failure(self, reservation_id: int, reason: str):
        try:
            reservation = self.reservation_repo.get_by_id_for_update(reservation_id)
            if not reservation or reservation.status in TERMINAL_RESERVATION_STATUSES:
                self.reservation_repo.commit()
                return

            reservation.status = "PENDING_RESERVATION"
            reservation.retry_count += 1
            reservation.failure_reason = reason[:1000]
            reservation.lease_until = datetime.now(timezone.utc) + timedelta(
                seconds=min(300, 2 ** min(reservation.retry_count, 8))
            )
            self.reservation_repo.commit()
            logger.info(
                "reservation_failed",
                extra={"reservation_id": reservation_id, "reason": reason[:1000]},
            )
        except Exception:
            self.reservation_repo.rollback()
            raise

    def _ensure_capacity_slots_for_reservation(self, reservation: ReservationRequest):
        rows = []
        for item in reservation.items:
            total_capacity = item.menu.max_daily_quantity if item.menu else 0
            rows.append(
                {
                    "merchant_id": reservation.merchant_id,
                    "menu_item_id": item.menu_item_id,
                    "service_date": reservation.service_date,
                    "pickup_slot": reservation.pickup_slot,
                    "total_capacity": total_capacity,
                    "reserved_count": 0,
                }
            )
        self.reservation_repo.ensure_capacity_slots(rows)

    def _validate_user_and_merchant(self, reservation_data: ReservationCreate):
        user = self.reservation_repo.get_user_by_id(reservation_data.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        merchant = self.reservation_repo.get_merchant_by_id(
            reservation_data.merchant_id
        )
        if not merchant:
            raise HTTPException(status_code=404, detail="Merchant not found")
        if merchant.audit_status != 1:
            raise HTTPException(status_code=400, detail="Merchant is not available")

    def _validate_service_date(self, service_date: date):
        today = date.today()
        if service_date < today:
            raise HTTPException(
                status_code=422, detail="service_date cannot be in the past"
            )
        if service_date > today + timedelta(days=7):
            raise HTTPException(
                status_code=422,
                detail="service_date cannot be more than 7 days ahead",
            )

    def _merge_item_quantities(self, reservation_data: ReservationCreate):
        menu_quantity_map = defaultdict(int)
        for item in reservation_data.items:
            menu_quantity_map[item.menu_item_id] += item.quantity
        return dict(menu_quantity_map)

    def _load_and_validate_menus(
        self,
        *,
        merchant_id: int,
        menu_quantity_map: dict[int, int],
    ):
        menus = self.reservation_repo.get_menus_by_ids(menu_quantity_map.keys())

        for menu_id, quantity in menu_quantity_map.items():
            menu = menus.get(menu_id)
            if not menu:
                raise HTTPException(
                    status_code=404,
                    detail=f"Menu item {menu_id} not found",
                )
            if menu.merchant_id != merchant_id:
                raise HTTPException(
                    status_code=400,
                    detail="All reservation items must belong to the selected merchant",
                )
            if not menu.merchant or menu.merchant.audit_status != 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"Menu item {menu_id} is not available",
                )
            if quantity > menu.max_daily_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"{menu.item_name} exceeds daily available quantity",
                )

        return menus

    def _sorted_items(self, reservation: ReservationRequest):
        return sorted(
            reservation.items,
            key=lambda item: (
                reservation.merchant_id,
                reservation.service_date,
                reservation.pickup_slot,
                item.menu_item_id,
            ),
        )

    def _build_reservation_requested_event(
        self,
        reservation: ReservationRequest,
        items: list[ReservationRequestItem],
    ):
        capacity_key = self._capacity_key(
            merchant_id=reservation.merchant_id,
            service_date=reservation.service_date,
            pickup_slot=reservation.pickup_slot,
        )
        payload = {
            "event_id": str(uuid4()),
            "event_type": "ReservationRequested",
            "reservation_id": reservation.id,
            "reservation_token": reservation.reservation_token,
            "user_id": reservation.user_id,
            "merchant_id": reservation.merchant_id,
            "service_date": reservation.service_date.isoformat(),
            "pickup_slot": reservation.pickup_slot or None,
            "pickup_option": reservation.pickup_option,
            "comments": reservation.comments,
            "diner_name": reservation.diner_name,
            "diner_phone": reservation.diner_phone,
            "capacity_key": capacity_key,
            "items": [
                {
                    "menu_item_id": item.menu_item_id,
                    "quantity": item.quantity,
                }
                for item in items
            ],
        }
        return ReservationOutboxEvent(
            event_type="ReservationRequested",
            aggregate_type="reservation_request",
            aggregate_id=reservation.id,
            payload=payload,
            ordering_key=capacity_key,
            status="PENDING",
        )

    def _capacity_key(
        self,
        *,
        merchant_id: int,
        service_date: date,
        pickup_slot: str,
    ):
        return f"{merchant_id}:{service_date.isoformat()}:{pickup_slot}"

    def _serialize_accepted(self, reservation: ReservationRequest):
        return {
            "reservation_id": reservation.id,
            "reservation_token": reservation.reservation_token,
            "order_token": reservation.reservation_token,
            "status": reservation.status,
            "message": "Reservation request received. Waiting for capacity confirmation.",
        }

    def _serialize_reservation(self, reservation: ReservationRequest):
        items = [
            {
                "id": item.id,
                "menu_item_id": item.menu_item_id,
                "item_name": item.menu.item_name if item.menu else "",
                "quantity": item.quantity,
                "unit_price": float(item.unit_price)
                if isinstance(item.unit_price, Decimal)
                else item.unit_price,
                "subtotal": float(item.subtotal)
                if isinstance(item.subtotal, Decimal)
                else item.subtotal,
            }
            for item in sorted(reservation.items, key=lambda item: item.id)
        ]
        failed_items = items if reservation.status == "SOLD_OUT" else []
        return {
            "reservation_id": reservation.id,
            "reservation_token": reservation.reservation_token,
            "order_token": reservation.reservation_token,
            "status": reservation.status,
            "service_date": reservation.service_date,
            "pickup_slot": reservation.pickup_slot or None,
            "pickup_option": reservation.pickup_option,
            "pickup_number": None,
            "comments": reservation.comments,
            "diner_name": reservation.diner_name,
            "diner_phone": reservation.diner_phone,
            "message": self._message_for_status(reservation.status),
            "items": items,
            "failed_items": failed_items,
            "created_at": reservation.created_at,
            "updated_at": reservation.updated_at,
            "processed_at": reservation.processed_at,
            "cancelled_at": reservation.cancelled_at,
        }

    def _message_for_status(self, status: str):
        if status == "RESERVED":
            return "Meal capacity reserved successfully."
        if status == "SOLD_OUT":
            return "This meal is sold out for the selected date or time slot."
        if status == "CANCELLED":
            return "Reservation cancelled."
        if status == "FAILED":
            return "Reservation failed."
        if status == "EXPIRED":
            return "Reservation expired."
        return "Checking meal availability."

    def _mark_cancelled(self, reservation: ReservationRequest):
        now = datetime.now(timezone.utc)
        reservation.status = "CANCELLED"
        reservation.cancelled_at = now
        reservation.lease_until = None

    def _normalize_pickup_slot(self, pickup_slot: str | None):
        return pickup_slot.strip() if pickup_slot else ""

    def _normalize_optional_text(self, value: str | None):
        normalized = value.strip() if value else ""
        return normalized or None

    def _generate_reservation_token(self):
        return token_urlsafe(24)

    def _hash_create_request(self, reservation_data: ReservationCreate):
        payload = reservation_data.model_dump(mode="json", by_alias=False)
        payload["pickup_slot"] = self._normalize_pickup_slot(payload["pickup_slot"])
        for key in ("comments", "diner_name", "diner_phone"):
            payload[key] = self._normalize_optional_text(payload.get(key))
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()
