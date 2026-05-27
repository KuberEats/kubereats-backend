from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.repo.menu_repo import MenuRepository
from app.repo.order_repo import OrderRepository
from app.schemas.order import OrderReleaseTaskRequest
from app.services.order_service import OrderService

router = APIRouter(prefix="/internal/tasks", tags=["Internal Tasks"])


def get_order_service(db: Session = Depends(get_db)):
    return OrderService(
        order_repo=OrderRepository(db),
        menu_repo=MenuRepository(db),
    )


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
    if settings.internal_task_auth_enabled:
        if not settings.internal_task_token:
            raise HTTPException(
                status_code=500,
                detail="Internal task token is not configured",
            )
        if x_internal_task_token != settings.internal_task_token:
            raise HTTPException(status_code=401, detail="Invalid internal task token")

    return service.release_scheduled_order(
        task_data.order_id,
        task_key=task_data.task_key,
        correlation_id=task_data.correlation_id,
    )
