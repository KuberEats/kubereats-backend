from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, JSON,
    Numeric, String,
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


class MerchantInfo(TimestampMixin, Base):
    __tablename__ = "merchant_info"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_info.id"), unique=True, nullable=False)
    merchant_name = Column(String(100), nullable=False)
    campus = Column(String(20), nullable=False)
    category = Column(String(50), nullable=False)
    rating = Column(Numeric(2, 1), default=0, nullable=False)
    order_count = Column(Integer, default=0, nullable=False)
    min_order = Column(Numeric(10, 2), default=0, nullable=False)
    max_order_quantity = Column(Integer, default=0, nullable=False)
    delivery_time = Column(String(50), nullable=False)
    tags = Column(JSON, default=list, nullable=False)
    audit_status = Column(Integer, default=0, nullable=False)

    user = relationship("UserInfo")
