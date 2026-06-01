from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.models.kubereats import (
    Finance,
    Menu,
    MenuDailyCapacity,
    MerchantInfo,
    Order,
    OrderItem,
    Tag,
    UserInfo,
)


def clear_all_data(db):
    db.execute(
        text(
            """
            TRUNCATE TABLE
                refresh_tokens,
                user_tags,
                tags,
                finance,
                order_items,
                orders,
                menu_daily_capacity,
                menu,
                merchant_info,
                user_info
            RESTART IDENTITY CASCADE
            """
        )
    )
    db.commit()


def seed():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        clear_all_data(db)

        admin_user = UserInfo(
            username="admin",
            hashed_password="fake_hashed_password",
            role="admin",
            history_records="Initial admin user",
        )

        staff_user = UserInfo(
            username="staff01",
            hashed_password="fake_hashed_password",
            role="staff",
            history_records="First staff user",
        )

        merchant_names = [
            "阿明便當",
            "小森咖哩",
            "清爽蔬食盒",
            "竹科牛肉麵",
            "竹科港式燒臘",
            "泰香打拋",
            "首爾飯桌",
            "義起吃麵",
            "海苔壽司屋",
            "麻辣研究所",
            "早安蛋餅",
            "墨西哥捲餅吧",
            "南科牛肉麵",
            "中科港式燒臘",
        ]
        merchant_users = [
            UserInfo(
                username=f"merchant{index:02d}",
                hashed_password="fake_hashed_password",
                role="merchant",
                history_records=f"{merchant_name} owner",
            )
            for index, merchant_name in enumerate(merchant_names, start=1)
        ]

        users = [admin_user, staff_user, *merchant_users]
        db.add_all(users)
        db.commit()
        for user in users:
            db.refresh(user)

        tag_hot = Tag(name="熱賣")
        tag_bento = Tag(name="雞腿飯")
        tag_curry = Tag(name="咖哩飯")
        tag_healthy = Tag(name="低卡")

        db.add_all([tag_hot, tag_bento, tag_curry, tag_healthy])
        db.commit()

        admin_user.tags = [tag_hot, tag_bento]
        staff_user.tags = [tag_curry, tag_healthy]
        db.commit()

        merchant_specs = [
            {
                "merchant_name": "阿明便當",
                "campus": "竹科",
                "category": "台式便當",
                "rating": "4.8",
                "order_count": 126,
                "min_order": "80.00",
                "max_order_quantity": 50,
                "delivery_time": "25-35 分鐘",
                "tags": ["熱賣", "雞腿飯", "可團訂"],
                "menus": [
                    ("雞腿便當", 50, "120.00"),
                    ("滷排骨飯", 40, "110.00"),
                    ("清爽瓜仔肉飯", 35, "105.00"),
                ],
            },
            {
                "merchant_name": "小森咖哩",
                "campus": "竹科",
                "category": "日式咖哩",
                "rating": "4.6",
                "order_count": 92,
                "min_order": "120.00",
                "max_order_quantity": 80,
                "delivery_time": "30-40 分鐘",
                "tags": ["人氣", "咖哩飯", "今日可訂"],
                "menus": [
                    ("起司豬排咖哩", 80, "150.00"),
                    ("蔬菜雞肉咖哩", 55, "145.00"),
                    ("清爽番茄咖哩", 35, "135.00"),
                ],
            },
            {
                "merchant_name": "清爽蔬食盒",
                "campus": "竹科",
                "category": "健康餐盒",
                "rating": "4.7",
                "order_count": 76,
                "min_order": "100.00",
                "max_order_quantity": 35,
                "delivery_time": "20-30 分鐘",
                "tags": ["低卡", "蔬食", "午餐推薦", "清爽"],
                "menus": [
                    ("舒肥雞胸餐盒", 35, "130.00"),
                    ("藜麥蔬食盒", 30, "125.00"),
                    ("低卡鮭魚餐盒", 20, "165.00"),
                ],
            },
            {
                "merchant_name": "竹科牛肉麵",
                "campus": "竹科",
                "category": "麵食",
                "rating": "4.5",
                "order_count": 88,
                "min_order": "90.00",
                "max_order_quantity": 45,
                "delivery_time": "30-45 分鐘",
                "tags": ["牛肉麵", "湯麵", "多人訂購"],
                "menus": [
                    ("紅燒牛肉麵", 45, "140.00"),
                    ("清燉牛肉麵", 35, "145.00"),
                    ("榨菜肉絲麵", 40, "95.00"),
                ],
            },
            {
                "merchant_name": "竹科港式燒臘",
                "campus": "竹科",
                "category": "港式燒臘",
                "rating": "4.4",
                "order_count": 104,
                "min_order": "95.00",
                "max_order_quantity": 60,
                "delivery_time": "25-35 分鐘",
                "tags": ["燒臘", "三寶飯", "熱門"],
                "menus": [
                    ("三寶飯", 60, "115.00"),
                    ("蜜汁叉燒飯", 45, "110.00"),
                    ("脆皮燒肉飯", 40, "125.00"),
                ],
            },
            {
                "merchant_name": "泰香打拋",
                "campus": "竹科",
                "category": "泰式",
                "rating": "4.3",
                "order_count": 67,
                "min_order": "100.00",
                "max_order_quantity": 45,
                "delivery_time": "20-30 分鐘",
                "tags": ["泰式", "打拋豬", "酸辣", "換口味"],
                "menus": [
                    ("打拋豬飯", 45, "125.00"),
                    ("綠咖哩雞飯", 35, "135.00"),
                    ("泰式椒麻雞", 30, "145.00"),
                ],
            },
            {
                "merchant_name": "首爾飯桌",
                "campus": "竹科",
                "category": "韓式",
                "rating": "4.2",
                "order_count": 58,
                "min_order": "110.00",
                "max_order_quantity": 40,
                "delivery_time": "35-45 分鐘",
                "tags": ["韓式", "泡菜", "辣", "石鍋飯"],
                "menus": [
                    ("泡菜豬肉飯", 40, "130.00"),
                    ("韓式拌飯", 35, "125.00"),
                    ("辣炒年糕", 25, "110.00"),
                ],
            },
            {
                "merchant_name": "義起吃麵",
                "campus": "竹科",
                "category": "義式",
                "rating": "4.1",
                "order_count": 52,
                "min_order": "120.00",
                "max_order_quantity": 35,
                "delivery_time": "30-40 分鐘",
                "tags": ["義大利麵", "奶油", "番茄", "焗烤"],
                "menus": [
                    ("青醬雞肉義大利麵", 30, "150.00"),
                    ("番茄海鮮義大利麵", 25, "170.00"),
                    ("奶油培根燉飯", 35, "145.00"),
                ],
            },
            {
                "merchant_name": "海苔壽司屋",
                "campus": "竹科",
                "category": "日式",
                "rating": "4.5",
                "order_count": 49,
                "min_order": "90.00",
                "max_order_quantity": 30,
                "delivery_time": "15-25 分鐘",
                "tags": ["壽司", "日式", "清爽", "冷食"],
                "menus": [
                    ("鮭魚壽司盒", 30, "160.00"),
                    ("豆皮壽司", 35, "95.00"),
                    ("海苔花壽司", 30, "110.00"),
                ],
            },
            {
                "merchant_name": "麻辣研究所",
                "campus": "竹科",
                "category": "麻辣",
                "rating": "4.6",
                "order_count": 72,
                "min_order": "120.00",
                "max_order_quantity": 30,
                "delivery_time": "35-50 分鐘",
                "tags": ["麻辣", "重口味", "辣", "宵夜"],
                "menus": [
                    ("麻辣鴨血豆腐", 30, "120.00"),
                    ("麻辣牛肉拌麵", 25, "150.00"),
                    ("香辣雞腿飯", 30, "135.00"),
                ],
            },
            {
                "merchant_name": "早安蛋餅",
                "campus": "竹科",
                "category": "早餐",
                "rating": "4.0",
                "order_count": 134,
                "min_order": "60.00",
                "max_order_quantity": 100,
                "delivery_time": "10-20 分鐘",
                "tags": ["早餐", "蛋餅", "快速", "便宜"],
                "menus": [
                    ("起司蛋餅", 100, "55.00"),
                    ("鮪魚蛋餅", 80, "65.00"),
                    ("蘿蔔糕套餐", 60, "85.00"),
                ],
            },
            {
                "merchant_name": "墨西哥捲餅吧",
                "campus": "竹科",
                "category": "墨西哥",
                "rating": "4.2",
                "order_count": 31,
                "min_order": "120.00",
                "max_order_quantity": 25,
                "delivery_time": "25-35 分鐘",
                "tags": ["墨西哥", "捲餅", "異國", "清爽"],
                "menus": [
                    ("雞肉莎莎捲餅", 25, "135.00"),
                    ("牛肉起司捲餅", 20, "150.00"),
                    ("酪梨蔬菜捲餅", 18, "145.00"),
                ],
            },
            {
                "merchant_name": "南科牛肉麵",
                "campus": "南科",
                "category": "麵食",
                "rating": "4.5",
                "order_count": 88,
                "min_order": "90.00",
                "max_order_quantity": 45,
                "delivery_time": "30-45 分鐘",
                "tags": ["牛肉麵", "湯麵", "多人訂購"],
                "menus": [("紅燒牛肉麵", 45, "140.00")],
            },
            {
                "merchant_name": "中科港式燒臘",
                "campus": "中科",
                "category": "港式",
                "rating": "4.4",
                "order_count": 104,
                "min_order": "95.00",
                "max_order_quantity": 60,
                "delivery_time": "25-35 分鐘",
                "tags": ["燒臘", "三寶飯", "熱門"],
                "menus": [("三寶飯", 60, "115.00")],
            },
        ]

        merchants = []
        menus = []

        for merchant_user, spec in zip(merchant_users, merchant_specs, strict=True):
            merchant = MerchantInfo(
                user_id=merchant_user.id,
                merchant_name=spec["merchant_name"],
                campus=spec["campus"],
                category=spec["category"],
                rating=Decimal(spec["rating"]),
                order_count=spec["order_count"],
                min_order=Decimal(spec["min_order"]),
                max_order_quantity=spec["max_order_quantity"],
                delivery_time=spec["delivery_time"],
                tags=spec["tags"],
                audit_status=1,
            )
            merchants.append(merchant)

        db.add_all(merchants)
        db.commit()
        for merchant in merchants:
            db.refresh(merchant)

        for merchant, spec in zip(merchants, merchant_specs, strict=True):
            for item_name, max_daily_quantity, price in spec["menus"]:
                menus.append(
                    Menu(
                        merchant_id=merchant.id,
                        item_name=item_name,
                        max_daily_quantity=max_daily_quantity,
                        image_id=f"{item_name}.jpg",
                        price=Decimal(price),
                    )
                )

        db.add_all(menus)
        db.commit()
        for menu in menus:
            db.refresh(menu)

        today = date.today()
        capacities = [
            MenuDailyCapacity(
                menu_id=menu.id,
                target_date=today,
                max_quantity=menu.max_daily_quantity,
                remaining_quantity=menu.max_daily_quantity,
            )
            for menu in menus
        ]

        db.add_all(capacities)
        db.commit()

        menu_by_name = {menu.item_name: menu for menu in menus}

        def create_order(user, item_name, days_ago, quantity=1, status=1):
            menu = menu_by_name[item_name]
            total = Decimal(menu.price) * quantity
            order = Order(
                user_id=user.id,
                total_amount=total,
                order_status=status,
                order_time=datetime.now(UTC) - timedelta(days=days_ago),
            )
            db.add(order)
            db.commit()
            db.refresh(order)

            order_item = OrderItem(
                order_id=order.id,
                menu_id=menu.id,
                quantity=quantity,
                unit_price=Decimal(menu.price),
                subtotal=total,
            )
            finance = Finance(
                merchant_id=menu.merchant_id,
                order_id=order.id,
                report_data={
                    "items": [
                        {
                            "name": item_name,
                            "quantity": quantity,
                            "price": float(menu.price),
                        }
                    ],
                    "payment_method": "credit_card",
                },
                settlement_amount=total * Decimal("0.9"),
            )
            db.add_all([order_item, finance])
            db.commit()
            return order

        create_order(admin_user, "雞腿便當", days_ago=1)

        # staff01 is the main recommendation test user.
        # Recent orders intentionally repeat some merchants so novelty prompts can
        # penalize familiar choices and surface unseen restaurants.
        staff_history = [
            ("雞腿便當", 0),
            ("滷排骨飯", 1),
            ("起司豬排咖哩", 2),
            ("蔬菜雞肉咖哩", 3),
            ("舒肥雞胸餐盒", 4),
            ("三寶飯", 5),
            ("紅燒牛肉麵", 6),
            ("打拋豬飯", 8),
            ("韓式拌飯", 10),
        ]

        for item_name, days_ago in staff_history:
            create_order(staff_user, item_name, days_ago)

        db.commit()

        print(
            "Dummy data reset and created successfully: "
            f"{len(merchants)} merchants, {len(menus)} menus, "
            f"{len(staff_history)} staff history orders."
        )

    finally:
        db.close()


if __name__ == "__main__":
    seed()
