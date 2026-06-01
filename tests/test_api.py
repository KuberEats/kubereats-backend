import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base
from sqlalchemy.pool import StaticPool

# Setup for testing FastAPI
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to KubeEats Finance Microservice"}

def test_get_finance_history():
    response = client.get("/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_finance_history_prefixed_alias():
    response = client.get("/finance/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_finance_reports_prefixed_alias():
    response = client.get("/finance/reports")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_finance_history_legacy_api_alias():
    response = client.get("/api/finance/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_finance_public_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_finance_prefixed_health_alias():
    response = client.get("/finance/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_merchant_domain_alias_is_not_exposed_from_finance_service():
    response = client.get("/api/merchant/monthly-total?merchant_id=1")
    assert response.status_code == 404


def test_get_monthly_item_distribution_api():
    # Setup database with test data via override_get_db context
    db = TestingSessionLocal()
    
    from app import models
    from decimal import Decimal
    from datetime import datetime
    
    merchant = models.MerchantInfo(
        user_id=1,
        merchant_name="API Test Merchant",
        campus="Main",
        category="Food",
        delivery_time="30 min"
    )
    db.add(merchant)
    db.commit()
    
    burger = models.Menu(merchant_id=merchant.id, item_name="經典牛肉堡", price=Decimal("150.00"))
    db.add(burger)
    db.commit()
    
    order = models.Order(user_id=1, total_amount=Decimal("150.00"), order_status=1, order_time=datetime.now())
    db.add(order)
    db.commit()
    
    item = models.OrderItem(order_id=order.id, menu_id=burger.id, quantity=1, unit_price=Decimal("150.00"), subtotal=Decimal("150.00"))
    db.add(item)
    db.commit()
    
    merchant_id = merchant.id
    db.close()
    
    response = client.get(
        f"/merchant/monthly-item-distribution?merchant_id={merchant_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["itemName"] == "經典牛肉堡"
    assert data[0]["totalAmount"] == 150.0
    assert data[0]["percentage"] == 100.0


def test_generate_report_returns_download_url_without_celery():
    db = TestingSessionLocal()

    from app import models
    from decimal import Decimal

    merchant = models.MerchantInfo(
        user_id=1,
        merchant_name="Report Merchant",
        campus="Main",
        category="Food",
        delivery_time="30 min",
    )
    db.add(merchant)
    db.commit()

    order = models.Order(
        user_id=1,
        total_amount=Decimal("150.00"),
        order_status=1,
    )
    db.add(order)
    db.commit()

    db.add(
        models.Finance(
            merchant_id=merchant.id,
            order_id=order.id,
            settlement_amount=Decimal("135.00"),
        )
    )
    db.commit()
    merchant_id = merchant.id
    db.close()

    response = client.post(
        f"/finance/generate-report?merchant_id={merchant_id}",
        headers={
            "x-forwarded-proto": "https",
            "x-forwarded-host": "api.kubereats.click",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"].endswith(".pdf")
    assert data["url"] == (
        f"https://api.kubereats.click/finance/reports/{data['filename']}"
    )
