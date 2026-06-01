from datetime import date, datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class MerchantReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    user_id: int = Field(serialization_alias="userId")
    merchant_name: str = Field(serialization_alias="merchantName")
    campus: str
    category: str
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


class AuditResultResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    merchant_name: str = Field(serialization_alias="merchantName")
    audit_status: int = Field(serialization_alias="auditStatus")
    message: str


class MerchantApprovalRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cooperation_start_date: date = Field(
        validation_alias=AliasChoices("cooperation_start_date", "cooperationStartDate")
    )
    cooperation_end_date: date = Field(
        validation_alias=AliasChoices("cooperation_end_date", "cooperationEndDate")
    )

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.cooperation_end_date < self.cooperation_start_date:
            raise ValueError("cooperation_end_date cannot be before cooperation_start_date")
        return self


class MerchantSuspendRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reason: str = Field(min_length=5, max_length=1000)
