from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.kubereats import Menu, MerchantInfo, UserInfo
from app.schemas.merchant import (
    MerchantApplyRequest,
    MerchantUpdateRequest,
    MenuCreateRequest,
    MenuUpdateRequest,
)


def create_public_merchant(
    db,
    username: str,
    merchant_name: str,
    campus: str,
    rating: Decimal,
    order_count: int,
    audit_status: int = 1,
    cooperation_start_date=None,
    cooperation_end_date=None,
):
    user = UserInfo(
        username=username,
        email=f"{username}@test.com",
        hashed_password="hashed",
        role="merchant",
        is_active=True,
    )
    db.add(user)
    db.flush()

    merchant = MerchantInfo(
        user_id=user.id,
        merchant_name=merchant_name,
        campus=campus,
        category="Food",
        rating=rating,
        order_count=order_count,
        min_order=50,
        max_order_quantity=10,
        delivery_time="30 mins",
        tags=["lunch"],
        audit_status=audit_status,
        cooperation_start_date=cooperation_start_date,
        cooperation_end_date=cooperation_end_date,
    )
    db.add(merchant)
    db.flush()
    return merchant


# ── Merchant ──


def test_apply_success(merchant_service, test_user):
    data = MerchantApplyRequest(
        merchant_name="New Shop",
        campus="North",
        category="Drinks",
        min_order=Decimal("30"),
        max_order_quantity=5,
        delivery_time="20 mins",
        tags=["cold"],
    )
    result = merchant_service.apply(test_user.id, data)
    assert result.merchant_name == "New Shop"
    assert result.audit_status == 0


def test_apply_duplicate_raises_409(merchant_service, test_merchant):
    data = MerchantApplyRequest(
        merchant_name="Another Shop",
        campus="North",
        category="Drinks",
        min_order=Decimal("30"),
        max_order_quantity=5,
        delivery_time="20 mins",
    )
    with pytest.raises(HTTPException) as exc:
        merchant_service.apply(test_merchant.user_id, data)
    assert exc.value.status_code == 409


def test_get_my_merchant_success(merchant_service, test_merchant):
    result = merchant_service.get_my_merchant(test_merchant.user_id)
    assert result.id == test_merchant.id


def test_get_my_merchant_not_found_raises_404(merchant_service):
    with pytest.raises(HTTPException) as exc:
        merchant_service.get_my_merchant(user_id=99999)
    assert exc.value.status_code == 404


def test_update_my_merchant_success(merchant_service, test_merchant):
    data = MerchantUpdateRequest(merchant_name="Updated Shop")
    result = merchant_service.update_my_merchant(test_merchant.user_id, data)
    assert result.merchant_name == "Updated Shop"


def test_update_my_merchant_no_fields_raises_400(merchant_service, test_merchant):
    data = MerchantUpdateRequest()
    with pytest.raises(HTTPException) as exc:
        merchant_service.update_my_merchant(test_merchant.user_id, data)
    assert exc.value.status_code == 400


# ── Public Catalog ──


def test_list_public_merchants_filters_approved_by_campus(db, merchant_service):
    visible = create_public_merchant(
        db, "visible", "Visible Shop", "竹科", Decimal("4.5"), 10
    )
    create_public_merchant(
        db, "other-campus", "Other Campus Shop", "南科", Decimal("5.0"), 99
    )
    create_public_merchant(
        db,
        "pending",
        "Pending Shop",
        "竹科",
        Decimal("5.0"),
        99,
        audit_status=0,
    )

    result = merchant_service.list_public_merchants(
        "竹科", target_date=date.today(), sort_by="recommend"
    )

    assert [merchant.id for merchant in result] == [visible.id]


def test_list_public_merchants_excludes_expired_cooperation(db, merchant_service):
    create_public_merchant(
        db,
        "expired",
        "Expired Shop",
        "竹科",
        Decimal("4.5"),
        10,
        cooperation_start_date=date.today() - timedelta(days=30),
        cooperation_end_date=date.today() - timedelta(days=1),
    )

    result = merchant_service.list_public_merchants(
        "竹科", target_date=date.today(), sort_by="recommend"
    )

    assert result == []


def test_list_public_merchants_sorts_by_people(db, merchant_service):
    create_public_merchant(db, "people-low", "Low", "竹科", Decimal("5.0"), 3)
    high = create_public_merchant(db, "people-high", "High", "竹科", Decimal("3.0"), 20)

    result = merchant_service.list_public_merchants(
        "竹科", target_date=date.today(), sort_by="people"
    )

    assert result[0].id == high.id


def test_list_public_merchants_sorts_by_popular(db, merchant_service):
    create_public_merchant(db, "popular-low", "Low", "竹科", Decimal("3.0"), 99)
    high = create_public_merchant(db, "popular-high", "High", "竹科", Decimal("4.9"), 1)

    result = merchant_service.list_public_merchants(
        "竹科", target_date=date.today(), sort_by="popular"
    )

    assert result[0].id == high.id


def test_list_public_merchants_sorts_by_recommend(db, merchant_service):
    create_public_merchant(db, "recommend-low", "Low", "竹科", Decimal("3.0"), 10)
    high = create_public_merchant(
        db, "recommend-high", "High", "竹科", Decimal("4.8"), 2
    )

    result = merchant_service.list_public_merchants(
        "竹科", target_date=date.today(), sort_by="recommend"
    )

    assert result[0].id == high.id


def test_get_public_merchant_detail_requires_approved(merchant_service, test_merchant):
    with pytest.raises(HTTPException) as exc:
        merchant_service.get_public_merchant_detail(test_merchant.id)

    assert exc.value.status_code == 404


def test_list_public_menu_items(db, merchant_service, approved_merchant, test_menu):
    second_menu = Menu(
        merchant_id=approved_merchant.id,
        item_name="Fries",
        price=60,
        max_daily_quantity=30,
    )
    db.add(second_menu)
    db.flush()

    result = merchant_service.list_public_menu_items(approved_merchant.id)

    assert [menu.item_name for menu in result] == ["Burger", "Fries"]


# ── Menu ──


def test_create_menu_item_success(merchant_service, approved_merchant):
    data = MenuCreateRequest(
        item_name="Fried Rice",
        price=Decimal("80"),
        max_daily_quantity=15,
        dietary_type="OVO_LACTO",
        allergens=["蛋", "奶"],
        certifications=["SGS"],
        calories_kcal=620,
        protein_g=Decimal("24.5"),
        carbs_g=Decimal("82.0"),
        fat_g=Decimal("18.5"),
        sodium_mg=Decimal("780"),
        sugar_g=Decimal("6.5"),
        serving_size="1 份",
        ingredients="白飯、蛋、青菜",
    )
    result = merchant_service.create_menu_item(approved_merchant.user_id, data)
    assert result.item_name == "Fried Rice"
    assert result.merchant_id == approved_merchant.id
    assert result.dietary_type == "OVO_LACTO"
    assert result.allergens == ["蛋", "奶"]
    assert result.certifications == ["SGS"]
    assert result.calories_kcal == 620
    assert result.protein_g == Decimal("24.5")
    assert result.serving_size == "1 份"
    assert result.ingredients == "白飯、蛋、青菜"


def test_create_menu_item_not_approved_raises_403(merchant_service, test_merchant):
    data = MenuCreateRequest(
        item_name="Fried Rice",
        price=Decimal("80"),
        max_daily_quantity=15,
    )
    with pytest.raises(HTTPException) as exc:
        merchant_service.create_menu_item(test_merchant.user_id, data)
    assert exc.value.status_code == 403


def test_create_menu_item_expired_cooperation_raises_403(
    merchant_service, approved_merchant
):
    approved_merchant.cooperation_start_date = date.today() - timedelta(days=30)
    approved_merchant.cooperation_end_date = date.today() - timedelta(days=1)
    data = MenuCreateRequest(
        item_name="Fried Rice",
        price=Decimal("80"),
        max_daily_quantity=15,
    )

    with pytest.raises(HTTPException) as exc:
        merchant_service.create_menu_item(approved_merchant.user_id, data)

    assert exc.value.status_code == 403


def test_list_menu_items(merchant_service, approved_merchant, test_menu):
    result = merchant_service.list_menu_items(approved_merchant.user_id)
    assert len(result) == 1
    assert result[0].item_name == "Burger"


def test_update_menu_item_success(merchant_service, approved_merchant, test_menu):
    data = MenuUpdateRequest(
        item_name="Cheeseburger",
        dietary_type="MEAT",
        allergens=["麩質"],
        certifications=["HACCP"],
        calories_kcal=700,
        protein_g=Decimal("30"),
        ingredients="牛肉、麵包",
    )
    result = merchant_service.update_menu_item(
        approved_merchant.user_id, test_menu.id, data
    )
    assert result.item_name == "Cheeseburger"
    assert result.allergens == ["麩質"]
    assert result.certifications == ["HACCP"]
    assert result.calories_kcal == 700
    assert result.protein_g == Decimal("30")
    assert result.ingredients == "牛肉、麵包"


def test_update_menu_item_not_found_raises_404(merchant_service, approved_merchant):
    data = MenuUpdateRequest(item_name="Ghost Item")
    with pytest.raises(HTTPException) as exc:
        merchant_service.update_menu_item(approved_merchant.user_id, 99999, data)
    assert exc.value.status_code == 404


def test_update_menu_item_no_fields_raises_400(
    merchant_service, approved_merchant, test_menu
):
    data = MenuUpdateRequest()
    with pytest.raises(HTTPException) as exc:
        merchant_service.update_menu_item(approved_merchant.user_id, test_menu.id, data)
    assert exc.value.status_code == 400


def test_delete_menu_item_success(merchant_service, approved_merchant, test_menu):
    merchant_service.delete_menu_item(approved_merchant.user_id, test_menu.id)
    result = merchant_service.list_menu_items(approved_merchant.user_id)
    assert len(result) == 0


def test_delete_menu_item_not_found_raises_404(merchant_service, approved_merchant):
    with pytest.raises(HTTPException) as exc:
        merchant_service.delete_menu_item(approved_merchant.user_id, 99999)
    assert exc.value.status_code == 404


# ── Confirm Today Orders ──


def test_confirm_today_orders_success(
    merchant_service, approved_merchant, today_pending_order
):
    result = merchant_service.confirm_today_orders(approved_merchant.user_id)
    assert result["confirmed_count"] == 1
    assert today_pending_order.order_status == 1


def test_confirm_today_orders_no_pending(merchant_service, approved_merchant):
    result = merchant_service.confirm_today_orders(approved_merchant.user_id)
    assert result["confirmed_count"] == 0


def test_confirm_today_orders_not_approved_raises_403(merchant_service, test_merchant):
    with pytest.raises(HTTPException) as exc:
        merchant_service.confirm_today_orders(test_merchant.user_id)
    assert exc.value.status_code == 403
