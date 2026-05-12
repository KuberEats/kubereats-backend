from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models, schemas, database
from decimal import Decimal
from datetime import datetime

router = APIRouter()

@router.get("/income-status", response_model=schemas.IncomeStatus)
def get_income_status(merchant_id: int, db: Session = Depends(database.get_db)):
    # Total income from finished orders related to this merchant's menu items
    # The current schema has Order table but no OrderItem table. 
    # Usually Order has many OrderItems which link to Menu.
    # Given the simplified schema in TODO.md, I'll assume Finance table records 
    # the settlement per order for the merchant.
    
    total = db.query(func.sum(models.Finance.settlement_amount)).filter(
        models.Finance.merchant_id == merchant_id
    ).scalar() or Decimal("0")
    
    count = db.query(models.Finance).filter(
        models.Finance.merchant_id == merchant_id
    ).count()
    
    return {"total_income": total, "order_count": count}

@router.get("/payouts", response_model=list[schemas.PayoutResult])
def get_payouts(merchant_id: int, db: Session = Depends(database.get_db)):
    records = db.query(models.Finance).filter(
        models.Finance.merchant_id == merchant_id
    ).all()
    
    results = []
    for r in records:
        status = "pending"
        if r.report_data and isinstance(r.report_data, dict):
            status = r.report_data.get("status", "pending")
        
        results.append({
            "id": r.id,
            "order_id": r.order_id,
            "settlement_amount": r.settlement_amount,
            "status": status
        })
    return results

@router.get("/monthly-total")
def get_monthly_total(merchant_id: int, db: Session = Depends(database.get_db)):
    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)
    
    total = db.query(func.sum(models.Finance.settlement_amount)).join(models.Order).filter(
        models.Finance.merchant_id == merchant_id,
        models.Order.order_time >= month_start
    ).scalar() or Decimal("0")
    
    return {"monthly_total": total, "month": now.month, "year": now.year}
