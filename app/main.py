from fastapi import FastAPI

from app.database import Base, engine
from app.models import kubereats

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Kubereats Backend",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"message": "Kubereats backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
