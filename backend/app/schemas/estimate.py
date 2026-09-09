from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class TokenRatios(ApiModel):
    input: Decimal = Field(ge=0, le=100)
    output: Decimal = Field(ge=0, le=100)
    cacheRead: Decimal = Field(ge=0, le=100)
    cacheWrite: Decimal = Field(ge=0, le=100)

    @model_validator(mode="after")
    def total_is_100(self) -> "TokenRatios":
        if self.input + self.output + self.cacheRead + self.cacheWrite != Decimal("100"):
            raise ValueError("Token ratios must total 100")
        return self


class ModelAllocation(ApiModel):
    modelId: str = Field(min_length=1)
    family: Literal["SONNET", "OPUS"]
    percentage: Decimal = Field(ge=0, le=100)


class ModelPrice(ApiModel):
    modelId: str
    displayName: str
    family: Literal["SONNET", "OPUS"]
    inputCostPerToken: Decimal = Field(ge=0)
    outputCostPerToken: Decimal = Field(ge=0)
    cacheReadCostPerToken: Decimal = Field(ge=0)
    cacheWriteCostPerToken: Decimal = Field(ge=0)


class EstimateRequest(ApiModel):
    dailyTotalTokens: int = Field(gt=0)
    activeDaysPerMonth: int = Field(ge=1, le=31)
    userCount: int = Field(gt=0)
    tokenRatios: TokenRatios
    models: list[ModelAllocation] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def valid_model_mix(self) -> "EstimateRequest":
        if {model.family for model in self.models} != {"SONNET", "OPUS"}:
            raise ValueError("Exactly one Sonnet and one Opus model are required")
        if sum((model.percentage for model in self.models), Decimal()) != Decimal("100"):
            raise ValueError("Model percentages must total 100")
        return self


class BreakdownItem(ApiModel):
    modelId: str
    family: Literal["SONNET", "OPUS"]
    category: Literal["input", "output", "cacheRead", "cacheWrite"]
    tokens: Decimal
    pricePerToken: Decimal
    costUsd: Decimal


class EstimateResult(ApiModel):
    breakdown: list[BreakdownItem]
    prices: list[ModelPrice]
    perUserDailyUsd: Decimal
    perUserMonthlyUsd: Decimal
    totalMonthlyUsd: Decimal
    totalAnnualUsd: Decimal
