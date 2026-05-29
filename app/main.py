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
from sqlalchemy.exc import OperationalError
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup with retry logic
    max_retries = 5
    retry_interval = 5
    for i in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            print("Database tables created successfully")
            break
        except OperationalError as e:
            if i < max_retries - 1:
                print(f"Database connection failed, retrying in {retry_interval} seconds... ({i+1}/{max_retries})")
                time.sleep(retry_interval)
            else:
                print("Max retries reached. Database connection failed.")
                raise e
    yield

from sqlalchemy import text

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

@app.post("/api/seed")
def seed_data(db: Session = Depends(get_db)):
    # Create a user for the merchant
    merchant_user = db.query(UserInfo).filter(UserInfo.username == "merchant_user").first()
    if not merchant_user:
        merchant_user = UserInfo(
            username="merchant_user", 
            hashed_password="hashed_password", 
            role="merchant"
        )
        db.add(merchant_user)
        db.flush()

    # Create a merchant
    merchant = db.query(MerchantInfo).filter(MerchantInfo.merchant_name == "Kube Fried Chicken").first()
    if not merchant:
        merchant = MerchantInfo(
            user_id=merchant_user.id,
            merchant_name="Kube Fried Chicken", 
            campus="Main Campus",
            category="Fast Food",
            delivery_time="20-30 min",
            audit_status=1
        )
        db.add(merchant)
        db.flush()
    
    # Create a user (staff)
    user = db.query(UserInfo).filter(UserInfo.username == "staff_001").first()
    if not user:
        user = UserInfo(
            username="staff_001", 
            hashed_password="hashed_password", 
            role="staff"
        )
        db.add(user)
        db.flush()
    
    # Create some orders
    for i in range(5):
        order = Order(user_id=user.id, total_amount=decimal.Decimal("150.00"), order_status=1)
        db.add(order)
        db.flush()
        
        # Create finance record
        finance = Finance(
            merchant_id=merchant.id, 
            order_id=order.id, 
            settlement_amount=decimal.Decimal("135.00"), 
            report_data={"tax": "10%"}
        )
        db.add(finance)
    
    db.commit()
    return {"message": "Data seeded successfully"}

@app.get("/api/merchant/income-status")
def get_merchant_income(merchant_id: int, db: Session = Depends(get_db)):
    service = MerchantService(db)
    return service.get_income_status(merchant_id)

@app.get("/api/merchant/payouts")
def get_merchant_payouts(merchant_id: int, db: Session = Depends(get_db)):
    records = db.query(Finance).filter(Finance.merchant_id == merchant_id).all()
    return [{"order_id": r.order_id, "settlement_amount": float(r.settlement_amount), "status": "payout_done"} for r in records]

@app.get("/api/merchant/monthly-total")
def get_merchant_monthly_total(merchant_id: int, db: Session = Depends(get_db)):
    # Simplified monthly total
    service = MerchantService(db)
    status = service.get_income_status(merchant_id)
    return {"monthly_total": status["total_income"]}

@app.get("/api/staff/expenses")
def get_staff_expenses(user_id: int, db: Session = Depends(get_db)):
    service = StaffService(db)
    return service.get_expenses(user_id)

@app.get("/api/staff/salary-deductions")
def get_staff_salary_deductions(user_id: int, db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.user_id == user_id, Order.order_status == 1).all()
    return [{"id": o.id, "total_amount": float(o.total_amount), "order_time": o.order_time} for o in orders]

@app.get("/api/finance/history")
def get_finance_history(db: Session = Depends(get_db)):
    records = db.query(Finance).all()
    return [{"id": r.id, "merchant_id": r.merchant_id, "order_id": r.order_id, "settlement_amount": float(r.settlement_amount), "report_data": r.report_data} for r in records]

@app.post("/api/finance/generate-report")
def generate_report(merchant_id: int, db: Session = Depends(get_db)):
    # This would typically trigger a Celery task
    return {"message": f"Report generation triggered for merchant {merchant_id}"}

@app.get("/api/tagging/user/{user_id}")
def get_user_tags(user_id: int, db: Session = Depends(get_db)):
    service = TaggingService(db)
    # Trigger update based on history
    service.update_user_tags_based_on_orders(user_id)
    tags = service.get_tags_by_user_id(user_id)
    return {"user_id": user_id, "tags": tags}

@app.post("/api/tagging/generate-barcode/{user_id}")
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
