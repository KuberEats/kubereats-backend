from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from .models import Base, MerchantInfo, Menu, UserInfo, Order, Finance
import datetime
from decimal import Decimal

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if data already exists
    if db.query(UserInfo).first():
        db.close()
        return

    # Create dummy users
    staff = UserInfo(username="staff1", hashed_password="hashed_password", role="staff")
    staff2 = UserInfo(username="staff2", hashed_password="hashed_password", role="staff")
    merchant_user = UserInfo(username="merchant1", hashed_password="hashed_password", role="merchant")
    db.add_all([staff, staff2, merchant_user])
    db.commit()

    # Create dummy merchant
    merchant = MerchantInfo(merchant_name="Delicious Pizza")
    merchant2 = MerchantInfo(merchant_name="Sushi King")
    db.add_all([merchant, merchant2])
    db.commit()

    # Create dummy menu
    pizza = Menu(merchant_id=merchant.id, item_name="Pepperoni Pizza", price=Decimal("15.99"))
    coke = Menu(merchant_id=merchant.id, item_name="Coke", price=Decimal("2.50"))
    sushi = Menu(merchant_id=merchant2.id, item_name="Salmon Nigiri", price=Decimal("12.00"))
    db.add_all([pizza, coke, sushi])
    db.commit()

    # Create dummy orders
    # Merchant 1 orders
    o1 = Order(user_id=staff.id, total_amount=Decimal("31.98"), order_status=1, order_time=datetime.datetime.now() - datetime.timedelta(days=2))
    o2 = Order(user_id=staff.id, total_amount=Decimal("18.49"), order_status=1, order_time=datetime.datetime.now() - datetime.timedelta(days=1))
    o3 = Order(user_id=staff2.id, total_amount=Decimal("15.99"), order_status=0, order_time=datetime.datetime.now()) # Processing
    o4 = Order(user_id=staff.id, total_amount=Decimal("15.99"), order_status=2) # Cancelled
    
    # Merchant 2 orders
    o5 = Order(user_id=staff2.id, total_amount=Decimal("24.00"), order_status=1)
    
    db.add_all([o1, o2, o3, o4, o5])
    db.commit()

    # Create dummy finance records
    f1 = Finance(merchant_id=merchant.id, order_id=o1.id, settlement_amount=Decimal("28.00"), report_data={"status": "payout_done"})
    f2 = Finance(merchant_id=merchant.id, order_id=o2.id, settlement_amount=Decimal("16.00"), report_data={"status": "pending"})
    f3 = Finance(merchant_id=merchant2.id, order_id=o5.id, settlement_amount=Decimal("21.00"), report_data={"status": "payout_done"})
    
    db.add_all([f1, f2, f3])
    db.commit()

    db.close()

if __name__ == "__main__":
    init_db()
