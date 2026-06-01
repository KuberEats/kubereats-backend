from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.repo.menu_repo import MenuRepository
from app.repo.order_repo import OrderRepository
from app.repo.reservation_repo import ReservationRepository
from app.schemas.order import OrderReleaseTaskRequest
from app.schemas.reservation import ReservationRequestedTaskRequest
from app.services.order_service import OrderService
from app.services.reservation_service import ReservationService

router = APIRouter(prefix="/internal/tasks", tags=["Internal Tasks"])


def get_order_service(db: Session = Depends(get_db)):
    return OrderService(
        order_repo=OrderRepository(db),
        menu_repo=MenuRepository(db),
    )


def get_reservation_service(db: Session = Depends(get_db)):
    return ReservationService(
        reservation_repo=ReservationRepository(db),
    )


def verify_internal_task_token(
    x_internal_task_token: str | None,
    settings: Settings,
):
    if settings.internal_task_auth_enabled:
        if not settings.internal_task_token:
            raise HTTPException(
                status_code=500,
                detail="Internal task token is not configured",
            )
        if x_internal_task_token != settings.internal_task_token:
            raise HTTPException(status_code=401, detail="Invalid internal task token")


@router.post("/orders/release", include_in_schema=False)
def release_scheduled_order(
    task_data: OrderReleaseTaskRequest,
    x_internal_task_token: str | None = Header(
        default=None,
        alias="X-Internal-Task-Token",
    ),
    settings: Settings = Depends(get_settings),
    service: OrderService = Depends(get_order_service),
):
    verify_internal_task_token(x_internal_task_token, settings)

    return service.release_scheduled_order(
        task_data.order_id,
        task_key=task_data.task_key,
        correlation_id=task_data.correlation_id,
    )


@router.post("/reservations/process", include_in_schema=False)
def process_reservation_requested(
    task_data: ReservationRequestedTaskRequest,
    x_internal_task_token: str | None = Header(
        default=None,
        alias="X-Internal-Task-Token",
    ),
    settings: Settings = Depends(get_settings),
    service: ReservationService = Depends(get_reservation_service),
):
    verify_internal_task_token(x_internal_task_token, settings)

    return service.process_reservation_requested(task_data.model_dump())
