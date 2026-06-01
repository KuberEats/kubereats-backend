from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.database import Base
from app.models.kubereats import (
    Menu,
    MerchantInfo,
    ReservationCapacitySlot,
    ReservationOutboxEvent,
    ReservationRequest,
    ReservationRequestItem,
    UserInfo,
)
from app.queues.reservation import LocalReservationEventPublisher
from app.repo.reservation_repo import ReservationRepository
from app.schemas.reservation import ReservationCreate, ReservationItemCreate
from app.services.reservation_outbox_publisher import ReservationOutboxPublisher
from app.services.reservation_service import ReservationService
from app.services.reservation_worker import ReservationDbPollingWorker


@pytest.fixture()
def session_factory(tmp_path):
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'reservations.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    db = factory()
    try:
        seed_data(db)
        db.commit()
    finally:
        db.close()

    return factory


@pytest.fixture()
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def seed_data(db):
    user = UserInfo(
        id=1,
        username="buyer",
        hashed_password="fake",
        role="staff",
    )
    merchant_user = UserInfo(
        id=2,
        username="merchant",
        hashed_password="fake",
        role="merchant",
    )
    merchant = MerchantInfo(
        id=1,
        user_id=2,
        merchant_name="Test Bento",
        campus="竹科",
        category="台式便當",
        rating=Decimal("4.8"),
        order_count=0,
        min_order=Decimal("0.00"),
        max_order_quantity=10,
        delivery_time="20-30 分鐘",
        tags=[],
        audit_status=1,
    )
    menu_1 = Menu(
        id=1,
        merchant_id=1,
        item_name="Chicken Bento",
        max_daily_quantity=10,
        price=Decimal("120.00"),
    )
    menu_2 = Menu(
        id=2,
        merchant_id=1,
        item_name="Pork Rice",
        max_daily_quantity=10,
        price=Decimal("110.00"),
    )
    db.add_all([user, merchant_user, merchant, menu_1, menu_2])


def service(db):
    return ReservationService(
        ReservationRepository(db),
        settings=Settings(
            reservation_processing_lease_seconds=30,
            reservation_db_polling_batch_size=25,
        ),
    )


def payload(
    *,
    quantity=1,
    items=None,
    service_date=None,
    pickup_slot="12:00-12:30",
):
    return ReservationCreate(
        user_id=1,
        merchant_id=1,
        service_date=service_date or date.today() + timedelta(days=1),
        pickup_slot=pickup_slot,
        pickup_option="SELF_PICKUP",
        items=items
        or [
            ReservationItemCreate(
                menu_item_id=1,
                quantity=quantity,
            )
        ],
    )


def outbox_payload(db):
    return db.query(ReservationOutboxEvent).one().payload


def capacity_slot(db, menu_item_id=1):
    return (
        db.query(ReservationCapacitySlot)
        .filter(ReservationCapacitySlot.menu_item_id == menu_item_id)
        .one()
    )


def add_capacity(db, *, menu_item_id=1, total_capacity=1):
    slot = ReservationCapacitySlot(
        merchant_id=1,
        menu_item_id=menu_item_id,
        service_date=date.today() + timedelta(days=1),
        pickup_slot="12:00-12:30",
        total_capacity=total_capacity,
        reserved_count=0,
    )
    db.add(slot)
    db.commit()
    return slot


def test_post_reservation_request_creates_pending_items_and_outbox(session_factory):
    db = session_factory()
    try:
        response = service(db).create_reservation_request(payload(quantity=2))
        assert response["status"] == "PENDING_RESERVATION"
        assert response["reservation_token"] == response["order_token"]

        reservation = db.query(ReservationRequest).one()
        assert reservation.status == "PENDING_RESERVATION"
        assert db.query(ReservationRequestItem).count() == 1
        event = db.query(ReservationOutboxEvent).one()
        assert event.event_type == "ReservationRequested"
        assert event.status == "PENDING"
    finally:
        db.close()


def test_same_user_idempotency_key_returns_same_reservation_without_duplicates(db):
    first = service(db).create_reservation_request(
        payload(),
        idempotency_key="same-key",
    )
    second = service(db).create_reservation_request(
        payload(),
        idempotency_key="same-key",
    )

    assert second["reservation_id"] == first["reservation_id"]
    assert db.query(ReservationRequest).count() == 1
    assert db.query(ReservationRequestItem).count() == 1
    assert db.query(ReservationOutboxEvent).count() == 1


def test_get_reservation_returns_pending_before_worker_processes_it(db):
    created = service(db).create_reservation_request(payload())

    result = service(db).get_reservation_by_token(created["order_token"])

    assert result["status"] == "PENDING_RESERVATION"
    assert result["reservation_token"] == created["order_token"]
    assert result["message"] == "Checking meal availability."


def test_worker_reserves_capacity_and_updates_to_reserved(db):
    service(db).create_reservation_request(payload(quantity=2))

    result = service(db).process_reservation_requested(outbox_payload(db))

    assert result == {"status": "RESERVED"}
    reservation = db.query(ReservationRequest).one()
    assert reservation.status == "RESERVED"
    assert capacity_slot(db).reserved_count == 2


def test_get_reservation_returns_reserved_after_worker_success(db):
    created = service(db).create_reservation_request(payload())
    service(db).process_reservation_requested(outbox_payload(db))

    result = service(db).get_reservation_by_token(created["order_token"])

    assert result["status"] == "RESERVED"
    assert result["message"] == "Meal capacity reserved successfully."
    assert result["pickup_number"] is None


def test_sold_out_path_does_not_oversell_capacity(db):
    add_capacity(db, total_capacity=1)
    service(db).create_reservation_request(payload(quantity=2))

    service(db).process_reservation_requested(outbox_payload(db))

    assert db.query(ReservationRequest).one().status == "SOLD_OUT"
    assert capacity_slot(db).reserved_count == 0
    assert capacity_slot(db).reserved_count <= capacity_slot(db).total_capacity


def test_multiple_item_reservation_is_atomic_when_one_item_unavailable(db):
    add_capacity(db, menu_item_id=1, total_capacity=10)
    add_capacity(db, menu_item_id=2, total_capacity=0)
    service(db).create_reservation_request(
        payload(
            items=[
                ReservationItemCreate(menu_item_id=1, quantity=1),
                ReservationItemCreate(menu_item_id=2, quantity=1),
            ]
        )
    )

    service(db).process_reservation_requested(outbox_payload(db))

    assert db.query(ReservationRequest).one().status == "SOLD_OUT"
    assert capacity_slot(db, menu_item_id=1).reserved_count == 0
    assert capacity_slot(db, menu_item_id=2).reserved_count == 0


def test_duplicate_event_delivery_does_not_reserve_capacity_twice(db):
    service(db).create_reservation_request(payload(quantity=2))
    event_payload = outbox_payload(db)

    service(db).process_reservation_requested(event_payload)
    service(db).process_reservation_requested(event_payload)

    assert db.query(ReservationRequest).one().status == "RESERVED"
    assert capacity_slot(db).reserved_count == 2


def test_concurrent_reservation_processing_never_exceeds_capacity(session_factory):
    setup_db = session_factory()
    try:
        add_capacity(setup_db, total_capacity=5)
        tokens = []
        for index in range(20):
            created = service(setup_db).create_reservation_request(
                payload(pickup_slot="12:00-12:30"),
                idempotency_key=f"key-{index}",
            )
            tokens.append(created["order_token"])
        event_payloads = [
            event.payload
            for event in setup_db.query(ReservationOutboxEvent)
            .order_by(ReservationOutboxEvent.id)
            .all()
        ]
    finally:
        setup_db.close()

    def process(event_payload):
        thread_db = session_factory()
        try:
            return service(thread_db).process_reservation_requested(event_payload)
        finally:
            thread_db.close()

    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(process, event_payloads))

    verify_db = session_factory()
    try:
        statuses = [
            status for (status,) in verify_db.query(ReservationRequest.status).all()
        ]
        slot = capacity_slot(verify_db)
        assert slot.reserved_count == 5
        assert slot.reserved_count <= slot.total_capacity
        assert statuses.count("RESERVED") == 5
        assert statuses.count("SOLD_OUT") == 15
    finally:
        verify_db.close()


def test_cancellation_before_processing_makes_worker_noop(db):
    created = service(db).create_reservation_request(payload())
    event_payload = outbox_payload(db)

    cancelled = service(db).cancel_reservation(created["order_token"])
    result = service(db).process_reservation_requested(event_payload)

    assert cancelled["status"] == "CANCELLED"
    assert result == {"status": "CANCELLED"}
    assert db.query(ReservationRequest).one().status == "CANCELLED"
    assert db.query(ReservationCapacitySlot).count() == 0


def test_cancellation_after_reserved_releases_capacity_once(db):
    created = service(db).create_reservation_request(payload(quantity=2))
    service(db).process_reservation_requested(outbox_payload(db))

    first = service(db).cancel_reservation(created["order_token"])
    second = service(db).cancel_reservation(created["order_token"])

    assert first["status"] == "CANCELLED"
    assert second["status"] == "CANCELLED"
    assert capacity_slot(db).reserved_count == 0


def test_invalid_service_dates_are_rejected(db):
    with pytest.raises(HTTPException) as past_error:
        service(db).create_reservation_request(
            payload(service_date=date.today() - timedelta(days=1))
        )
    with pytest.raises(HTTPException) as future_error:
        service(db).create_reservation_request(
            payload(service_date=date.today() + timedelta(days=8))
        )

    assert past_error.value.status_code == 422
    assert future_error.value.status_code == 422


def test_outbox_publish_failure_keeps_event_retryable_and_request_persisted(db):
    service(db).create_reservation_request(payload())

    result = ReservationOutboxPublisher(
        ReservationRepository(db),
        LocalReservationEventPublisher(fail=True),
        settings=Settings(reservation_outbox_max_retries=3),
    ).publish_once()

    event = db.query(ReservationOutboxEvent).one()
    assert result == {"published": 0, "failed": 1, "dead_lettered": 0}
    assert event.status == "FAILED_RETRYABLE"
    assert event.retry_count == 1
    assert db.query(ReservationRequest).count() == 1


def test_db_polling_fallback_processes_pending_reservations(db):
    service(db).create_reservation_request(payload())

    result = ReservationDbPollingWorker(
        ReservationRepository(db),
        service(db),
        settings=Settings(reservation_db_polling_batch_size=10),
    ).poll_once()

    assert result == {"processed": 1, "failed": 0}
    assert db.query(ReservationRequest).one().status == "RESERVED"
    assert capacity_slot(db).reserved_count == 1
