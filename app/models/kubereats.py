from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
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


class MerchantInfo(TimestampMixin, Base):
    __tablename__ = "merchant_info"

    id = Column(Integer, primary_key=True, index=True)
    merchant_name = Column(String(100), nullable=False)
    campus = Column(String(20), nullable=False)
    category = Column(String(50), nullable=False)
    rating = Column(Numeric(2, 1), default=0, nullable=False)
    order_count = Column(Integer, default=0, nullable=False)
    min_order = Column(Numeric(10, 2), default=0, nullable=False)
    delivery_time = Column(String(50), nullable=False)
    tags = Column(JSON, default=list, nullable=False)
    audit_status = Column(Integer, default=0, nullable=False)

    menus = relationship(
        "Menu",
        back_populates="merchant",
        cascade="all, delete-orphan",
    )
    finances = relationship("Finance", back_populates="merchant")


class Menu(TimestampMixin, Base):
    __tablename__ = "menu"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant_info.id"), nullable=False)
    item_name = Column(String(100), nullable=False)
    max_daily_quantity = Column(Integer, default=0, nullable=False)
    image_id = Column(String(255))
    price = Column(Numeric(10, 2), nullable=False)

    merchant = relationship("MerchantInfo", back_populates="menus")
    order_items = relationship("OrderItem", back_populates="menu")


class UserInfo(TimestampMixin, Base):
    __tablename__ = "user_info"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    history_records = Column(Text)

    orders = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_info.id"), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    order_status = Column(Integer, default=0, nullable=False)
    order_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("UserInfo", back_populates="orders")
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    finance_records = relationship(
        "Finance",
        back_populates="order",
        cascade="all, delete-orphan",
    )


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


class Finance(TimestampMixin, Base):
    __tablename__ = "finance"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant_info.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    report_data = Column(JSON)
    settlement_amount = Column(Numeric(10, 2), nullable=False)

    merchant = relationship("MerchantInfo", back_populates="finances")
    order = relationship("Order", back_populates="finance_records")
