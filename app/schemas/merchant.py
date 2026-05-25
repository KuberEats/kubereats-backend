from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Campus = Literal["竹科", "南科", "中科", "高科"]
MerchantSortKey = Literal["people", "popular", "recommend"]


class MerchantBase(BaseModel):
    merchant_name: str
    campus: Campus
    category: str
    rating: float
    order_count: int
    min_order: float
    max_order_quantity: int
    delivery_time: str
    tags: list[str]


class MerchantCreate(MerchantBase):
    user_id: int
    audit_status: int = 0


class MerchantUpdate(BaseModel):
    user_id: int | None = None
    merchant_name: str | None = None
    campus: Campus | None = None
    category: str | None = None
    rating: float | None = None
    order_count: int | None = None
    min_order: float | None = None
    max_order_quantity: int | None = None
    delivery_time: str | None = None
    tags: list[str] | None = None
    audit_status: int | None = None


class MerchantListQuery(BaseModel):
    campus: Campus
    date: date
    sort_by: MerchantSortKey = "recommend"


class MerchantListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    merchant_name: str = Field(serialization_alias="name")
    campus: Campus
    category: str
    rating: float
    order_count: int = Field(serialization_alias="orderCount")
    min_order: float = Field(serialization_alias="minOrder")
    max_order_quantity: int = Field(serialization_alias="maxOrderQuantity")
    delivery_time: str = Field(serialization_alias="deliveryTime")
    tags: list[str]


class MerchantDetail(MerchantListItem):
    user_id: int = Field(serialization_alias="userId")
    audit_status: int
    created_at: datetime
    updated_at: datetime
