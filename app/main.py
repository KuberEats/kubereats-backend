from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas, database
from .routers import merchant, staff, finance
from .database_init import init_db

app = FastAPI(title="KubeEats Finance Microservice")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # In a real microservice, we might use Alembic
    # For local dev, we init db with dummy data
    init_db()

app.include_router(merchant.router, prefix="/api/merchant", tags=["merchant"])
app.include_router(staff.router, prefix="/api/staff", tags=["staff"])
app.include_router(finance.router, prefix="/api/finance", tags=["finance"])

@app.get("/")
def read_root():
    return {"message": "Welcome to KubeEats Finance Microservice"}
