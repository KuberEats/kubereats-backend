from .worker import celery_app
from .database import SessionLocal
from .services.tagging import TaggingService
from .models import UserInfo

@celery_app.task(name="update_all_user_tags")
def update_all_user_tags():
    db = SessionLocal()
    try:
        users = db.query(UserInfo).all()
        service = TaggingService(db)
        for user in users:
            service.update_user_tags_based_on_orders(user.id)
        return f"Updated tags for {len(users)} users"
    finally:
        db.close()

@celery_app.task(name="generate_finance_report")
def generate_finance_report(merchant_id: int):
    # Simulated report generation
    return f"Report generated for merchant {merchant_id}"
