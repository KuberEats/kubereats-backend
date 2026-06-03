from datetime import datetime
from decimal import Decimal
from typing import Literal
from urllib.parse import quote

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_serializer


# ── Merchant ──


MerchantSortKey = Literal["people", "popular", "recommend"]


class MerchantApplyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    merchant_name: str = Field(
        max_length=100,
        validation_alias=AliasChoices("merchant_name", "merchantName"),
    )
    campus: str = Field(max_length=20)
    category: str = Field(max_length=50)
    min_order: Decimal = Field(
        default=Decimal("0"),
        validation_alias=AliasChoices("min_order", "minOrder"),
    )
    delivery_time: str = Field(
        max_length=50,
        validation_alias=AliasChoices("delivery_time", "deliveryTime"),
    )
    max_order_quantity: int = Field(
        default=0,
        validation_alias=AliasChoices("max_order_quantity", "maxOrderQuantity"),
    )
    tags: list[str] = Field(default_factory=list)


class MerchantUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    merchant_name: str | None = Field(
        default=None,
        max_length=100,
        validation_alias=AliasChoices("merchant_name", "merchantName"),
    )
    campus: str | None = Field(default=None, max_length=20)
    category: str | None = Field(default=None, max_length=50)
    min_order: Decimal | None = Field(
        default=None,
        validation_alias=AliasChoices("min_order", "minOrder"),
    )
    delivery_time: str | None = Field(
        default=None,
        max_length=50,
        validation_alias=AliasChoices("delivery_time", "deliveryTime"),
    )
    max_order_quantity: int | None = Field(
        default=None,
        validation_alias=AliasChoices("max_order_quantity", "maxOrderQuantity"),
    )
    tags: list[str] | None = None


class MerchantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    user_id: int = Field(serialization_alias="userId")
    merchant_name: str = Field(serialization_alias="merchantName")
    campus: str
    category: str
    rating: float
    order_count: int = Field(serialization_alias="orderCount")
    min_order: float = Field(serialization_alias="minOrder")
    max_order_quantity: int = Field(serialization_alias="maxOrderQuantity")
    delivery_time: str = Field(serialization_alias="deliveryTime")
    tags: list[str]
    audit_status: int = Field(serialization_alias="auditStatus")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class PublicMerchantListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    merchant_name: str = Field(serialization_alias="name")
    campus: str
    category: str
    rating: float
    order_count: int = Field(serialization_alias="orderCount")
    min_order: float = Field(serialization_alias="minOrder")
    max_order_quantity: int = Field(serialization_alias="maxOrderQuantity")
    delivery_time: str = Field(serialization_alias="deliveryTime")
    tags: list[str]


class PublicMerchantDetail(PublicMerchantListItem):
    user_id: int = Field(serialization_alias="userId")
    audit_status: int = Field(serialization_alias="auditStatus")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


# ── Menu ──


class MenuCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    item_name: str = Field(
        max_length=100,
        validation_alias=AliasChoices("item_name", "itemName"),
    )
    price: Decimal = Field(gt=0)
    max_daily_quantity: int = Field(
        gt=0,
        validation_alias=AliasChoices("max_daily_quantity", "maxDailyQuantity"),
    )
    image_url: str | None = Field(
        default=None,
        max_length=512,
        validation_alias=AliasChoices("image_url", "imageUrl"),
    )


class MenuUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    item_name: str | None = Field(
        default=None,
        max_length=100,
        validation_alias=AliasChoices("item_name", "itemName"),
    )
    price: Decimal | None = Field(default=None, gt=0)
    max_daily_quantity: int | None = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices("max_daily_quantity", "maxDailyQuantity"),
    )
    image_url: str | None = Field(
        default=None,
        max_length=512,
        validation_alias=AliasChoices("image_url", "imageUrl"),
    )


class MenuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    merchant_id: int = Field(serialization_alias="merchantId")
    item_name: str = Field(serialization_alias="itemName")
    price: float
    max_daily_quantity: int = Field(serialization_alias="maxDailyQuantity")
    image_url: str | None = Field(default=None, serialization_alias="imageUrl")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")

    @field_serializer("image_url")
    def serialize_image_url(self, value: str | None) -> str | None:
        return build_public_menu_image_url(value, self.merchant_id)


def build_public_menu_image_url(value: str | None, merchant_id: int) -> str | None:
    if not value:
        return None

    image_ref = value.strip()
    if not image_ref:
        return None

    if image_ref.startswith(("http://", "https://", "/")):
        return image_ref

    object_name = image_ref.lstrip("/")
    if not object_name.startswith(f"{merchant_id}/"):
        object_name = f"{merchant_id}/{object_name}"

    encoded_object_name = quote(object_name, safe="/")
    return (
        "https://storage.googleapis.com/kubereats-menu-images/"
        f"{encoded_object_name}"
    )


class MenuImageUploadResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    image_url: str = Field(serialization_alias="imageUrl")


# ── Order Summary ──


class OrderItemSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    menu_id: int = Field(serialization_alias="menuId")
    item_name: str = Field(serialization_alias="itemName")
    total_quantity: int = Field(serialization_alias="totalQuantity")
    total_amount: float = Field(serialization_alias="totalAmount")


class TodayOrderSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    date: str
    total_orders: int = Field(serialization_alias="totalOrders")
    total_amount: float = Field(serialization_alias="totalAmount")
    items: list[OrderItemSummary]
    user_ids: list[int] = Field(default_factory=list, serialization_alias="userIds")
