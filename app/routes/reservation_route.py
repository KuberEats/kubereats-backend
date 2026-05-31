from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.repo.reservation_repo import ReservationRepository
from app.schemas.reservation import (
    ReservationAcceptedResponse,
    ReservationCreate,
    ReservationResponse,
)
from app.services.reservation_service import ReservationService

router = APIRouter(prefix="/reservation-requests", tags=["Reservations"])


def get_reservation_service(db: Session = Depends(get_db)):
    return ReservationService(
        reservation_repo=ReservationRepository(db),
    )


@router.post("", response_model=ReservationAcceptedResponse, status_code=202)
def create_reservation_request(
    reservation_data: ReservationCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: ReservationService = Depends(get_reservation_service),
):
    return service.create_reservation_request(
        reservation_data,
        idempotency_key=idempotency_key,
    )


@router.get("/{order_token}", response_model=ReservationResponse)
def get_reservation_request(
    order_token: str,
    service: ReservationService = Depends(get_reservation_service),
):
    return service.get_reservation_by_token(order_token)


@router.post("/{order_token}/cancel", response_model=ReservationResponse)
def cancel_reservation_request(
    order_token: str,
    service: ReservationService = Depends(get_reservation_service),
):
    return service.cancel_reservation(order_token)
