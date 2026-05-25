from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.models import kubereats  # noqa: F401
from app.routes.merchant_route import router as merchant_router
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

app.include_router(merchant_router)
app.include_router(order_router)


@app.get("/")
def root():
    return {"message": "Kubereats backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
