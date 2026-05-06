from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


OrderStatus = Literal[0, 1, 2]


class OrderItemCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    menu_id: int = Field(validation_alias=AliasChoices("menu_id", "menuId"))
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: int = Field(validation_alias=AliasChoices("user_id", "userId"))
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderStatusUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order_status: OrderStatus = Field(
        validation_alias=AliasChoices("order_status", "orderStatus")
    )


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    menu_id: int = Field(serialization_alias="menuId")
    item_name: str = Field(serialization_alias="itemName")
    quantity: int
    unit_price: float = Field(serialization_alias="unitPrice")
    subtotal: float


class FinanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    merchant_id: int = Field(serialization_alias="merchantId")
    merchant_name: str = Field(serialization_alias="merchantName")
    settlement_amount: float = Field(serialization_alias="settlementAmount")
    report_data: dict | None = Field(default=None, serialization_alias="reportData")


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    user_id: int = Field(serialization_alias="userId")
    total_amount: float = Field(serialization_alias="totalAmount")
    order_status: int = Field(serialization_alias="orderStatus")
    order_time: datetime = Field(serialization_alias="orderTime")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
    items: list[OrderItemResponse]
    finance_records: list[FinanceResponse] = Field(serialization_alias="financeRecords")
