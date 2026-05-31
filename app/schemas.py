from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from datetime import datetime, date
from decimal import Decimal

class FinanceBase(BaseModel):
    merchant_id: int
    order_id: int
    report_data: Optional[Any] = None
    settlement_amount: Decimal

class FinanceCreate(FinanceBase):
    pass

class FinanceRecord(FinanceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class IncomeStatus(BaseModel):
    total_income: Decimal
    order_count: int

class PayoutResult(BaseModel):
    id: int
    order_id: int
    settlement_amount: Decimal
    status: str

class ExpenseStatus(BaseModel):
    total_expense: Decimal
    order_count: int

class SalaryDeduction(BaseModel):
    id: int
    total_amount: Decimal
    order_time: datetime

class OrderItemBase(BaseModel):
    menu_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

class OrderBase(BaseModel):
    user_id: int
    total_amount: Decimal
    order_status: int
    order_time: datetime

class OrderWithItems(OrderBase):
    id: int
    items: List[OrderItemBase]
    
    model_config = ConfigDict(from_attributes=True)

class MerchantBase(BaseModel):
    user_id: int
    merchant_name: str
    campus: str
    category: str
    rating: Decimal = Decimal("0")
    order_count: int = 0
    min_order: Decimal = Decimal("0")
    max_order_quantity: int = 0
    delivery_time: str
    tags: List[str] = []
    audit_status: int = 0

class MerchantRecord(MerchantBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MonthlyItemDistribution(BaseModel):
    itemName: str
    totalAmount: float
    percentage: float
