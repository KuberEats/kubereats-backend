from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import setup_logging
from app.core.metrics import (
    kubereats_menu_capacity_remaining,
    kubereats_merchant_available,
)
from app.database import Base, engine, get_db
from app.models import kubereats  # noqa: F401
from app.repo.merchant_repo import MerchantRepository
from app.routes.merchant_route import router as merchant_router
from datetime import date

setup_logging()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="KuberEats Merchant Service",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(merchant_router)


@app.get("/")
def root():
    return {"service": "merchant-service", "status": "running"}


@app.get("/health/live")
def health_live():
    """Liveness probe — confirms the process is running."""
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    """Readiness probe — confirms the service can reach the database."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    for snapshot in MerchantRepository(db).list_business_metric_snapshots(date.today()):
        labels = {
            "campus": snapshot["campus"],
            "merchant_id": snapshot["merchant_id"],
        }
        kubereats_merchant_available.labels(**labels).set(snapshot["available"])
        kubereats_menu_capacity_remaining.labels(
            **labels,
            pickup_slot="daily",
        ).set(snapshot["remaining_capacity"])
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
