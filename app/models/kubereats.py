from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TimestampMixin:
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
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
    cooperation_start_date = Column(Date, nullable=True)
    cooperation_end_date = Column(Date, nullable=True)
    suspended_at = Column(DateTime(timezone=True), nullable=True)
    suspension_reason = Column(Text, nullable=True)

    user = relationship("UserInfo")
    menus = relationship(
        "Menu",
        back_populates="merchant",
        cascade="all, delete-orphan",
    )


class Menu(TimestampMixin, Base):
    __tablename__ = "menu"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant_info.id"), nullable=False)
    item_name = Column(String(100), nullable=False)
    max_daily_quantity = Column(Integer, default=0, nullable=False)
    image_url = Column(String(255))
    price = Column(Numeric(10, 2), nullable=False)
    dietary_type = Column(String(32), default="MEAT", nullable=False)
    allergens = Column(JSON, default=list, nullable=False)
    certifications = Column(JSON, default=list, nullable=False)
    calories_kcal = Column(Integer, nullable=True)
    protein_g = Column(Numeric(8, 2), nullable=True)
    carbs_g = Column(Numeric(8, 2), nullable=True)
    fat_g = Column(Numeric(8, 2), nullable=True)
    sodium_mg = Column(Numeric(8, 2), nullable=True)
    sugar_g = Column(Numeric(8, 2), nullable=True)
    serving_size = Column(String(50), nullable=True)
    ingredients = Column(Text, nullable=True)

    merchant = relationship("MerchantInfo", back_populates="menus")
    order_items = relationship("OrderItem", back_populates="menu")


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_info.id"), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    order_status = Column(Integer, default=0, nullable=False)
    order_time = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    menu_id = Column(Integer, ForeignKey("menu.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    menu = relationship("Menu", back_populates="order_items")
