from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


# ── Merchant ──


MerchantSortKey = Literal["people", "popular", "recommend"]
DietaryType = Literal["MEAT", "VEGAN", "OVO_LACTO", "OVO", "LACTO", "PESCATARIAN"]


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
    cooperation_start_date: date | None = Field(
        default=None,
        serialization_alias="cooperationStartDate",
    )
    cooperation_end_date: date | None = Field(
        default=None,
        serialization_alias="cooperationEndDate",
    )
    suspended_at: datetime | None = Field(default=None, serialization_alias="suspendedAt")
    suspension_reason: str | None = Field(
        default=None,
        serialization_alias="suspensionReason",
    )
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
    cooperation_start_date: date | None = Field(
        default=None,
        serialization_alias="cooperationStartDate",
    )
    cooperation_end_date: date | None = Field(
        default=None,
        serialization_alias="cooperationEndDate",
    )


class PublicMerchantDetail(PublicMerchantListItem):
    user_id: int = Field(serialization_alias="userId")
    audit_status: int = Field(serialization_alias="auditStatus")
    suspended_at: datetime | None = Field(default=None, serialization_alias="suspendedAt")
    suspension_reason: str | None = Field(
        default=None,
        serialization_alias="suspensionReason",
    )
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
    image_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("image_id", "imageId"),
    )
    dietary_type: DietaryType = Field(
        default="MEAT",
        validation_alias=AliasChoices("dietary_type", "dietaryType"),
    )
    allergens: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    calories_kcal: int | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("calories_kcal", "caloriesKcal"),
    )
    protein_g: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("protein_g", "proteinG"),
    )
    carbs_g: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("carbs_g", "carbsG"),
    )
    fat_g: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("fat_g", "fatG"),
    )
    sodium_mg: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("sodium_mg", "sodiumMg"),
    )
    sugar_g: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("sugar_g", "sugarG"),
    )
    serving_size: str | None = Field(
        default=None,
        max_length=50,
        validation_alias=AliasChoices("serving_size", "servingSize"),
    )
    ingredients: str | None = Field(default=None, max_length=1000)


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
    image_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("image_id", "imageId"),
    )
    dietary_type: DietaryType | None = Field(
        default=None,
        validation_alias=AliasChoices("dietary_type", "dietaryType"),
    )
    allergens: list[str] | None = None
    certifications: list[str] | None = None
    calories_kcal: int | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("calories_kcal", "caloriesKcal"),
    )
    protein_g: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("protein_g", "proteinG"),
    )
    carbs_g: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("carbs_g", "carbsG"),
    )
    fat_g: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("fat_g", "fatG"),
    )
    sodium_mg: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("sodium_mg", "sodiumMg"),
    )
    sugar_g: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("sugar_g", "sugarG"),
    )
    serving_size: str | None = Field(
        default=None,
        max_length=50,
        validation_alias=AliasChoices("serving_size", "servingSize"),
    )
    ingredients: str | None = Field(default=None, max_length=1000)


class MenuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    merchant_id: int = Field(serialization_alias="merchantId")
    item_name: str = Field(serialization_alias="itemName")
    price: float
    max_daily_quantity: int = Field(serialization_alias="maxDailyQuantity")
    image_id: str | None = Field(default=None, serialization_alias="imageId")
    dietary_type: str = Field(serialization_alias="dietaryType")
    allergens: list[str]
    certifications: list[str]
    calories_kcal: int | None = Field(default=None, serialization_alias="caloriesKcal")
    protein_g: float | None = Field(default=None, serialization_alias="proteinG")
    carbs_g: float | None = Field(default=None, serialization_alias="carbsG")
    fat_g: float | None = Field(default=None, serialization_alias="fatG")
    sodium_mg: float | None = Field(default=None, serialization_alias="sodiumMg")
    sugar_g: float | None = Field(default=None, serialization_alias="sugarG")
    serving_size: str | None = Field(default=None, serialization_alias="servingSize")
    ingredients: str | None = None
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


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
