from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class MerchantInfo(Base):
    __tablename__ = "merchant_info"

    id = Column(Integer, primary_key=True, index=True)
    merchant_name = Column(String(100), nullable=False)
    audit_status = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    menus = relationship("Menu", back_populates="merchant")
    finances = relationship("Finance", back_populates="merchant")


class Menu(Base):
    __tablename__ = "menu"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant_info.id"))
    item_name = Column(String(100), nullable=False)
    max_daily_quantity = Column(Integer, default=0)
    image_id = Column(String(255))
    price = Column(Numeric(10, 2), nullable=False)

    merchant = relationship("MerchantInfo", back_populates="menus")


class UserInfo(Base):
    __tablename__ = "user_info"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20))
    history_records = Column(Text)

    orders = relationship("Order", back_populates="user")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_info.id"))
    total_amount = Column(Numeric(10, 2), nullable=False)
    order_status = Column(Integer, default=0)
    order_time = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("UserInfo", back_populates="orders")
    finance_records = relationship("Finance", back_populates="order")


class Finance(Base):
    __tablename__ = "finance"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant_info.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))
    report_data = Column(JSON)
    settlement_amount = Column(Numeric(10, 2))

    merchant = relationship("MerchantInfo", back_populates="finances")
    order = relationship("Order", back_populates="finance_records")
