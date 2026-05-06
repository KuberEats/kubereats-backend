from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    merchant_id: int = Field(serialization_alias="merchantId")
    item_name: str = Field(serialization_alias="itemName")
    max_daily_quantity: int = Field(serialization_alias="maxDailyQuantity")
    image_id: str | None = Field(default=None, serialization_alias="imageId")
    price: float
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
