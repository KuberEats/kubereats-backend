from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MerchantReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    user_id: int = Field(serialization_alias="userId")
    merchant_name: str = Field(serialization_alias="merchantName")
    campus: str
    category: str
    min_order: float = Field(serialization_alias="minOrder")
    delivery_time: str = Field(serialization_alias="deliveryTime")
    tags: list[str]
    audit_status: int = Field(serialization_alias="auditStatus")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class AuditResultResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    merchant_name: str = Field(serialization_alias="merchantName")
    audit_status: int = Field(serialization_alias="auditStatus")
    message: str
