from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.repo.menu_repo import MenuRepository
from app.repo.order_repo import OrderRepository
from app.schemas.order import (
    OrderCreate,
    OrderHistorySortKey,
    OrderResponse,
    OrderStatusUpdate,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


def get_order_service(db: Session = Depends(get_db)):
    return OrderService(
        order_repo=OrderRepository(db),
        menu_repo=MenuRepository(db),
    )


@router.post("", response_model=OrderResponse, status_code=201)
def create_order(
    order_data: OrderCreate,
    service: OrderService = Depends(get_order_service),
):
    return service.create_order(order_data)


@router.get("", response_model=list[OrderResponse])
def list_orders(
    user_id: int = Query(alias="userId"),
    sort_by: OrderHistorySortKey = Query(default="time", alias="sortBy"),
    service: OrderService = Depends(get_order_service),
):
    return service.list_orders_by_user(user_id, sort_by)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_by_id(
    order_id: int,
    service: OrderService = Depends(get_order_service),
):
    return service.get_order_by_id(order_id)


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    service: OrderService = Depends(get_order_service),
):
    return service.update_order_status(order_id, status_data.order_status)
