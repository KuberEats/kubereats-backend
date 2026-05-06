from sqlalchemy.orm import Session, joinedload

from app.models.kubereats import Finance, Order, OrderItem, UserInfo


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

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    def refresh(self, instance):
        self.db.refresh(instance)
