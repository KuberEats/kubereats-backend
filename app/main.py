import logging
import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.models import kubereats  # noqa: F401
from app.routes.recommendation_route import router as recommendation_router
from app.services.recommendation.metrics import recommendation_metrics

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(levelname)s:%(name)s:%(message)s",
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Kubereats Recommendation Backend",
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

app.include_router(recommendation_router)


@app.middleware("http")
async def recommendation_metrics_middleware(request, call_next):
    path = request.url.path

    if path not in {"/recommendations/merchants", "/recommendations/menus"}:
        return await call_next(request)

    started_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        recommendation_metrics.record_api_request(
            path,
            request.method,
            "error",
            time.perf_counter() - started_at,
        )
        raise

    recommendation_metrics.record_api_request(
        path,
        request.method,
        "success" if response.status_code < 400 else "error",
        time.perf_counter() - started_at,
    )
    return response


@app.get("/")
def root():
    return {"message": "Kubereats recommendation backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health-check")
def health_check_alias():
    return health_check()
