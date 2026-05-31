from datetime import date

from fastapi import HTTPException, status

from app.models.kubereats import Menu, MerchantInfo
from app.repo.merchant_repo import MerchantRepository
from app.schemas.merchant import (
    MerchantApplyRequest,
    MerchantSortKey,
    MerchantUpdateRequest,
    MenuCreateRequest,
    MenuUpdateRequest,
)


class MerchantService:
    def __init__(self, merchant_repo: MerchantRepository):
        self.merchant_repo = merchant_repo

    # ── Merchant ──

    def apply(self, user_id: int, data: MerchantApplyRequest) -> MerchantInfo:
        existing = self.merchant_repo.get_by_user_id(user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Merchant application already exists",
            )

        merchant = self.merchant_repo.create_merchant(
            MerchantInfo(
                user_id=user_id,
                merchant_name=data.merchant_name,
                campus=data.campus,
                category=data.category,
                min_order=data.min_order,
                max_order_quantity=data.max_order_quantity,
                delivery_time=data.delivery_time,
                tags=data.tags,
                audit_status=0,
            )
        )
        self.merchant_repo.commit()
        return merchant

    def get_my_merchant(self, user_id: int) -> MerchantInfo:
        merchant = self.merchant_repo.get_by_user_id(user_id)
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found, please apply first",
            )
        return merchant

    def update_my_merchant(
        self, user_id: int, data: MerchantUpdateRequest
    ) -> MerchantInfo:
        merchant = self.get_my_merchant(user_id)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )
        self.merchant_repo.update_merchant(merchant, update_data)
        self.merchant_repo.commit()
        return merchant

    # ── Public Catalog ──

    def list_public_merchants(
        self,
        campus: str,
        target_date: date,
        sort_by: MerchantSortKey,
    ) -> list[MerchantInfo]:
        merchants = self.merchant_repo.list_approved_by_campus(campus)

        if sort_by == "people":
            return sorted(
                merchants, key=lambda merchant: merchant.order_count, reverse=True
            )

        if sort_by == "popular":
            return sorted(merchants, key=lambda merchant: merchant.rating, reverse=True)

        return sorted(
            merchants,
            key=lambda merchant: float(merchant.rating) * 20 + merchant.order_count,
            reverse=True,
        )

    def get_public_merchant_detail(self, merchant_id: int) -> MerchantInfo:
        merchant = self.merchant_repo.get_approved_by_id(merchant_id)
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found",
            )
        return merchant

    def list_public_menu_items(self, merchant_id: int) -> list[Menu]:
        merchant = self.get_public_merchant_detail(merchant_id)
        return self.merchant_repo.list_menus_by_merchant(merchant.id)

    # ── Menu ──

    def create_menu_item(self, user_id: int, data: MenuCreateRequest) -> Menu:
        merchant = self._get_approved_merchant(user_id)
        menu = self.merchant_repo.create_menu(
            Menu(
                merchant_id=merchant.id,
                item_name=data.item_name,
                price=data.price,
                max_daily_quantity=data.max_daily_quantity,
                image_id=data.image_id,
            )
        )
        self.merchant_repo.commit()
        return menu

    def list_menu_items(self, user_id: int) -> list[Menu]:
        merchant = self.get_my_merchant(user_id)
        return self.merchant_repo.list_menus_by_merchant(merchant.id)

    def update_menu_item(
        self, user_id: int, menu_id: int, data: MenuUpdateRequest
    ) -> Menu:
        merchant = self._get_approved_merchant(user_id)
        menu = self._get_own_menu(merchant.id, menu_id)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )
        self.merchant_repo.update_menu(menu, update_data)
        self.merchant_repo.commit()
        return menu

    def delete_menu_item(self, user_id: int, menu_id: int) -> None:
        merchant = self._get_approved_merchant(user_id)
        menu = self._get_own_menu(merchant.id, menu_id)
        self.merchant_repo.delete_menu(menu)
        self.merchant_repo.commit()

    # ── Order Summary ──

    def get_today_order_summary(self, user_id: int) -> dict:
        merchant = self._get_approved_merchant(user_id)
        today = date.today()
        results = self.merchant_repo.get_today_order_summary(merchant.id, today)

        items = [
            {
                "menu_id": row.menu_id,
                "item_name": row.item_name,
                "total_quantity": int(row.total_quantity),
                "total_amount": float(row.total_amount),
            }
            for row in results
        ]

        return {
            "date": today.isoformat(),
            "total_orders": sum(item["total_quantity"] for item in items),
            "total_amount": sum(item["total_amount"] for item in items),
            "items": items,
        }

    def confirm_today_orders(self, user_id: int) -> dict:
        merchant = self._get_approved_merchant(user_id)
        today = date.today()
        orders = self.merchant_repo.get_today_pending_orders(merchant.id, today)
        for order in orders:
            order.order_status = 1
        self.merchant_repo.commit()
        return {"confirmed_count": len(orders)}

    # ── Helpers ──

    def _get_approved_merchant(self, user_id: int) -> MerchantInfo:
        merchant = self.get_my_merchant(user_id)
        if merchant.audit_status != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Merchant is not approved yet",
            )
        return merchant

    def _get_own_menu(self, merchant_id: int, menu_id: int) -> Menu:
        menu = self.merchant_repo.get_menu_by_id(menu_id)
        if not menu or menu.merchant_id != merchant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found",
            )
        return menu
