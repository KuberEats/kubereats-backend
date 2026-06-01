from .worker import celery_app
from .database import SessionLocal
from .services import ReportService

@celery_app.task
def generate_report_task(merchant_id: int):
    db = SessionLocal()
    try:
        return f"Report generated at {ReportService.generate_report_file(db, merchant_id)}"
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
