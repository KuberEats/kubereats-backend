import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest


def _register_user(auth_service, username="user1", role="merchant"):
    return auth_service.register(
        RegisterRequest(username=username, password="password123", role=role)
    )


# ── Register ──


def test_register_success(auth_service):
    user = _register_user(auth_service)
    assert user.username == "user1"
    assert user.role == "merchant"


def test_register_invalid_role_raises_validation_error(auth_service):
    with pytest.raises(ValidationError):
        RegisterRequest(username="user1", password="password123", role="admin")


def test_register_duplicate_username_raises_409(auth_service):
    _register_user(auth_service, username="user1")
    with pytest.raises(HTTPException) as exc:
        _register_user(auth_service, username="user1")
    assert exc.value.status_code == 409


def test_register_duplicate_email_raises_409(auth_service):
    auth_service.register(
        RegisterRequest(
            username="user1",
            password="password123",
            role="merchant",
            email="a@test.com",
        )
    )
    with pytest.raises(HTTPException) as exc:
        auth_service.register(
            RegisterRequest(
                username="user2",
                password="password123",
                role="merchant",
                email="a@test.com",
            )
        )
    assert exc.value.status_code == 409


# ── Login ──


def test_login_success(auth_service):
    _register_user(auth_service)
    result = auth_service.login("user1", "password123")
    assert "access_token" in result
    assert "refresh_token" in result
    assert result["token_type"] == "bearer"


def test_login_wrong_username_raises_401(auth_service):
    with pytest.raises(HTTPException) as exc:
        auth_service.login("nobody", "password123")
    assert exc.value.status_code == 401


def test_login_wrong_password_raises_401(auth_service):
    _register_user(auth_service)
    with pytest.raises(HTTPException) as exc:
        auth_service.login("user1", "wrongpassword")
    assert exc.value.status_code == 401


def test_login_inactive_user_raises_403(auth_service, db):
    user = _register_user(auth_service)
    user.is_active = False
    db.flush()
    with pytest.raises(HTTPException) as exc:
        auth_service.login("user1", "password123")
    assert exc.value.status_code == 403


# ── Refresh ──


def test_refresh_success(auth_service):
    _register_user(auth_service)
    tokens = auth_service.login("user1", "password123")
    result = auth_service.refresh(tokens["refresh_token"])
    assert "access_token" in result
    assert "refresh_token" in result
    assert result["token_type"] == "bearer"


def test_refresh_old_token_is_invalidated(auth_service):
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch

    _register_user(auth_service)
    tokens = auth_service.login("user1", "password123")

    new_expire = datetime.now(timezone.utc) + timedelta(days=7)
    with patch(
        "app.services.auth_service.create_refresh_token",
        return_value=("new-unique-rotated-token", new_expire),
    ):
        auth_service.refresh(tokens["refresh_token"])

    with pytest.raises(HTTPException) as exc:
        auth_service.refresh(tokens["refresh_token"])
    assert exc.value.status_code == 401


def test_refresh_invalid_token_raises_401(auth_service):
    with pytest.raises(HTTPException) as exc:
        auth_service.refresh("not.a.valid.token")
    assert exc.value.status_code == 401
