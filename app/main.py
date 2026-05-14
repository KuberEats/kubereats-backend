from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.models import kubereats  # noqa: F401
from app.routes.merchant_route import router as merchant_router

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


@app.get("/health")
def health_check():
    return {"status": "ok"}
