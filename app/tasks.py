from .worker import celery_app
from .database import SessionLocal
from .models import Finance, MerchantInfo, Order
from fpdf import FPDF
import os
from datetime import datetime

@celery_app.task
def generate_report_task(merchant_id: int):
    db = SessionLocal()
    try:
        merchant = db.query(MerchantInfo).filter(MerchantInfo.id == merchant_id).first()
        if not merchant:
            return "Merchant not found"

        records = db.query(Finance).filter(Finance.merchant_id == merchant_id).all()
        
        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Financial Report for {merchant.merchant_name}", ln=True, align='C')
        pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
        pdf.ln(10)
        
        pdf.cell(40, 10, "Order ID", 1)
        pdf.cell(60, 10, "Settlement Amount", 1)
        pdf.cell(60, 10, "Status", 1)
        pdf.ln()

        total_settlement = 0
        for r in records:
            status = r.report_data.get("status", "N/A") if r.report_data else "N/A"
            pdf.cell(40, 10, str(r.order_id), 1)
            pdf.cell(60, 10, f"${r.settlement_amount}", 1)
            pdf.cell(60, 10, status, 1)
            pdf.ln()
            total_settlement += float(r.settlement_amount)

        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Total Settlement: ${total_settlement}", ln=True)

        # Ensure reports directory exists
        report_dir = "reports"
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
            
        file_path = f"{report_dir}/report_merchant_{merchant_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        pdf.output(file_path)
        
        # Update Finance table (optional notification record)
        # Here we could send an email or push notification
        
        return f"Report generated at {file_path}"
    finally:
        db.close()

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Periodically write monthly info
    sender.add_periodic_task(3600.0, monthly_finance_aggregation.s(), name='monthly aggregation')

@celery_app.task
def monthly_finance_aggregation():
    # Example: Logic to aggregate orders into finance table for the month
    db = SessionLocal()
    # Simplified logic: just log for now
    print("Running monthly finance aggregation...")
    db.close()
