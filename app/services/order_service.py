from collections import defaultdict
from decimal import Decimal

from fastapi import HTTPException

from app.models.kubereats import Finance, Order, OrderItem
from app.repo.menu_repo import MenuRepository
from app.repo.order_repo import OrderRepository
from app.schemas.order import OrderCreate


class OrderService:
    PLATFORM_SETTLEMENT_RATE = Decimal("0.90")
    VALID_ORDER_STATUSES = {0, 1, 2}

    def __init__(
        self,
        order_repo: OrderRepository,
        menu_repo: MenuRepository,
    ):
        self.order_repo = order_repo
        self.menu_repo = menu_repo

    def create_order(self, order_data: OrderCreate):
        user = self.order_repo.get_user_by_id(order_data.user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        menu_quantity_map = self._merge_item_quantities(order_data)
        menus = self._load_menus(menu_quantity_map)
        total_amount = self._calculate_total_amount(menu_quantity_map, menus)
        self._validate_merchant_min_orders(menu_quantity_map, menus)

        try:
            order = self.order_repo.create_order(
                Order(
                    user_id=order_data.user_id,
                    total_amount=total_amount,
                    order_status=0,
                )
            )

            order_items = [
                OrderItem(
                    order_id=order.id,
                    menu_id=menu.id,
                    quantity=menu_quantity_map[menu.id],
                    unit_price=menu.price,
                    subtotal=menu.price * menu_quantity_map[menu.id],
                )
                for menu in menus.values()
            ]
            self.order_repo.create_order_items(order_items)

            finance_records = self._build_finance_records(order.id, menu_quantity_map, menus)
            self.order_repo.create_finance_records(finance_records)

            self.order_repo.commit()
            return self.get_order_by_id(order.id)
        except Exception:
            self.order_repo.rollback()
            raise

    def get_order_by_id(self, order_id: int):
        order = self.order_repo.get_by_id(order_id)

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        return self._serialize_order(order)

    def update_order_status(self, order_id: int, order_status: int):
        order = self.order_repo.get_by_id(order_id)

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order_status not in self.VALID_ORDER_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid order status")

        if order.order_status in {1, 2} and order.order_status != order_status:
            raise HTTPException(
                status_code=400,
                detail="Completed or cancelled orders cannot change status",
            )

        order.order_status = order_status
        self.order_repo.commit()
        return self.get_order_by_id(order.id)

    def _merge_item_quantities(self, order_data: OrderCreate):
        menu_quantity_map = defaultdict(int)

        for item in order_data.items:
            menu_quantity_map[item.menu_id] += item.quantity

        return dict(menu_quantity_map)

    def _load_menus(self, menu_quantity_map: dict[int, int]):
        menus = {}

        for menu_id in menu_quantity_map:
            menu = self.menu_repo.get_by_id(menu_id)

            if not menu:
                raise HTTPException(
                    status_code=404,
                    detail=f"Menu item {menu_id} not found",
                )

            if menu.merchant.audit_status != 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"Menu item {menu_id} is not available",
                )

            menus[menu_id] = menu

        return menus

    def _calculate_total_amount(self, menu_quantity_map, menus):
        total_amount = Decimal("0.00")

        for menu_id, quantity in menu_quantity_map.items():
            menu = menus[menu_id]

            if quantity > menu.max_daily_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"{menu.item_name} exceeds daily available quantity",
                )

            total_amount += menu.price * quantity

        return total_amount

    def _validate_merchant_min_orders(self, menu_quantity_map, menus):
        merchant_totals = defaultdict(Decimal)

        for menu_id, quantity in menu_quantity_map.items():
            menu = menus[menu_id]
            merchant_totals[menu.merchant_id] += menu.price * quantity

        for merchant_id, merchant_total in merchant_totals.items():
            merchant = next(
                menu.merchant for menu in menus.values() if menu.merchant_id == merchant_id
            )

            if merchant_total < merchant.min_order:
                raise HTTPException(
                    status_code=400,
                    detail=f"{merchant.merchant_name} minimum order is {merchant.min_order}",
                )

    def _build_finance_records(self, order_id: int, menu_quantity_map, menus):
        merchant_items = defaultdict(list)

        for menu_id, quantity in menu_quantity_map.items():
            menu = menus[menu_id]
            subtotal = menu.price * quantity
            merchant_items[menu.merchant_id].append(
                {
                    "menu_id": menu.id,
                    "name": menu.item_name,
                    "quantity": quantity,
                    "price": float(menu.price),
                    "subtotal": float(subtotal),
                }
            )

        finance_records = []

        for merchant_id, items in merchant_items.items():
            merchant_total = sum(Decimal(str(item["subtotal"])) for item in items)
            settlement_amount = merchant_total * self.PLATFORM_SETTLEMENT_RATE

            finance_records.append(
                Finance(
                    merchant_id=merchant_id,
                    order_id=order_id,
                    report_data={
                        "items": items,
                        "merchant_total": float(merchant_total),
                        "settlement_rate": float(self.PLATFORM_SETTLEMENT_RATE),
                    },
                    settlement_amount=settlement_amount,
                )
            )

        return finance_records

    def _serialize_order(self, order):
        return {
            "id": order.id,
            "user_id": order.user_id,
            "total_amount": float(order.total_amount),
            "order_status": order.order_status,
            "order_time": order.order_time,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "items": [
                {
                    "id": item.id,
                    "menu_id": item.menu_id,
                    "item_name": item.menu.item_name,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "subtotal": float(item.subtotal),
                }
                for item in order.items
            ],
            "finance_records": [
                {
                    "id": finance.id,
                    "merchant_id": finance.merchant_id,
                    "merchant_name": finance.merchant.merchant_name,
                    "settlement_amount": float(finance.settlement_amount),
                    "report_data": finance.report_data,
                }
                for finance in order.finance_records
            ],
        }
