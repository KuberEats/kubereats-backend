from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

Campus = Literal["竹科", "南科", "中科", "高科"]


class RecommendationMustConstraints(BaseModel):
    campus: Campus | None = None
    excluded_terms: list[str] = Field(
        default_factory=list,
        serialization_alias="excludedTerms",
    )
    max_budget: float | None = Field(default=None, serialization_alias="maxBudget")


class RecommendationAvoidConstraints(BaseModel):
    recent_merchants: bool = Field(
        default=False,
        serialization_alias="recentMerchants",
    )
    recent_order_limit: int = Field(default=5, serialization_alias="recentOrderLimit")


class RecommendationPreferences(BaseModel):
    terms: list[str] = Field(default_factory=list)
    fast_delivery: bool = Field(default=False, serialization_alias="fastDelivery")
    popular: bool = False
    familiar: bool = False
    novelty: bool = False


class RecommendationIntent(BaseModel):
    must: RecommendationMustConstraints = Field(
        default_factory=RecommendationMustConstraints
    )
    avoid: RecommendationAvoidConstraints = Field(
        default_factory=RecommendationAvoidConstraints
    )
    prefer: RecommendationPreferences = Field(
        default_factory=RecommendationPreferences
    )


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: int = Field(validation_alias=AliasChoices("user_id", "userId"))
    campus: Campus | None = None
    prompt: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)


class MenuRecommendationRequest(RecommendationRequest):
    merchant_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("merchant_id", "merchantId"),
    )


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
    signals: dict[str, object] = Field(default_factory=dict)


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
    signals: dict[str, object] = Field(default_factory=dict)
