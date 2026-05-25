from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload

from app.models.kubereats import Finance, MenuDailyCapacity, Order, OrderItem, UserInfo


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int):
        return self.db.query(UserInfo).filter(UserInfo.id == user_id).first()

    def create_order(self, order: Order):
        self.db.add(order)
        self.db.flush()
        return order

    def create_order_items(self, order_items: list[OrderItem]):
        self.db.add_all(order_items)
        self.db.flush()
        return order_items

    def create_finance_records(self, finance_records: list[Finance]):
        self.db.add_all(finance_records)
        self.db.flush()
        return finance_records

    def get_by_id(self, order_id: int):
        return (
            self.db.query(Order)
            .options(
                joinedload(Order.items).joinedload(OrderItem.menu),
                joinedload(Order.finance_records).joinedload(Finance.merchant),
            )
            .filter(Order.id == order_id)
            .first()
        )

    def list_by_user_id(self, user_id: int):
        return (
            self.db.query(Order)
            .options(
                joinedload(Order.items).joinedload(OrderItem.menu),
                joinedload(Order.finance_records).joinedload(Finance.merchant),
            )
            .filter(Order.user_id == user_id)
            .order_by(Order.order_time.desc())
            .all()
        )

    def ensure_menu_daily_capacities(self, menus, target_date):
        rows = [
            {
                "menu_id": menu.id,
                "target_date": target_date,
                "max_quantity": menu.max_daily_quantity,
                "remaining_quantity": menu.max_daily_quantity,
            }
            for menu in menus
        ]

        if not rows:
            return

        statement = insert(MenuDailyCapacity).values(rows)
        statement = statement.on_conflict_do_nothing(
            index_elements=["menu_id", "target_date"]
        )
        self.db.execute(statement)
        self.db.flush()

    def deduct_menu_daily_capacity(self, menu_id: int, target_date, quantity: int):
        statement = (
            update(MenuDailyCapacity)
            .where(
                MenuDailyCapacity.menu_id == menu_id,
                MenuDailyCapacity.target_date == target_date,
                MenuDailyCapacity.remaining_quantity >= quantity,
            )
            .values(remaining_quantity=MenuDailyCapacity.remaining_quantity - quantity)
        )

        result = self.db.execute(statement)
        self.db.flush()
        return result.rowcount == 1

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    def refresh(self, instance):
        self.db.refresh(instance)
