from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserInfo(TimestampMixin, Base):
    __tablename__ = "user_info"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class RefreshToken(TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_info.id"), nullable=False)
    token = Column(String(500), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("UserInfo", back_populates="refresh_tokens")
