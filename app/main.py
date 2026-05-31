from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import merchant, staff, finance

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # In a real microservice, we might use Alembic
    # init_db() was removed to avoid modifying shared remote DB schema
    yield

app = FastAPI(title="KubeEats Finance Microservice", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(merchant.router, prefix="/merchant", tags=["finance"])
app.include_router(staff.router, prefix="/staff", tags=["finance"])
app.include_router(finance.router, tags=["finance"])

# Deprecated compatibility aliases for environments that do not strip the
# service prefix at the load balancer.
app.include_router(
    merchant.router,
    prefix="/finance/merchant",
    tags=["finance-deprecated"],
    deprecated=True,
)
app.include_router(
    staff.router,
    prefix="/finance/staff",
    tags=["finance-deprecated"],
    deprecated=True,
)
app.include_router(
    finance.router,
    prefix="/finance",
    tags=["finance-deprecated"],
    deprecated=True,
)

# Deprecated compatibility aliases. Public LB routes must use /finance/*.
app.include_router(
    finance.router,
    prefix="/api/finance",
    tags=["finance-deprecated"],
    deprecated=True,
)

@app.get("/")
def read_root():
    return {"message": "Welcome to KubeEats Finance Microservice"}

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/finance/health")
def finance_health_check():
    return health_check()
