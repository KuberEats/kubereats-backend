from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models, schemas, database
from decimal import Decimal

router = APIRouter()

@router.get("/expenses", response_model=schemas.ExpenseStatus)
def get_expenses(user_id: int, db: Session = Depends(database.get_db)):
    total = db.query(func.sum(models.Order.total_amount)).filter(
        models.Order.user_id == user_id,
        models.Order.order_status == 1 # Finished
    ).scalar() or Decimal("0")
    
    count = db.query(models.Order).filter(
        models.Order.user_id == user_id,
        models.Order.order_status == 1
    ).count()
    
    return {"total_expense": total, "order_count": count}

@router.get("/salary-deductions", response_model=list[schemas.SalaryDeduction])
def get_salary_deductions(user_id: int, db: Session = Depends(database.get_db)):
    # Assuming all finished orders are deducted from salary in this system
    orders = db.query(models.Order).filter(
        models.Order.user_id == user_id,
        models.Order.order_status == 1
    ).all()
    
    return orders
