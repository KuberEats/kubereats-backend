from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database import get_db
from app.models.kubereats import UserInfo
from app.repo.merchant_repo import MerchantRepository
from app.schemas.merchant import (
    MerchantApplyRequest,
    MerchantResponse,
    MerchantUpdateRequest,
    MenuCreateRequest,
    MenuResponse,
    MenuUpdateRequest,
    TodayOrderSummaryResponse,
)
from app.services.merchant_service import MerchantService

router = APIRouter(prefix="/merchants", tags=["Merchants"])

merchant_role = require_role("merchant")


def get_merchant_service(db: Session = Depends(get_db)):
    return MerchantService(merchant_repo=MerchantRepository(db))


@router.post("/apply", response_model=MerchantResponse, status_code=201)
def apply_merchant(
    data: MerchantApplyRequest,
    current_user: UserInfo = Depends(merchant_role),
    service: MerchantService = Depends(get_merchant_service),
):
    return service.apply(current_user.id, data)


@router.get("/me", response_model=MerchantResponse)
def get_my_merchant(
    current_user: UserInfo = Depends(merchant_role),
    service: MerchantService = Depends(get_merchant_service),
):
    return service.get_my_merchant(current_user.id)


@router.put("/me", response_model=MerchantResponse)
def update_my_merchant(
    data: MerchantUpdateRequest,
    current_user: UserInfo = Depends(merchant_role),
    service: MerchantService = Depends(get_merchant_service),
):
    return service.update_my_merchant(current_user.id, data)


@router.post("/menu", response_model=MenuResponse, status_code=201)
def create_menu_item(
    data: MenuCreateRequest,
    current_user: UserInfo = Depends(merchant_role),
    service: MerchantService = Depends(get_merchant_service),
):
    return service.create_menu_item(current_user.id, data)


@router.get("/menu", response_model=list[MenuResponse])
def list_menu_items(
    current_user: UserInfo = Depends(merchant_role),
    service: MerchantService = Depends(get_merchant_service),
):
    return service.list_menu_items(current_user.id)


@router.put("/menu/{menu_id}", response_model=MenuResponse)
def update_menu_item(
    menu_id: int,
    data: MenuUpdateRequest,
    current_user: UserInfo = Depends(merchant_role),
    service: MerchantService = Depends(get_merchant_service),
):
    return service.update_menu_item(current_user.id, menu_id, data)


@router.delete("/menu/{menu_id}", status_code=204)
def delete_menu_item(
    menu_id: int,
    current_user: UserInfo = Depends(merchant_role),
    service: MerchantService = Depends(get_merchant_service),
):
    service.delete_menu_item(current_user.id, menu_id)


@router.get("/orders/today", response_model=TodayOrderSummaryResponse)
def get_today_orders(
    current_user: UserInfo = Depends(merchant_role),
    service: MerchantService = Depends(get_merchant_service),
):
    return service.get_today_order_summary(current_user.id)
