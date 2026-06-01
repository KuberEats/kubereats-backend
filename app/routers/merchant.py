from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import schemas, database
from ..metrics import records_returned, settlement_queries
from ..services import MerchantFinanceService

router = APIRouter()

@router.get("/income-status", response_model=schemas.IncomeStatus)
def get_income_status(merchant_id: int, db: Session = Depends(database.get_db)):
    result = MerchantFinanceService.get_income_status(db, merchant_id)
    settlement_queries.inc("merchant_income_status", "success")
    records_returned.inc("merchant_income_status", amount=result["order_count"])
    return result

@router.get("/payouts", response_model=list[schemas.PayoutResult])
def get_payouts(merchant_id: int, db: Session = Depends(database.get_db)):
    payouts = MerchantFinanceService.get_payouts(db, merchant_id)
    settlement_queries.inc("merchant_payouts", "success")
    records_returned.inc("merchant_payouts", amount=len(payouts))
    return payouts

@router.get("/monthly-total")
def get_monthly_total(merchant_id: int, db: Session = Depends(database.get_db)):
    settlement_queries.inc("merchant_monthly_total", "success")
    return MerchantFinanceService.get_monthly_total(db, merchant_id)

@router.get("/monthly-item-distribution", response_model=list[schemas.MonthlyItemDistribution])
def get_monthly_item_distribution(merchant_id: int, db: Session = Depends(database.get_db)):
    items = MerchantFinanceService.get_monthly_item_distribution(db, merchant_id)
    settlement_queries.inc("merchant_monthly_item_distribution", "success")
    records_returned.inc("merchant_monthly_item_distribution", amount=len(items))
    return items

# @router.get("/test-connection")
# def test_connection(db: Session = Depends(database.get_db)):
#     from .. import models
#     merchant = db.query(models.MerchantInfo).filter(models.MerchantInfo.id == 1).first()
#     if not merchant:
#         return {"message": "Connected to DB, but no merchant with ID 1 found."}
#     return {"message": "Success", "merchant_name": merchant.merchant_name}
