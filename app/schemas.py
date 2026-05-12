from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime
from decimal import Decimal

class FinanceRecord(BaseModel):
    id: int
    merchant_id: int
    order_id: int
    report_data: Optional[Any]
    settlement_amount: Decimal

    class Config:
        from_attributes = True

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
