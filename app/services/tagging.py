from sqlalchemy.orm import Session
from ..models import UserInfo, Order, Tag, user_tags, Finance
from sqlalchemy import func
from ..metrics import classify_tag, user_tags_assigned

class TaggingService:
    def __init__(self, db: Session):
        self.db = db

    def get_tags_by_user_id(self, user_id: int):
        user = self.db.query(UserInfo).filter(UserInfo.id == user_id).first()
        if not user:
            return []
        return [tag.name for tag in user.tags]

    def update_user_tags_based_on_orders(self, user_id: int):
        """
        Sync staff ID to tag and update based on order history.
        """
        user = self.db.query(UserInfo).filter(UserInfo.id == user_id).first()
        if not user:
            return
        
        # 1. Handle "把員工編號轉成標籤"
        if user.role == "staff":
            staff_tag_name = f"STAFF-{user.id:03d}"
            self._add_tag_to_user(user, staff_tag_name)

        # 2. Logic based on orders
        order_count = self.db.query(func.count(Order.id)).filter(Order.user_id == user_id).scalar()
        total_spent = self.db.query(func.sum(Order.total_amount)).filter(Order.user_id == user_id).scalar() or 0
        
        if order_count > 10:
            self._add_tag_to_user(user, "Frequent Buyer")
        if total_spent > 1000:
            self._add_tag_to_user(user, "Big Spender")
            
        self.db.commit()
        return [tag.name for tag in user.tags]

    def _add_tag_to_user(self, user: UserInfo, tag_name: str):
        tag = self.db.query(Tag).filter(Tag.name == tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            self.db.add(tag)
            self.db.flush()
        
        if tag not in user.tags:
            user.tags.append(tag)
            user_tags_assigned.inc(classify_tag(tag_name))

class MerchantService:
    def __init__(self, db: Session):
        self.db = db

    def get_income_status(self, merchant_id: int):
        records = self.db.query(Finance).filter(Finance.merchant_id == merchant_id).all()
        total_income = sum(r.settlement_amount for r in records if r.settlement_amount)
        order_count = len(records)
        return {"total_income": float(total_income), "order_count": order_count}

class StaffService:
    def __init__(self, db: Session):
        self.db = db

    def get_expenses(self, user_id: int):
        orders = self.db.query(Order).filter(Order.user_id == user_id, Order.order_status == 1).all()
        total_expense = sum(o.total_amount for o in orders)
        return {"total_expense": float(total_expense), "order_count": len(orders)}
