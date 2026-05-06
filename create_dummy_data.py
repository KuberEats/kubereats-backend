from decimal import Decimal

from app.database import Base, engine, SessionLocal
from app.models.kubereats import Finance, Menu, MerchantInfo, Order, OrderItem, UserInfo


def seed():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        existing_user = db.query(UserInfo).filter(UserInfo.username == "admin").first()
        if existing_user:
            print("Dummy data already exists.")
            return

        merchant_1 = MerchantInfo(
            merchant_name="Tingwei Bento",
            audit_status=1,
        )

        merchant_2 = MerchantInfo(
            merchant_name="Kubereats Cafe",
            audit_status=1,
        )

        db.add_all([merchant_1, merchant_2])
        db.commit()
        db.refresh(merchant_1)
        db.refresh(merchant_2)

        menu_1 = Menu(
            merchant_id=merchant_1.id,
            item_name="Chicken Bento",
            max_daily_quantity=50,
            image_id="chicken-bento.jpg",
            price=Decimal("120.00"),
        )

        menu_2 = Menu(
            merchant_id=merchant_1.id,
            item_name="Pork Rice",
            max_daily_quantity=40,
            image_id="pork-rice.jpg",
            price=Decimal("110.00"),
        )

        menu_3 = Menu(
            merchant_id=merchant_2.id,
            item_name="Iced Latte",
            max_daily_quantity=80,
            image_id="iced-latte.jpg",
            price=Decimal("75.00"),
        )

        db.add_all([menu_1, menu_2, menu_3])
        db.commit()
        db.refresh(menu_1)
        db.refresh(menu_2)
        db.refresh(menu_3)

        user_1 = UserInfo(
            username="admin",
            hashed_password="fake_hashed_password",
            role="admin",
            history_records="Initial admin user",
        )

        user_2 = UserInfo(
            username="staff01",
            hashed_password="fake_hashed_password",
            role="staff",
            history_records="First staff user",
        )

        db.add_all([user_1, user_2])
        db.commit()
        db.refresh(user_1)
        db.refresh(user_2)

        order_1 = Order(
            user_id=user_1.id,
            total_amount=Decimal("120.00"),
            order_status=1,
        )

        order_2 = Order(
            user_id=user_2.id,
            total_amount=Decimal("185.00"),
            order_status=0,
        )

        db.add_all([order_1, order_2])
        db.commit()
        db.refresh(order_1)
        db.refresh(order_2)

        order_item_1 = OrderItem(
            order_id=order_1.id,
            menu_id=menu_1.id,
            quantity=1,
            unit_price=Decimal("120.00"),
            subtotal=Decimal("120.00"),
        )

        order_item_2 = OrderItem(
            order_id=order_2.id,
            menu_id=menu_2.id,
            quantity=1,
            unit_price=Decimal("110.00"),
            subtotal=Decimal("110.00"),
        )

        order_item_3 = OrderItem(
            order_id=order_2.id,
            menu_id=menu_3.id,
            quantity=1,
            unit_price=Decimal("75.00"),
            subtotal=Decimal("75.00"),
        )

        db.add_all([order_item_1, order_item_2, order_item_3])

        finance_1 = Finance(
            merchant_id=merchant_1.id,
            order_id=order_1.id,
            report_data={
                "items": [
                    {
                        "name": "Chicken Bento",
                        "quantity": 1,
                        "price": 120,
                    }
                ],
                "payment_method": "cash",
            },
            settlement_amount=Decimal("108.00"),
        )

        finance_2 = Finance(
            merchant_id=merchant_2.id,
            order_id=order_2.id,
            report_data={
                "items": [
                    {
                        "name": "Iced Latte",
                        "quantity": 1,
                        "price": 75,
                    },
                    {
                        "name": "Pork Rice",
                        "quantity": 1,
                        "price": 110,
                    },
                ],
                "payment_method": "credit_card",
            },
            settlement_amount=Decimal("166.50"),
        )

        db.add_all([finance_1, finance_2])
        db.commit()

        print("Dummy data created successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
