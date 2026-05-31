from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import or_, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.kubereats import (
    Menu,
    MerchantInfo,
    ReservationCapacitySlot,
    ReservationOutboxEvent,
    ReservationRequest,
    ReservationRequestItem,
    UserInfo,
)


class ReservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int):
        return self.db.query(UserInfo).filter(UserInfo.id == user_id).first()

    def get_merchant_by_id(self, merchant_id: int):
        return (
            self.db.query(MerchantInfo).filter(MerchantInfo.id == merchant_id).first()
        )

    def get_menus_by_ids(self, menu_item_ids: Iterable[int]):
        ids = list(menu_item_ids)
        if not ids:
            return {}

        menus = (
            self.db.query(Menu)
            .options(joinedload(Menu.merchant))
            .filter(Menu.id.in_(ids))
            .all()
        )
        return {menu.id: menu for menu in menus}

    def get_by_user_id_and_idempotency_key(
        self,
        user_id: int,
        idempotency_key: str,
    ):
        return (
            self.db.query(ReservationRequest)
            .options(
                joinedload(ReservationRequest.items).joinedload(
                    ReservationRequestItem.menu
                )
            )
            .filter(
                ReservationRequest.user_id == user_id,
                ReservationRequest.idempotency_key == idempotency_key,
            )
            .first()
        )

    def get_by_token(self, reservation_token: str):
        return (
            self.db.query(ReservationRequest)
            .options(
                joinedload(ReservationRequest.items).joinedload(
                    ReservationRequestItem.menu
                )
            )
            .filter(ReservationRequest.reservation_token == reservation_token)
            .first()
        )

    def get_by_id(self, reservation_id: int):
        return (
            self.db.query(ReservationRequest)
            .options(
                joinedload(ReservationRequest.items).joinedload(
                    ReservationRequestItem.menu
                )
            )
            .filter(ReservationRequest.id == reservation_id)
            .first()
        )

    def get_by_id_for_update(self, reservation_id: int):
        return (
            self.db.query(ReservationRequest)
            .options(
                joinedload(ReservationRequest.items).joinedload(
                    ReservationRequestItem.menu
                )
            )
            .filter(ReservationRequest.id == reservation_id)
            .with_for_update()
            .first()
        )

    def create_reservation_request(self, reservation: ReservationRequest):
        self.db.add(reservation)
        self.db.flush()
        return reservation

    def create_reservation_items(self, items: list[ReservationRequestItem]):
        self.db.add_all(items)
        self.db.flush()
        return items

    def create_outbox_event(self, event: ReservationOutboxEvent):
        self.db.add(event)
        self.db.flush()
        return event

    def ensure_capacity_slots(
        self,
        rows: list[dict],
    ) -> None:
        if not rows:
            return

        dialect_name = self.db.bind.dialect.name if self.db.bind else ""
        if dialect_name == "postgresql":
            statement = postgres_insert(ReservationCapacitySlot).values(rows)
            statement = statement.on_conflict_do_nothing(
                index_elements=[
                    "merchant_id",
                    "menu_item_id",
                    "service_date",
                    "pickup_slot",
                ]
            )
            self.db.execute(statement)
        elif dialect_name == "sqlite":
            statement = sqlite_insert(ReservationCapacitySlot).values(rows)
            statement = statement.on_conflict_do_nothing(
                index_elements=[
                    "merchant_id",
                    "menu_item_id",
                    "service_date",
                    "pickup_slot",
                ]
            )
            self.db.execute(statement)
        else:
            existing_keys = {
                (
                    slot.merchant_id,
                    slot.menu_item_id,
                    slot.service_date,
                    slot.pickup_slot,
                )
                for slot in self.db.query(ReservationCapacitySlot)
                .filter(
                    ReservationCapacitySlot.merchant_id.in_(
                        {row["merchant_id"] for row in rows}
                    ),
                    ReservationCapacitySlot.menu_item_id.in_(
                        {row["menu_item_id"] for row in rows}
                    ),
                    ReservationCapacitySlot.service_date.in_(
                        {row["service_date"] for row in rows}
                    ),
                )
                .all()
            }
            self.db.add_all(
                ReservationCapacitySlot(**row)
                for row in rows
                if (
                    row["merchant_id"],
                    row["menu_item_id"],
                    row["service_date"],
                    row["pickup_slot"],
                )
                not in existing_keys
            )

        self.db.flush()

    def reserve_capacity(
        self,
        *,
        merchant_id: int,
        menu_item_id: int,
        service_date,
        pickup_slot: str,
        quantity: int,
    ) -> bool:
        statement = (
            update(ReservationCapacitySlot)
            .where(
                ReservationCapacitySlot.merchant_id == merchant_id,
                ReservationCapacitySlot.menu_item_id == menu_item_id,
                ReservationCapacitySlot.service_date == service_date,
                ReservationCapacitySlot.pickup_slot == pickup_slot,
                ReservationCapacitySlot.reserved_count + quantity
                <= ReservationCapacitySlot.total_capacity,
            )
            .values(reserved_count=ReservationCapacitySlot.reserved_count + quantity)
        )
        result = self.db.execute(statement)
        self.db.flush()
        return result.rowcount == 1

    def release_capacity(
        self,
        *,
        merchant_id: int,
        menu_item_id: int,
        service_date,
        pickup_slot: str,
        quantity: int,
    ) -> bool:
        statement = (
            update(ReservationCapacitySlot)
            .where(
                ReservationCapacitySlot.merchant_id == merchant_id,
                ReservationCapacitySlot.menu_item_id == menu_item_id,
                ReservationCapacitySlot.service_date == service_date,
                ReservationCapacitySlot.pickup_slot == pickup_slot,
                ReservationCapacitySlot.reserved_count >= quantity,
            )
            .values(reserved_count=ReservationCapacitySlot.reserved_count - quantity)
        )
        result = self.db.execute(statement)
        self.db.flush()
        return result.rowcount == 1

    def get_capacity_slot(
        self,
        *,
        merchant_id: int,
        menu_item_id: int,
        service_date,
        pickup_slot: str,
    ):
        return (
            self.db.query(ReservationCapacitySlot)
            .filter(
                ReservationCapacitySlot.merchant_id == merchant_id,
                ReservationCapacitySlot.menu_item_id == menu_item_id,
                ReservationCapacitySlot.service_date == service_date,
                ReservationCapacitySlot.pickup_slot == pickup_slot,
            )
            .first()
        )

    def list_publishable_outbox_events(self, limit: int = 100):
        now = datetime.now(timezone.utc)
        return (
            self.db.query(ReservationOutboxEvent)
            .filter(
                ReservationOutboxEvent.status.in_(["PENDING", "FAILED_RETRYABLE"]),
                or_(
                    ReservationOutboxEvent.next_retry_at.is_(None),
                    ReservationOutboxEvent.next_retry_at <= now,
                ),
            )
            .order_by(
                ReservationOutboxEvent.next_retry_at.asc().nullsfirst(),
                ReservationOutboxEvent.id.asc(),
            )
            .with_for_update(skip_locked=True)
            .limit(limit)
            .all()
        )

    def claim_pending_reservation_ids(self, limit: int, lease_until: datetime):
        now = datetime.now(timezone.utc)
        reservations = (
            self.db.query(ReservationRequest)
            .filter(
                ReservationRequest.status == "PENDING_RESERVATION",
                or_(
                    ReservationRequest.lease_until.is_(None),
                    ReservationRequest.lease_until <= now,
                ),
            )
            .order_by(ReservationRequest.created_at.asc(), ReservationRequest.id.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
            .all()
        )

        ids = []
        for reservation in reservations:
            reservation.lease_until = lease_until
            ids.append(reservation.id)

        self.db.flush()
        return ids

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    def flush(self):
        self.db.flush()

    def is_integrity_error(self, error: Exception):
        return isinstance(error, IntegrityError)
