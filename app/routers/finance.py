from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from .. import database, schemas
from ..services import ReportService, MonitoringService

router = APIRouter()

@router.get("/grafanacheck")
def grafana_check(db: Session = Depends(database.get_db)):
    return MonitoringService.health_check(db)

@router.get("/history")
def get_finance_history(db: Session = Depends(database.get_db)):
    return ReportService.get_history(db)

@router.post("/generate-report")
def trigger_report_generation(merchant_id: int):
    return ReportService.trigger_report_generation(merchant_id)
