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
            merchant_name="阿明便當",
            campus="竹科",
            category="台式便當",
            rating=Decimal("4.8"),
            order_count=126,
            min_order=Decimal("80.00"),
            delivery_time="25-35 分鐘",
            tags=["熱賣", "雞腿飯", "可團訂"],
            audit_status=1,
        )

        merchant_2 = MerchantInfo(
            merchant_name="小森咖哩",
            campus="竹科",
            category="日式咖哩",
            rating=Decimal("4.6"),
            order_count=92,
            min_order=Decimal("120.00"),
            delivery_time="30-40 分鐘",
            tags=["人氣", "咖哩飯", "今日可訂"],
            audit_status=1,
        )

        merchant_3 = MerchantInfo(
            merchant_name="清爽蔬食盒",
            campus="竹科",
            category="健康餐盒",
            rating=Decimal("4.7"),
            order_count=76,
            min_order=Decimal("100.00"),
            delivery_time="20-30 分鐘",
            tags=["低卡", "蔬食", "午餐推薦"],
            audit_status=1,
        )

        merchant_4 = MerchantInfo(
            merchant_name="南科牛肉麵",
            campus="南科",
            category="麵食",
            rating=Decimal("4.5"),
            order_count=88,
            min_order=Decimal("90.00"),
            delivery_time="30-45 分鐘",
            tags=["牛肉麵", "湯麵", "多人訂購"],
            audit_status=1,
        )

        merchant_5 = MerchantInfo(
            merchant_name="中科港式燒臘",
            campus="中科",
            category="港式",
            rating=Decimal("4.4"),
            order_count=104,
            min_order=Decimal("95.00"),
            delivery_time="25-35 分鐘",
            tags=["燒臘", "三寶飯", "熱門"],
            audit_status=1,
        )

        db.add_all([merchant_1, merchant_2, merchant_3, merchant_4, merchant_5])
        db.commit()
        for merchant in [merchant_1, merchant_2, merchant_3, merchant_4, merchant_5]:
            db.refresh(merchant)

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
            item_name="起司豬排咖哩",
            max_daily_quantity=80,
            image_id="pork-curry.jpg",
            price=Decimal("150.00"),
        )

        menu_4 = Menu(
            merchant_id=merchant_3.id,
            item_name="舒肥雞胸餐盒",
            max_daily_quantity=35,
            image_id="chicken-salad-box.jpg",
            price=Decimal("130.00"),
        )

        menu_5 = Menu(
            merchant_id=merchant_4.id,
            item_name="紅燒牛肉麵",
            max_daily_quantity=45,
            image_id="beef-noodle.jpg",
            price=Decimal("140.00"),
        )

        menu_6 = Menu(
            merchant_id=merchant_5.id,
            item_name="三寶飯",
            max_daily_quantity=60,
            image_id="bbq-rice.jpg",
            price=Decimal("115.00"),
        )

        db.add_all([menu_1, menu_2, menu_3, menu_4, menu_5, menu_6])
        db.commit()
        for menu in [menu_1, menu_2, menu_3, menu_4, menu_5, menu_6]:
            db.refresh(menu)

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
            total_amount=Decimal("150.00"),
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
            menu_id=menu_3.id,
            quantity=1,
            unit_price=Decimal("150.00"),
            subtotal=Decimal("150.00"),
        )

        db.add_all([order_item_1, order_item_2])

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
                        "name": "起司豬排咖哩",
                        "quantity": 1,
                        "price": 150,
                    },
                ],
                "payment_method": "credit_card",
            },
            settlement_amount=Decimal("135.00"),
        )

        db.add_all([finance_1, finance_2])
        db.commit()

        print("Dummy data created successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
