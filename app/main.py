from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.models import kubereats  # noqa: F401
from app.routes.internal_task_route import router as internal_task_router
from app.routes.order_route import router as order_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Kubereats Backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(order_router)
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
