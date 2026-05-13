from sqlalchemy.orm import Session
from ..models import UserInfo, Order, Tag, user_tags
from sqlalchemy import func

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
        Example logic: 
        - If total orders > 10 -> "Frequent Buyer"
        - If total amount > 1000 -> "Big Spender"
        """
        user = self.db.query(UserInfo).filter(UserInfo.id == user_id).first()
        if not user:
            return
        
        order_count = self.db.query(func.count(Order.id)).filter(Order.user_id == user_id).scalar()
        total_spent = self.db.query(func.sum(Order.total_amount)).filter(Order.user_id == user_id).scalar() or 0
        
        new_tag_names = []
        if order_count > 10:
            new_tag_names.append("Frequent Buyer")
        if total_spent > 1000:
            new_tag_names.append("Big Spender")
        if user.role == "staff":
            new_tag_names.append("Internal Staff")
            
        # Update tags in DB
        for tag_name in new_tag_names:
            tag = self.db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                self.db.add(tag)
                self.db.flush()
            
            if tag not in user.tags:
                user.tags.append(tag)
        
        self.db.commit()
        return [tag.name for tag in user.tags]

class MerchantService:
    def __init__(self, db: Session):
        self.db = db

    def get_income_status(self, merchant_id: int):
        # Dummy logic: sum of orders for this merchant's menu items
        # In this schema, Order is not directly linked to Merchant, 
        # but Finance links Merchant and Order.
        from ..models import Finance
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
