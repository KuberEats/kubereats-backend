import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql://postgres:test@localhost:5432/testdb"
)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import kubereats  # noqa: F401 - register all models
from app.models.kubereats import MerchantInfo, UserInfo
from app.repo.committee_repo import CommitteeRepository
from app.services.committee_service import CommitteeService

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def committee_service(db):
    return CommitteeService(committee_repo=CommitteeRepository(db))


@pytest.fixture
def test_user(db):
    user = UserInfo(
        username="testmerchant",
        email="merchant@test.com",
        hashed_password="hashed",
        role="merchant",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def pending_merchant(db, test_user):
    merchant = MerchantInfo(
        user_id=test_user.id,
        merchant_name="Pending Shop",
        campus="Main",
        category="Food",
        min_order=50,
        max_order_quantity=10,
        delivery_time="30 mins",
        tags=[],
        audit_status=0,
    )
    db.add(merchant)
    db.flush()
    return merchant


@pytest.fixture
def approved_merchant(db):
    user = UserInfo(
        username="approveduser",
        email="approved@test.com",
        hashed_password="hashed",
        role="merchant",
        is_active=True,
    )
    db.add(user)
    db.flush()
    merchant = MerchantInfo(
        user_id=user.id,
        merchant_name="Approved Shop",
        campus="Main",
        category="Food",
        min_order=50,
        max_order_quantity=10,
        delivery_time="30 mins",
        tags=[],
        audit_status=1,
    )
    db.add(merchant)
    db.flush()
    return merchant
