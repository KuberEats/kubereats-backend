from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import schemas, database
from ..metrics import records_returned, settlement_queries
from ..services import StaffFinanceService

router = APIRouter()

@router.get("/expenses", response_model=schemas.ExpenseStatus)
def get_expenses(user_id: int, db: Session = Depends(database.get_db)):
    result = StaffFinanceService.get_expenses(db, user_id)
    settlement_queries.inc("staff_expenses", "success")
    records_returned.inc("staff_expenses", amount=result["order_count"])
    return result

@router.get("/salary-deductions", response_model=list[schemas.SalaryDeduction])
def get_salary_deductions(user_id: int, db: Session = Depends(database.get_db)):
    orders = StaffFinanceService.get_salary_deductions(db, user_id)
    settlement_queries.inc("staff_salary_deductions", "success")
    records_returned.inc("staff_salary_deductions", amount=len(orders))
    return orders
