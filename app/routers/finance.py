from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from .. import database, schemas
from ..metrics import report_downloads, records_returned, reports_generated, settlement_queries
from ..services import ReportService, MonitoringService

router = APIRouter()


def report_base_url(request: Request) -> str:
    path = request.url.path.rstrip("/")
    if path.endswith("/generate-report"):
        path = f"{path.removesuffix('/generate-report')}/reports"

    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    scheme = scheme.split(",", 1)[0].strip()
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if not host:
        host = request.url.netloc
    return f"{scheme}://{host}{path}"

@router.get("/grafanacheck")
def grafana_check(db: Session = Depends(database.get_db)):
    return MonitoringService.health_check(db)

@router.get("/history")
def get_finance_history(db: Session = Depends(database.get_db)):
    records = ReportService.get_history(db)
    settlement_queries.inc("history", "success")
    records_returned.inc("history", amount=len(records))
    return records

@router.get("/reports", response_model=list[schemas.ReportResult])
def list_reports(request: Request):
    reports = ReportService.list_reports(report_base_url(request))
    records_returned.inc("reports", amount=len(reports))
    return reports


@router.get("/reports/{filename}", name="download_report")
def download_report(filename: str):
    path = ReportService.get_report_path(filename)
    if not path:
        report_downloads.inc("not_found")
        raise HTTPException(status_code=404, detail="Report not found")
    report_downloads.inc("success")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@router.post("/generate-report", response_model=schemas.ReportResult)
def trigger_report_generation(
    merchant_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
):
    try:
        report = ReportService.trigger_report_generation(
            db,
            merchant_id,
            report_base_url(request),
        )
        reports_generated.inc("success")
        return report
    except ValueError as error:
        reports_generated.inc("merchant_not_found")
        raise HTTPException(status_code=404, detail=str(error)) from error
