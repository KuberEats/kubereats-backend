from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .services.tagging import TaggingService, MerchantService, StaffService
from .models import Finance, Order, UserInfo, MerchantInfo, Tag
import decimal
import time
import io
import base64
import barcode
from barcode.writer import ImageWriter
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Check database connection on startup
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            print("Database connection verified successfully")
    except Exception as e:
        print(f"Database connection failed: {e}")
    yield

app = FastAPI(title="KubeEats Tagging Service", lifespan=lifespan)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Unhealthy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "KubeEats Tagging Service is running"}


@app.get("/tagging/health", deprecated=True)
def tagging_health_check(db: Session = Depends(get_db)):
    return health_check(db)


# Deprecated/internal compatibility routes from early tagging-service prototypes.
# These are not part of the public LB contract and should not be documented as
# public API. Finance ownership lives in finance-service.
@app.get("/api/merchant/income-status", include_in_schema=False, deprecated=True)
def get_merchant_income(merchant_id: int, db: Session = Depends(get_db)):
    service = MerchantService(db)
    return service.get_income_status(merchant_id)


@app.get("/api/merchant/test-connection", include_in_schema=False, deprecated=True)
def test_db_connection(db: Session = Depends(get_db)):
    merchant = db.query(MerchantInfo).filter(MerchantInfo.id == 1).first()
    if not merchant:
        return {"status": "connected", "message": "Connected to DB, but merchant with ID 1 not found."}
    return {"status": "connected", "merchant_name": merchant.merchant_name}


@app.get("/api/merchant/payouts", include_in_schema=False, deprecated=True)
def get_merchant_payouts(merchant_id: int, db: Session = Depends(get_db)):
    records = db.query(Finance).filter(Finance.merchant_id == merchant_id).all()
    return [{"order_id": r.order_id, "settlement_amount": float(r.settlement_amount), "status": "payout_done"} for r in records]


@app.get("/api/merchant/monthly-total", include_in_schema=False, deprecated=True)
def get_merchant_monthly_total(merchant_id: int, db: Session = Depends(get_db)):
    # Simplified monthly total
    service = MerchantService(db)
    status = service.get_income_status(merchant_id)
    return {"monthly_total": status["total_income"]}


@app.get("/api/staff/expenses", include_in_schema=False, deprecated=True)
def get_staff_expenses(user_id: int, db: Session = Depends(get_db)):
    service = StaffService(db)
    return service.get_expenses(user_id)


@app.get("/api/staff/salary-deductions", include_in_schema=False, deprecated=True)
def get_staff_salary_deductions(user_id: int, db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.user_id == user_id, Order.order_status == 1).all()
    return [{"id": o.id, "total_amount": float(o.total_amount), "order_time": o.order_time} for o in orders]


@app.get("/api/finance/history", include_in_schema=False, deprecated=True)
def get_finance_history(db: Session = Depends(get_db)):
    records = db.query(Finance).all()
    return [{"id": r.id, "merchant_id": r.merchant_id, "order_id": r.order_id, "settlement_amount": float(r.settlement_amount), "report_data": r.report_data} for r in records]


@app.post("/api/finance/generate-report", include_in_schema=False, deprecated=True)
def generate_report(merchant_id: int, db: Session = Depends(get_db)):
    # This would typically trigger a Celery task
    return {"message": f"Report generation triggered for merchant {merchant_id}"}


@app.get("/user/{user_id}")
@app.get("/tagging/user/{user_id}", deprecated=True)
@app.get("/api/tagging/user/{user_id}", deprecated=True)
def get_user_tags(user_id: int, db: Session = Depends(get_db)):
    service = TaggingService(db)
    # Trigger update based on history
    service.update_user_tags_based_on_orders(user_id)
    tags = service.get_tags_by_user_id(user_id)
    return {"user_id": user_id, "tags": tags}


@app.post("/generate-barcode/{user_id}")
@app.post("/tagging/generate-barcode/{user_id}", deprecated=True)
@app.post("/api/tagging/generate-barcode/{user_id}", deprecated=True)
def generate_staff_barcode(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserInfo).filter(UserInfo.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Use Code128 barcode format
    EAN = barcode.get_barcode_class('code128')
    # Generate staff identification string, e.g., STAFF-001
    staff_code = f"STAFF-{user.id:03d}"
    my_barcode = EAN(staff_code, writer=ImageWriter())
    
    # Save barcode to buffer
    buffer = io.BytesIO()
    my_barcode.write(buffer)
    
    # Encode to Base64
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return {"user_id": user_id, "staff_code": staff_code, "barcode_base64": f"data:image/png;base64,{img_str}"}
