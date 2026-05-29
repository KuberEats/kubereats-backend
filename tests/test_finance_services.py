import pytest
from decimal import Decimal
from datetime import datetime
from app.services import MerchantFinanceService, ReportService
from app import models

def test_get_income_status(db_session):
    # Setup test data
    merchant = models.MerchantInfo(
        user_id=1,
        merchant_name="Test Merchant",
        campus="Main",
        category="Food",
        delivery_time="30 min"
    )
    db_session.add(merchant)
    db_session.commit()

    order = models.Order(user_id=1, total_amount=Decimal("100.00"), order_status=1)
    db_session.add(order)
    db_session.commit()

    finance1 = models.Finance(merchant_id=merchant.id, order_id=order.id, settlement_amount=Decimal("90.00"))
    finance2 = models.Finance(merchant_id=merchant.id, order_id=order.id, settlement_amount=Decimal("45.50"))
    db_session.add_all([finance1, finance2])
    db_session.commit()

    # Call service
    result = MerchantFinanceService.get_income_status(db_session, merchant.id)

    # Assertions
    assert result["total_income"] == Decimal("135.50")
    assert result["order_count"] == 2

def test_get_payouts(db_session):
    merchant = models.MerchantInfo(user_id=2, merchant_name="Payout Merchant", campus="Main", category="Food", delivery_time="30 min")
    db_session.add(merchant)
    db_session.commit()

    order = models.Order(user_id=2, total_amount=Decimal("50.00"), order_status=1)
    db_session.add(order)
    db_session.commit()

    finance = models.Finance(
        merchant_id=merchant.id, 
        order_id=order.id, 
        settlement_amount=Decimal("45.00"),
        report_data={"status": "paid"}
    )
    db_session.add(finance)
    db_session.commit()

    result = MerchantFinanceService.get_payouts(db_session, merchant.id)

    assert len(result) == 1
    assert result[0]["status"] == "paid"
    assert result[0]["settlement_amount"] == Decimal("45.00")

def test_save_monthly_summary(db_session):
    merchant = models.MerchantInfo(user_id=3, merchant_name="Summary Merchant", campus="Main", category="Food", delivery_time="30 min")
    db_session.add(merchant)
    db_session.commit()

    report_data = {"total_sales": 1000, "commission": 100}
    amount = Decimal("900.00")
    
    record = ReportService.save_monthly_summary(db_session, merchant.id, report_data, amount)
    
    assert record.id is not None
    assert record.merchant_id == merchant.id
    assert record.settlement_amount == amount
    assert record.report_data == report_data

def test_get_history(db_session):
    # This just tests if it returns all records
    merchant = models.MerchantInfo(user_id=4, merchant_name="History Merchant", campus="Main", category="Food", delivery_time="30 min")
    db_session.add(merchant)
    db_session.commit()

    finance = models.Finance(merchant_id=merchant.id, order_id=0, settlement_amount=Decimal("10.00"))
    db_session.add(finance)
    db_session.commit()

    history = ReportService.get_history(db_session)
    assert len(history) >= 1
