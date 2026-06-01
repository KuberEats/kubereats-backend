from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.models import kubereats  # noqa: F401
from app.routes.internal_task_route import router as internal_task_router
from app.routes.order_route import router as order_router
from app.routes.reservation_route import router as reservation_router

Base.metadata.create_all(bind=engine)
settings = get_settings()

app = FastAPI(
    title="Kubereats Backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(order_router)
app.include_router(reservation_router)
app.include_router(internal_task_router)


@app.get("/")
def root():
    return {"message": "Kubereats backend is running"}


def get_health_status():
    return {"status": "ok"}


@app.get("/health")
def health_check():
    return get_health_status()


@app.get("/health-check")
def health_check_probe():
    return get_health_status()
