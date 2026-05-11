from fastapi import HTTPException, status

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.kubereats import RefreshToken, UserInfo
from app.repo.user_repo import UserRepository
from app.schemas.auth import RegisterRequest


class AuthService:
    VALID_ROLES = {"employee", "merchant", "committee"}

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def register(self, data: RegisterRequest) -> UserInfo:
        if data.role not in self.VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role",
            )

        if self.user_repo.get_by_username(data.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists",
            )

        if data.email and self.user_repo.get_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            )

        user = self.user_repo.create_user(
            UserInfo(
                username=data.username,
                hashed_password=hash_password(data.password),
                email=data.email,
                role=data.role,
            )
        )
        self.user_repo.commit()
        return user

    def login(self, username: str, password: str) -> dict:
        user = self.user_repo.get_by_username(username)

        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        access_token = create_access_token(user.id, user.role)
        refresh_token_str, expires_at = create_refresh_token(user.id)

        self.user_repo.save_refresh_token(
            RefreshToken(
                user_id=user.id,
                token=refresh_token_str,
                expires_at=expires_at,
            )
        )
        self.user_repo.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "bearer",
        }

    def refresh(self, refresh_token_str: str) -> dict:
        payload = decode_token(refresh_token_str)

        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        stored_token = self.user_repo.get_refresh_token(refresh_token_str)

        if not stored_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found or expired",
            )

        user = self.user_repo.get_by_id(stored_token.user_id)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        self.user_repo.delete_refresh_token(refresh_token_str)

        access_token = create_access_token(user.id, user.role)
        new_refresh_str, expires_at = create_refresh_token(user.id)

        self.user_repo.save_refresh_token(
            RefreshToken(
                user_id=user.id,
                token=new_refresh_str,
                expires_at=expires_at,
            )
        )
        self.user_repo.commit()

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_str,
            "token_type": "bearer",
        }
