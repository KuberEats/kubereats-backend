from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from .models import Base, MerchantInfo, Menu, UserInfo, Order, Finance, OrderItem
import datetime
from decimal import Decimal

def init_db():
    # In development, we drop and recreate to ensure schema matches
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Create dummy users
    staff = UserInfo(username="staff1", hashed_password="hashed_password", role="staff")
    staff2 = UserInfo(username="staff2", hashed_password="hashed_password", role="staff")
    merchant_user1 = UserInfo(username="merchant_user1", hashed_password="hashed_password", role="merchant")
    merchant_user2 = UserInfo(username="merchant_user2", hashed_password="hashed_password", role="merchant")
    db.add_all([staff, staff2, merchant_user1, merchant_user2])
    db.commit()

    # Create dummy merchant
    merchant = MerchantInfo(
        user_id=merchant_user1.id,
        merchant_name="Delicious Pizza",
        campus="Main",
        category="Pizza",
        delivery_time="30-45 min",
        min_order=Decimal("10.00")
    )
    merchant2 = MerchantInfo(
        user_id=merchant_user2.id,
        merchant_name="Sushi King",
        campus="East",
        category="Japanese",
        delivery_time="20-30 min",
        min_order=Decimal("15.00")
    )
    db.add_all([merchant, merchant2])
    db.commit()

    # Create dummy menu
    pizza = Menu(merchant_id=merchant.id, item_name="Pepperoni Pizza", price=Decimal("15.99"))
    coke = Menu(merchant_id=merchant.id, item_name="Coke", price=Decimal("2.50"))
    sushi = Menu(merchant_id=merchant2.id, item_name="Salmon Nigiri", price=Decimal("12.00"))
    db.add_all([pizza, coke, sushi])
    db.commit()

    # Create dummy orders
    # Order 1: Pepperoni Pizza + Coke
    o1 = Order(user_id=staff.id, total_amount=Decimal("18.49"), order_status=1, order_time=datetime.datetime.now() - datetime.timedelta(days=2))
    db.add(o1)
    db.commit()
    
    item1 = OrderItem(order_id=o1.id, menu_id=pizza.id, quantity=1, unit_price=pizza.price, subtotal=pizza.price)
    item2 = OrderItem(order_id=o1.id, menu_id=coke.id, quantity=1, unit_price=coke.price, subtotal=coke.price)
    db.add_all([item1, item2])
    db.commit()

    # Order 2: Sushi
    o2 = Order(user_id=staff2.id, total_amount=Decimal("24.00"), order_status=1, order_time=datetime.datetime.now() - datetime.timedelta(days=1))
    db.add(o2)
    db.commit()
    
    item3 = OrderItem(order_id=o2.id, menu_id=sushi.id, quantity=2, unit_price=sushi.price, subtotal=Decimal("24.00"))
    db.add(item3)
    db.commit()

    # Create dummy finance records
    f1 = Finance(merchant_id=merchant.id, order_id=o1.id, settlement_amount=Decimal("16.50"), report_data={"status": "payout_done"})
    f2 = Finance(merchant_id=merchant2.id, order_id=o2.id, settlement_amount=Decimal("21.00"), report_data={"status": "payout_done"})
    
    db.add_all([f1, f2])
    db.commit()

    db.close()

if __name__ == "__main__":
    init_db()
