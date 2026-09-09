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
    family: Literal["HAIKU", "SONNET", "OPUS", "OTHER"]
    percentage: Decimal = Field(ge=0, le=100)


class ModelPrice(ApiModel):
    modelId: str
    displayName: str
    family: Literal["HAIKU", "SONNET", "OPUS", "OTHER"]
    inputCostPerToken: Decimal = Field(ge=0)
    outputCostPerToken: Decimal = Field(ge=0)
    cacheReadCostPerToken: Decimal = Field(ge=0)
    cacheWriteCostPerToken: Decimal = Field(ge=0)


def validate_models(models: list[ModelAllocation]) -> None:
    families = {model.family for model in models}
    if not {"HAIKU", "SONNET", "OPUS"}.issubset(families):
        raise ValueError("Haiku, Sonnet, and Opus base models are required")
    if len({model.modelId for model in models}) != len(models):
        raise ValueError("Duplicate models are not allowed")
    if sum((model.percentage for model in models), Decimal()) != Decimal("100"):
        raise ValueError("Model percentages must total 100")


class EstimateRequest(ApiModel):
    dailyTotalTokens: int = Field(gt=0)
    activeDaysPerMonth: int = Field(ge=1, le=31)
    userCount: int = Field(gt=0)
    tokenRatios: TokenRatios
    models: list[ModelAllocation] = Field(min_length=3, max_length=20)

    @model_validator(mode="after")
    def valid_model_mix(self) -> "EstimateRequest":
        validate_models(self.models)
        return self


class BreakdownItem(ApiModel):
    modelId: str
    family: Literal["HAIKU", "SONNET", "OPUS", "OTHER"]
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


class CohortInput(ApiModel):
    intensity: Literal["lite", "general", "heavy"]
    percentage: Decimal = Field(gt=0, le=100)
    dailyTotalTokens: int = Field(gt=0)
    tokenRatios: TokenRatios
    models: list[ModelAllocation] = Field(min_length=3, max_length=20)

    @model_validator(mode="after")
    def valid_model_mix(self) -> "CohortInput":
        validate_models(self.models)
        return self


class CohortEstimateRequest(ApiModel):
    activeDaysPerMonth: int = Field(ge=1, le=31)
    userCount: int = Field(gt=0)
    cohorts: list[CohortInput] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def valid_cohorts(self) -> "CohortEstimateRequest":
        if sum((cohort.percentage for cohort in self.cohorts), Decimal()) != Decimal("100"):
            raise ValueError("Cohort percentages must total 100")
        if len({cohort.intensity for cohort in self.cohorts}) != len(self.cohorts):
            raise ValueError("Duplicate cohort intensities are not allowed")
        if any(cohort.tokenRatios != self.cohorts[0].tokenRatios for cohort in self.cohorts[1:]):
            raise ValueError("All cohorts must use the same token ratios")
        if any(cohort.models != self.cohorts[0].models for cohort in self.cohorts[1:]):
            raise ValueError("All cohorts must use the same model mix")
        return self


class CohortResult(ApiModel):
    intensity: Literal["lite", "general", "heavy"]
    percentage: Decimal
    effectiveUsers: Decimal
    perUserDailyUsd: Decimal
    breakdown: list[BreakdownItem]
    totalMonthlyUsd: Decimal
    totalAnnualUsd: Decimal


class CohortEstimateResult(ApiModel):
    cohorts: list[CohortResult]
    totalMonthlyUsd: Decimal
    totalAnnualUsd: Decimal
