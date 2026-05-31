from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import schemas, database
from ..services import MerchantFinanceService

router = APIRouter()

@router.get("/income-status", response_model=schemas.IncomeStatus)
def get_income_status(merchant_id: int, db: Session = Depends(database.get_db)):
    return MerchantFinanceService.get_income_status(db, merchant_id)

@router.get("/payouts", response_model=list[schemas.PayoutResult])
def get_payouts(merchant_id: int, db: Session = Depends(database.get_db)):
    return MerchantFinanceService.get_payouts(db, merchant_id)

@router.get("/monthly-total")
def get_monthly_total(merchant_id: int, db: Session = Depends(database.get_db)):
    return MerchantFinanceService.get_monthly_total(db, merchant_id)

@router.get("/monthly-item-distribution", response_model=list[schemas.MonthlyItemDistribution])
def get_monthly_item_distribution(merchant_id: int, db: Session = Depends(database.get_db)):
    return MerchantFinanceService.get_monthly_item_distribution(db, merchant_id)
