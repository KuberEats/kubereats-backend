from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.metrics import auth_login_total, auth_register_total, auth_token_refresh_total
from app.database import get_db
from app.models.kubereats import UserInfo
from app.repo.user_repo import UserRepository
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service(db: Session = Depends(get_db)):
    return AuthService(user_repo=UserRepository(db))


@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    data: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
):
    result = service.register(data)
    auth_register_total.inc()
    return result


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    result = service.login(data.username, data.password)
    auth_login_total.labels(outcome="success").inc()
    return result


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    data: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
):
    result = service.refresh(data.refresh_token)
    auth_token_refresh_total.labels(outcome="success").inc()
    return result


@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserInfo = Depends(get_current_user)):
    return current_user
