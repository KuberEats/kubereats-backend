from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from .. import database, schemas
from ..services import ReportService, MonitoringService

router = APIRouter()


def report_base_url(request: Request) -> str:
    path = request.url.path.rstrip("/")
    if path.endswith("/generate-report"):
        path = f"{path.removesuffix('/generate-report')}/reports"
    return f"{str(request.base_url).rstrip('/')}{path}"

@router.get("/grafanacheck")
def grafana_check(db: Session = Depends(database.get_db)):
    return MonitoringService.health_check(db)

@router.get("/history")
def get_finance_history(db: Session = Depends(database.get_db)):
    return ReportService.get_history(db)

@router.get("/reports", response_model=list[schemas.ReportResult])
def list_reports(request: Request):
    return ReportService.list_reports(report_base_url(request))


@router.get("/reports/{filename}", name="download_report")
def download_report(filename: str):
    path = ReportService.get_report_path(filename)
    if not path:
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@router.post("/generate-report", response_model=schemas.ReportResult)
def trigger_report_generation(
    merchant_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
):
    try:
        return ReportService.trigger_report_generation(
            db,
            merchant_id,
            report_base_url(request),
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
