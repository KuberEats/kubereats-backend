from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Campus = Literal["竹科", "南科", "中科", "高科"]


class MerchantRecommendation(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    merchant_name: str = Field(serialization_alias="name")
    campus: Campus
    category: str
    rating: float
    order_count: int = Field(serialization_alias="orderCount")
    delivery_time: str = Field(serialization_alias="deliveryTime")
    tags: list[str]
    score: float
    reason: str


class MenuRecommendation(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    merchant_id: int = Field(serialization_alias="merchantId")
    merchant_name: str = Field(serialization_alias="merchantName")
    item_name: str = Field(serialization_alias="itemName")
    price: float
    max_daily_quantity: int = Field(serialization_alias="maxDailyQuantity")
    score: float
    reason: str
