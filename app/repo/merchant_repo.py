from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.kubereats import Menu, MerchantInfo, Order, OrderItem


class MerchantRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Merchant ──

    def get_by_id(self, merchant_id: int) -> MerchantInfo | None:
        return (
            self.db.query(MerchantInfo).filter(MerchantInfo.id == merchant_id).first()
        )

    def list_approved_by_campus(self, campus: str) -> list[MerchantInfo]:
        return (
            self.db.query(MerchantInfo)
            .filter(
                MerchantInfo.campus == campus,
                MerchantInfo.audit_status == 1,
            )
            .all()
        )

    def get_approved_by_id(self, merchant_id: int) -> MerchantInfo | None:
        return (
            self.db.query(MerchantInfo)
            .options(joinedload(MerchantInfo.menus))
            .filter(
                MerchantInfo.id == merchant_id,
                MerchantInfo.audit_status == 1,
            )
            .first()
        )

    def get_by_user_id(self, user_id: int) -> MerchantInfo | None:
        return (
            self.db.query(MerchantInfo).filter(MerchantInfo.user_id == user_id).first()
        )

    def create_merchant(self, merchant: MerchantInfo) -> MerchantInfo:
        self.db.add(merchant)
        self.db.flush()
        return merchant

    def update_merchant(self, merchant: MerchantInfo, data: dict) -> MerchantInfo:
        for key, value in data.items():
            setattr(merchant, key, value)
        self.db.flush()
        return merchant

    # ── Menu ──

    def get_menu_by_id(self, menu_id: int) -> Menu | None:
        return self.db.query(Menu).filter(Menu.id == menu_id).first()

    def list_menus_by_merchant(self, merchant_id: int) -> list[Menu]:
        return self.db.query(Menu).filter(Menu.merchant_id == merchant_id).all()

    def create_menu(self, menu: Menu) -> Menu:
        self.db.add(menu)
        self.db.flush()
        return menu

    def update_menu(self, menu: Menu, data: dict) -> Menu:
        for key, value in data.items():
            setattr(menu, key, value)
        self.db.flush()
        return menu

    def delete_menu(self, menu: Menu) -> None:
        self.db.delete(menu)
        self.db.flush()

    # ── Order Summary ──

    def get_today_order_summary(
        self, merchant_id: int, day_start: datetime, day_end: datetime
    ):
        results = (
            self.db.query(
                OrderItem.menu_id,
                Menu.item_name,
                func.sum(OrderItem.quantity).label("total_quantity"),
                func.sum(OrderItem.subtotal).label("total_amount"),
            )
            .join(Menu, OrderItem.menu_id == Menu.id)
            .join(Order, OrderItem.order_id == Order.id)
            .filter(
                Menu.merchant_id == merchant_id,
                Order.order_time >= day_start,
                Order.order_time < day_end,
                Order.order_status != 2,
            )
            .group_by(OrderItem.menu_id, Menu.item_name)
            .all()
        )
        return results

    def get_today_order_user_ids(
        self, merchant_id: int, day_start: datetime, day_end: datetime
    ) -> list[int]:
        results = (
            self.db.query(Order.id, Order.user_id)
            .join(OrderItem, Order.id == OrderItem.order_id)
            .join(Menu, OrderItem.menu_id == Menu.id)
            .filter(
                Menu.merchant_id == merchant_id,
                Order.order_time >= day_start,
                Order.order_time < day_end,
                Order.order_status != 2,
            )
            .group_by(Order.id, Order.user_id)
            .all()
        )
        return [row.user_id for row in results]

    def get_today_pending_orders(
        self, merchant_id: int, day_start: datetime, day_end: datetime
    ) -> list[Order]:
        return (
            self.db.query(Order)
            .join(OrderItem, Order.id == OrderItem.order_id)
            .join(Menu, OrderItem.menu_id == Menu.id)
            .filter(
                Menu.merchant_id == merchant_id,
                Order.order_time >= day_start,
                Order.order_time < day_end,
                Order.order_status == 0,
            )
            .distinct()
            .all()
        )

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
