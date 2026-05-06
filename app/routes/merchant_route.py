from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.repo.menu_repo import MenuRepository
from app.repo.merchant_repo import MerchantRepository
from app.schemas.menu import MenuItemResponse
from app.schemas.merchant import Campus, MerchantDetail, MerchantListItem, MerchantSortKey
from app.services.menu_service import MenuService
from app.services.merchant_service import MerchantService

router = APIRouter(prefix="/merchants", tags=["Merchants"])


def get_merchant_service(db: Session = Depends(get_db)):
    return MerchantService(MerchantRepository(db))


def get_menu_service(db: Session = Depends(get_db)):
    return MenuService(
        menu_repo=MenuRepository(db),
        merchant_repo=MerchantRepository(db),
    )


@router.get("", response_model=list[MerchantListItem])
def list_restaurants_for_order_page(
    campus: Campus,
    date: date,
    sort_by: MerchantSortKey = Query(default="recommend"),
    service: MerchantService = Depends(get_merchant_service),
):
    return service.list_restaurants_for_order_page(campus, date, sort_by)


@router.get("/{merchant_id}", response_model=MerchantDetail)
def get_merchant_detail(
    merchant_id: int,
    service: MerchantService = Depends(get_merchant_service),
):
    return service.get_merchant_detail(merchant_id)


@router.get("/{merchant_id}/menus", response_model=list[MenuItemResponse])
def list_menu_items(
    merchant_id: int,
    service: MenuService = Depends(get_menu_service),
):
    return service.list_menu_items(merchant_id)
