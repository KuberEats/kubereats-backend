from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import schemas, database
from ..services import StaffFinanceService

router = APIRouter()

@router.get("/expenses", response_model=schemas.ExpenseStatus)
def get_expenses(user_id: int, db: Session = Depends(database.get_db)):
    return StaffFinanceService.get_expenses(db, user_id)

@router.get("/salary-deductions", response_model=list[schemas.SalaryDeduction])
def get_salary_deductions(user_id: int, db: Session = Depends(database.get_db)):
    return StaffFinanceService.get_salary_deductions(db, user_id)
