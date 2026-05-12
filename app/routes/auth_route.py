from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
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
    return service.register(data)


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    return service.login(data.username, data.password)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    data: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
):
    return service.refresh(data.refresh_token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserInfo = Depends(get_current_user)):
    return current_user
