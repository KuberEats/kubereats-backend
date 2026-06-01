import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.tagging import TaggingService, MerchantService, StaffService
from app.models import UserInfo, Order, Tag, Finance, MerchantInfo


def test_public_tagging_routes_are_registered():
    routes = {route.path for route in app.routes}

    assert "/health" in routes
    assert "/user/{user_id}" in routes
    assert "/generate-barcode/{user_id}" in routes
    assert "/tagging/health" in routes
    assert "/tagging/user/{user_id}" in routes
    assert "/tagging/generate-barcode/{user_id}" in routes
    assert "/api/tagging/user/{user_id}" in routes
    assert "/api/tagging/generate-barcode/{user_id}" in routes


def test_metrics_endpoint_exposes_tagging_app_metrics():
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "tagging_http_requests_total" in response.text
    assert "tagging_user_tag_sync_total" in response.text

def test_get_tags_by_user_id(db_session):
    # Setup
    user = UserInfo(username="testuser", hashed_password="pw", role="user")
    tag = Tag(name="TestTag")
    user.tags.append(tag)
    db_session.add(user)
    db_session.commit()

    service = TaggingService(db_session)
    tags = service.get_tags_by_user_id(user.id)
    
    assert "TestTag" in tags
    assert len(tags) == 1

def test_get_tags_non_existent_user(db_session):
    service = TaggingService(db_session)
    tags = service.get_tags_by_user_id(999)
    assert tags == []

def test_update_user_tags_staff(db_session):
    user = UserInfo(username="staffuser", hashed_password="pw", role="staff")
    db_session.add(user)
    db_session.commit()

    service = TaggingService(db_session)
    service.update_user_tags_based_on_orders(user.id)
    
    tags = service.get_tags_by_user_id(user.id)
    assert f"STAFF-{user.id:03d}" in tags

def test_update_user_tags_frequent_buyer(db_session):
    user = UserInfo(username="buyer", hashed_password="pw", role="user")
    db_session.add(user)
    db_session.commit()

    # Add 11 orders
    for i in range(11):
        order = Order(user_id=user.id, total_amount=10)
        db_session.add(order)
    db_session.commit()

    service = TaggingService(db_session)
    service.update_user_tags_based_on_orders(user.id)
    
    tags = service.get_tags_by_user_id(user.id)
    assert "Frequent Buyer" in tags

def test_update_user_tags_big_spender(db_session):
    user = UserInfo(username="spender", hashed_password="pw", role="user")
    db_session.add(user)
    db_session.commit()

    # Add 1 order with > 1000 spent
    order = Order(user_id=user.id, total_amount=1001)
    db_session.add(order)
    db_session.commit()

    service = TaggingService(db_session)
    service.update_user_tags_based_on_orders(user.id)
    
    tags = service.get_tags_by_user_id(user.id)
    assert "Big Spender" in tags

def test_merchant_get_income_status(db_session):
    # Setup user and merchant
    user = UserInfo(username="merchant_user", hashed_password="pw", role="merchant")
    db_session.add(user)
    db_session.flush()
    
    merchant = MerchantInfo(
        user_id=user.id, 
        merchant_name="Test Store", 
        campus="Main", 
        category="Food", 
        delivery_time="30m"
    )
    db_session.add(merchant)
    db_session.flush()

    # Add finance records
    order = Order(user_id=user.id, total_amount=100)
    db_session.add(order)
    db_session.flush()
    
    f1 = Finance(merchant_id=merchant.id, order_id=order.id, settlement_amount=50.5)
    f2 = Finance(merchant_id=merchant.id, order_id=order.id, settlement_amount=49.5)
    db_session.add_all([f1, f2])
    db_session.commit()

    service = MerchantService(db_session)
    status = service.get_income_status(merchant.id)
    
    assert status["total_income"] == 100.0
    assert status["order_count"] == 2

def test_staff_get_expenses(db_session):
    user = UserInfo(username="staff", hashed_password="pw", role="staff")
    db_session.add(user)
    db_session.commit()

    # Add orders with status 1 (completed) and 0 (pending)
    o1 = Order(user_id=user.id, total_amount=100, order_status=1)
    o2 = Order(user_id=user.id, total_amount=200, order_status=0)
    db_session.add_all([o1, o2])
    db_session.commit()

    service = StaffService(db_session)
    expenses = service.get_expenses(user.id)
    
    assert expenses["total_expense"] == 100.0
    assert expenses["order_count"] == 1
