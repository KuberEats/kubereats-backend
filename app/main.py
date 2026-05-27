from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.models import notification  # noqa: F401
from app.routes.notifications import router as notification_router

app = FastAPI(title="KuberEats Notification Service", version="0.1.0")
app.include_router(notification_router)


@app.get("/")
def root():
    return {"service": "notification-service", "status": "running"}


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
