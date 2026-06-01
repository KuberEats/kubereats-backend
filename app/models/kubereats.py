from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

# Association table for User <-> Tag
user_tags = Table(
    "user_tags",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user_info.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    users = relationship("UserInfo", secondary=user_tags, back_populates="tags")


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
    image_url = Column(String(255))
    price = Column(Numeric(10, 2), nullable=False)

    merchant = relationship("MerchantInfo", back_populates="menus")
    order_items = relationship("OrderItem", back_populates="menu")


# Isolated table to track daily capacity of each menu item, separate from Menu to avoid concurrency issues when multiple orders are placed simultaneously.
class MenuDailyCapacity(TimestampMixin, Base):
    __tablename__ = "menu_daily_capacity"
    __table_args__ = (
        UniqueConstraint(
            "menu_id", "target_date", name="uq_menu_daily_capacity_menu_date"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    menu_id = Column(Integer, ForeignKey("menu.id"), nullable=False)
    target_date = Column(Date, nullable=False)
    max_quantity = Column(Integer, nullable=False)
    remaining_quantity = Column(Integer, nullable=False)

    menu = relationship("Menu")


class UserInfo(TimestampMixin, Base):
    __tablename__ = "user_info"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    orders = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    tags = relationship("Tag", secondary=user_tags, back_populates="users")


class RefreshToken(TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_info.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)

    user = relationship("UserInfo", back_populates="refresh_tokens")


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("order_number", name="uq_orders_order_number"),
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_orders_user_id_idempotency_key"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_info.id"), nullable=False)
    order_number = Column(String(32), nullable=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    order_status = Column(Integer, default=0, nullable=False)
    order_time = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    service_date = Column(Date, nullable=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    dispatch_at = Column(DateTime(timezone=True), nullable=True)
    schedule_status = Column(String(32), default="not_scheduled", nullable=False)
    idempotency_key = Column(String(255), nullable=True)
    idempotency_request_hash = Column(String(64), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)

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


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(Integer, primary_key=True, index=True)
    aggregate_type = Column(String(64), nullable=False)
    aggregate_id = Column(Integer, nullable=False)
    event_type = Column(String(128), nullable=False)
    payload_json = Column(JSON, nullable=False)
    available_at = Column(DateTime(timezone=True), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReservationRequest(TimestampMixin, Base):
    __tablename__ = "reservation_requests"
    __table_args__ = (
        UniqueConstraint(
            "reservation_token",
            name="uq_reservation_requests_reservation_token",
        ),
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_reservation_requests_user_id_idempotency_key",
        ),
        Index(
            "ix_reservation_requests_status_created_at",
            "status",
            "created_at",
        ),
        Index(
            "ix_reservation_requests_lease_until",
            "lease_until",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    reservation_token = Column(String(64), nullable=False)
    user_id = Column(Integer, ForeignKey("user_info.id"), nullable=False)
    merchant_id = Column(Integer, ForeignKey("merchant_info.id"), nullable=False)
    service_date = Column(Date, nullable=False)
    pickup_slot = Column(String(64), nullable=False, default="")
    pickup_option = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="PENDING_RESERVATION")
    idempotency_key = Column(String(255), nullable=True)
    idempotency_request_hash = Column(String(64), nullable=True)
    failure_reason = Column(Text, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    lease_until = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    user = relationship("UserInfo")
    merchant = relationship("MerchantInfo")
    items = relationship(
        "ReservationRequestItem",
        back_populates="reservation_request",
        cascade="all, delete-orphan",
    )


class ReservationRequestItem(TimestampMixin, Base):
    __tablename__ = "reservation_request_items"

    id = Column(Integer, primary_key=True, index=True)
    reservation_request_id = Column(
        Integer,
        ForeignKey("reservation_requests.id"),
        nullable=False,
    )
    menu_item_id = Column(Integer, ForeignKey("menu.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=True)
    subtotal = Column(Numeric(10, 2), nullable=True)

    reservation_request = relationship(
        "ReservationRequest",
        back_populates="items",
    )
    menu = relationship("Menu")


class ReservationCapacitySlot(TimestampMixin, Base):
    __tablename__ = "reservation_capacity_slots"
    __table_args__ = (
        UniqueConstraint(
            "merchant_id",
            "menu_item_id",
            "service_date",
            "pickup_slot",
            name="uq_reservation_capacity_slot_key",
        ),
        CheckConstraint(
            "total_capacity >= 0",
            name="ck_reservation_capacity_total_nonnegative",
        ),
        CheckConstraint(
            "reserved_count >= 0",
            name="ck_reservation_capacity_reserved_nonnegative",
        ),
        CheckConstraint(
            "reserved_count <= total_capacity",
            name="ck_reservation_capacity_not_oversold",
        ),
        Index(
            "ix_reservation_capacity_lookup",
            "merchant_id",
            "menu_item_id",
            "service_date",
            "pickup_slot",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchant_info.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu.id"), nullable=False)
    service_date = Column(Date, nullable=False)
    pickup_slot = Column(String(64), nullable=False, default="")
    total_capacity = Column(Integer, nullable=False)
    reserved_count = Column(Integer, default=0, nullable=False)

    merchant = relationship("MerchantInfo")
    menu = relationship("Menu")


class ReservationOutboxEvent(TimestampMixin, Base):
    __tablename__ = "reservation_outbox_events"
    __table_args__ = (
        CheckConstraint(
            "retry_count >= 0",
            name="ck_reservation_outbox_retry_count_nonnegative",
        ),
        Index(
            "ix_reservation_outbox_status_next_retry",
            "status",
            "next_retry_at",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(128), nullable=False)
    aggregate_type = Column(String(64), nullable=False)
    aggregate_id = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    ordering_key = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="PENDING")
    retry_count = Column(Integer, default=0, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
