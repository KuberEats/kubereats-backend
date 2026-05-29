from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.schemas.merchant import (
    MerchantApplyRequest,
    MerchantUpdateRequest,
    MenuCreateRequest,
    MenuUpdateRequest,
)


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


# ── Menu ──


def test_create_menu_item_success(merchant_service, approved_merchant):
    data = MenuCreateRequest(
        item_name="Fried Rice",
        price=Decimal("80"),
        max_daily_quantity=15,
    )
    result = merchant_service.create_menu_item(approved_merchant.user_id, data)
    assert result.item_name == "Fried Rice"
    assert result.merchant_id == approved_merchant.id


def test_create_menu_item_not_approved_raises_403(merchant_service, test_merchant):
    data = MenuCreateRequest(
        item_name="Fried Rice",
        price=Decimal("80"),
        max_daily_quantity=15,
    )
    with pytest.raises(HTTPException) as exc:
        merchant_service.create_menu_item(test_merchant.user_id, data)
    assert exc.value.status_code == 403


def test_list_menu_items(merchant_service, approved_merchant, test_menu):
    result = merchant_service.list_menu_items(approved_merchant.user_id)
    assert len(result) == 1
    assert result[0].item_name == "Burger"


def test_update_menu_item_success(merchant_service, approved_merchant, test_menu):
    data = MenuUpdateRequest(item_name="Cheeseburger")
    result = merchant_service.update_menu_item(
        approved_merchant.user_id, test_menu.id, data
    )
    assert result.item_name == "Cheeseburger"


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
