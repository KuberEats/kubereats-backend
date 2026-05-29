import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql://postgres:test@localhost:5432/testdb"
)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import kubereats  # noqa: F401 - register all models
from app.models.kubereats import Menu, MerchantInfo, Order, OrderItem, UserInfo
from app.repo.merchant_repo import MerchantRepository
from app.services.merchant_service import MerchantService

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:test@localhost:5432/testdb"
)

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
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.expire_all()
            session.begin_nested()

    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def merchant_service(db):
    return MerchantService(merchant_repo=MerchantRepository(db))


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
def test_merchant(db, test_user):
    merchant = MerchantInfo(
        user_id=test_user.id,
        merchant_name="Test Shop",
        campus="Main",
        category="Food",
        min_order=50,
        max_order_quantity=10,
        delivery_time="30 mins",
        tags=["fast", "cheap"],
        audit_status=0,
    )
    db.add(merchant)
    db.flush()
    return merchant


@pytest.fixture
def approved_merchant(db, test_user):
    merchant = MerchantInfo(
        user_id=test_user.id,
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


@pytest.fixture
def test_menu(db, approved_merchant):
    menu = Menu(
        merchant_id=approved_merchant.id,
        item_name="Burger",
        price=120,
        max_daily_quantity=20,
    )
    db.add(menu)
    db.flush()
    return menu


@pytest.fixture
def today_pending_order(db, test_user, test_menu):
    """An order placed today with status=0 (pending), containing test_menu."""
    order = Order(
        user_id=test_user.id,
        total_amount=120,
        order_status=0,
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        menu_id=test_menu.id,
        quantity=1,
        unit_price=120,
        subtotal=120,
    )
    db.add(item)
    db.flush()
    return order
