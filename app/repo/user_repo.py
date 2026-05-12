from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.kubereats import RefreshToken, UserInfo


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> UserInfo | None:
        return self.db.query(UserInfo).filter(UserInfo.id == user_id).first()

    def get_by_username(self, username: str) -> UserInfo | None:
        return self.db.query(UserInfo).filter(UserInfo.username == username).first()

    def get_by_email(self, email: str) -> UserInfo | None:
        return self.db.query(UserInfo).filter(UserInfo.email == email).first()

    def create_user(self, user: UserInfo) -> UserInfo:
        self.db.add(user)
        self.db.flush()
        return user

    def save_refresh_token(self, refresh_token: RefreshToken) -> RefreshToken:
        self.db.add(refresh_token)
        self.db.flush()
        return refresh_token

    def get_refresh_token(self, token: str) -> RefreshToken | None:
        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.token == token,
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )

    def delete_refresh_token(self, token: str) -> None:
        self.db.query(RefreshToken).filter(RefreshToken.token == token).delete()
        self.db.flush()

    def delete_user_refresh_tokens(self, user_id: int) -> None:
        self.db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        self.db.flush()

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
