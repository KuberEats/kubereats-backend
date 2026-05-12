from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from .. import models, database, schemas
from ..tasks import generate_report_task

router = APIRouter()

@router.get("/history")
def get_finance_history(db: Session = Depends(database.get_db)):
    return db.query(models.Finance).all()

@router.post("/generate-report")
def trigger_report_generation(merchant_id: int):
    # Trigger Celery task
    task = generate_report_task.delay(merchant_id)
    return {"task_id": task.id, "status": "Report generation started"}
