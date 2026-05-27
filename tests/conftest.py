import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        from fastapi.testclient import TestClient

        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def order_confirmed_payload():
    return {
        "templateKey": "employee.order.confirmed",
        "recipient": {
            "type": "EMPLOYEE",
            "id": "EMP001",
            "email": "employee@example.com",
            "name": "王小明",
        },
        "locale": "zh-TW",
        "payload": {
            "orderId": "ORD-20260601-0001",
            "vendorName": "健康便當",
            "pickupDate": "2026-06-03",
            "pickupTime": "12:00-12:30",
            "pickupLocation": "A 廠一樓領餐區",
            "amount": 120,
            "detailUrl": "https://food.example.com/orders/ORD-20260601-0001",
        },
    }
