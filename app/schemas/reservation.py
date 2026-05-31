from datetime import date, datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


ReservationStatus = Literal[
    "PENDING_RESERVATION",
    "PROCESSING",
    "RESERVED",
    "SOLD_OUT",
    "CANCELLED",
    "EXPIRED",
    "FAILED",
]


class ReservationItemCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    menu_item_id: int = Field(
        validation_alias=AliasChoices("menu_item_id", "menuItemId", "menu_id", "menuId")
    )
    quantity: int = Field(gt=0)


class ReservationCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: int = Field(validation_alias=AliasChoices("user_id", "userId"))
    merchant_id: int = Field(validation_alias=AliasChoices("merchant_id", "merchantId"))
    service_date: date = Field(
        validation_alias=AliasChoices("service_date", "serviceDate")
    )
    pickup_slot: str | None = Field(
        default=None,
        validation_alias=AliasChoices("pickup_slot", "pickupSlot"),
    )
    pickup_option: str = Field(
        default="SELF_PICKUP",
        validation_alias=AliasChoices("pickup_option", "pickupOption"),
    )
    items: list[ReservationItemCreate] = Field(min_length=1)


class ReservationItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    menu_item_id: int = Field(serialization_alias="menuItemId")
    item_name: str = Field(serialization_alias="itemName")
    quantity: int
    unit_price: float | None = Field(default=None, serialization_alias="unitPrice")
    subtotal: float | None = None


class ReservationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reservation_id: int = Field(serialization_alias="reservationId")
    order_token: str = Field(serialization_alias="orderToken")
    status: ReservationStatus
    service_date: date = Field(serialization_alias="serviceDate")
    pickup_slot: str | None = Field(default=None, serialization_alias="pickupSlot")
    pickup_option: str = Field(serialization_alias="pickupOption")
    pickup_number: str | None = Field(default=None, serialization_alias="pickupNumber")
    message: str
    items: list[ReservationItemResponse] = Field(default_factory=list)
    failed_items: list[ReservationItemResponse] = Field(
        default_factory=list,
        serialization_alias="failedItems",
    )
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
    processed_at: datetime | None = Field(
        default=None, serialization_alias="processedAt"
    )
    cancelled_at: datetime | None = Field(
        default=None, serialization_alias="cancelledAt"
    )


class ReservationAcceptedResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reservation_id: int = Field(serialization_alias="reservationId")
    order_token: str = Field(serialization_alias="orderToken")
    status: ReservationStatus
    message: str


class ReservationRequestedTaskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("event_id", "eventId"),
    )
    event_type: str = Field(
        default="ReservationRequested",
        validation_alias=AliasChoices("event_type", "eventType"),
    )
    reservation_id: int = Field(
        validation_alias=AliasChoices("reservation_id", "reservationId")
    )
    reservation_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("reservation_token", "reservationToken"),
    )
    capacity_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("capacity_key", "capacityKey"),
    )
