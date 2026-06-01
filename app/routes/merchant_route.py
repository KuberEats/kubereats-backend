from datetime import date as Date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.core.metrics import (
    merchant_apply_total,
    merchant_menu_created_total,
    merchant_menu_deleted_total,
    merchant_orders_confirmed_total,
)
from app.database import get_db
from app.models.kubereats import UserInfo
from app.repo.merchant_repo import MerchantRepository
from app.schemas.merchant import (
    MerchantApplyRequest,
    MerchantSortKey,
    PublicMerchantDetail,
    PublicMerchantListItem,
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
    result = service.apply(current_user.id, data)
    merchant_apply_total.inc()
    return result


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
    result = service.create_menu_item(current_user.id, data)
    merchant_menu_created_total.inc()
    return result


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
    merchant_menu_deleted_total.inc()


@router.get("/orders/today", response_model=TodayOrderSummaryResponse)
def get_today_orders(
    current_user: UserInfo = Depends(merchant_role),
    service: MerchantService = Depends(get_merchant_service),
):
    return service.get_today_order_summary(current_user.id)


@router.post("/orders/confirm-today")
def confirm_today_orders(
    current_user: UserInfo = Depends(merchant_role),
    service: MerchantService = Depends(get_merchant_service),
):
    result = service.confirm_today_orders(current_user.id)
    merchant_orders_confirmed_total.inc()
    return result


@router.get("", response_model=list[PublicMerchantListItem])
def list_public_merchants(
    campus: str,
    date: Date | None = None,
    sort_by: MerchantSortKey = Query(default="recommend"),
    service: MerchantService = Depends(get_merchant_service),
):
    return service.list_public_merchants(campus, date or Date.today(), sort_by)


@router.get("/{merchant_id}", response_model=PublicMerchantDetail)
def get_public_merchant_detail(
    merchant_id: int,
    service: MerchantService = Depends(get_merchant_service),
):
    return service.get_public_merchant_detail(merchant_id)


@router.get("/{merchant_id}/menus", response_model=list[MenuResponse])
def list_public_menu_items(
    merchant_id: int,
    service: MerchantService = Depends(get_merchant_service),
):
    return service.list_public_menu_items(merchant_id)
