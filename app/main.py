from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import setup_logging
from app.database import Base, engine, get_db
from app.models import kubereats  # noqa: F401
from app.routes.auth_route import router as auth_router

setup_logging()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="KuberEats Auth Service",
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
    return {"service": "auth-service", "status": "running"}


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
