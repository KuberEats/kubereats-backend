from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.notification import NotificationStatus
from app.templates.registry import Recipient


class CreateEmailNotificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    templateKey: str
    recipient: Recipient
    locale: str = "zh-TW"
    payload: dict[str, Any]


class CreateEmailNotificationResponse(BaseModel):
    notificationId: str
    status: str
    duplicate: bool


class NotificationStatusResponse(BaseModel):
    notificationId: str
    templateKey: str
    templateVersion: int
    sourceService: str
    recipientType: str
    status: NotificationStatus
    attemptCount: int
    providerMessageId: str | None
    createdAt: datetime
    sentAt: datetime | None


class QueueMessage(BaseModel):
    notificationId: str
    correlationId: str = Field(min_length=1)
