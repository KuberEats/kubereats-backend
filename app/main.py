from time import monotonic

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.database import Base, engine, get_db
from app.models import kubereats  # noqa: F401
from app.routes.auth_route import router as auth_router

settings = get_settings()
setup_logging()
started_at = monotonic()

if settings.auto_create_tables:
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="KuberEats Verification Service",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/")
def root():
    return {"service": "verification", "status": "running"}


@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.get("/readyz")
def readyz():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    uptime_seconds = monotonic() - started_at
    return (
        "# HELP verification_up Service health status.\n"
        "# TYPE verification_up gauge\n"
        "verification_up 1\n"
        "# HELP verification_uptime_seconds Service uptime in seconds.\n"
        "# TYPE verification_uptime_seconds gauge\n"
        f"verification_uptime_seconds {uptime_seconds:.0f}\n"
    )
