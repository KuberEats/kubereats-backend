from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.kubereats import Menu, MerchantInfo, Order, OrderItem


class MerchantRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Merchant ──

    def get_by_id(self, merchant_id: int) -> MerchantInfo | None:
        return self.db.query(MerchantInfo).filter(MerchantInfo.id == merchant_id).first()

    def get_by_user_id(self, user_id: int) -> MerchantInfo | None:
        return self.db.query(MerchantInfo).filter(MerchantInfo.user_id == user_id).first()

    def create_merchant(self, merchant: MerchantInfo) -> MerchantInfo:
        self.db.add(merchant)
        self.db.flush()
        return merchant

    def update_merchant(self, merchant: MerchantInfo, data: dict) -> MerchantInfo:
        for key, value in data.items():
            if value is not None:
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
            if value is not None:
                setattr(menu, key, value)
        self.db.flush()
        return menu

    def delete_menu(self, menu: Menu) -> None:
        self.db.delete(menu)
        self.db.flush()

    # ── Order Summary ──

    def get_today_order_summary(self, merchant_id: int, target_date: date):
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
                func.date(Order.order_time) == target_date,
                Order.order_status != 2,  # exclude cancelled
            )
            .group_by(OrderItem.menu_id, Menu.item_name)
            .all()
        )
        return results

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
