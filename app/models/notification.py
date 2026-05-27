import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NotificationStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    RETRYING = "RETRYING"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


json_type = JSON().with_variant(JSONB, "postgresql")


class NotificationRequest(Base):
    __tablename__ = "notification_requests"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_notification_idempotency_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_service: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    recipient_type: Mapped[str] = mapped_column(String(40), nullable=False)
    recipient_id: Mapped[str] = mapped_column(String(120), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False)
    recipient_name: Mapped[str | None] = mapped_column(String(120))
    locale: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict] = mapped_column(json_type, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus), nullable=False, default=NotificationStatus.QUEUED
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_message_id: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=utc_now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    last_error_message: Mapped[str | None] = mapped_column(Text)

    attempts: Mapped[list["NotificationDeliveryAttempt"]] = relationship(
        back_populates="notification", cascade="all, delete-orphan"
    )


class NotificationDeliveryAttempt(Base):
    __tablename__ = "notification_delivery_attempts"
    __table_args__ = (
        UniqueConstraint("notification_id", "attempt_no", name="uq_delivery_attempt_no"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    notification_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("notification_requests.id"), nullable=False, index=True
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    notification: Mapped[NotificationRequest] = relationship(back_populates="attempts")
