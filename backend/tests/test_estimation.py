from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.estimate import EstimateRequest, ModelAllocation, ModelPrice, TokenRatios
from app.services.estimation import calculate_estimate


def request() -> EstimateRequest:
    return EstimateRequest(
        dailyTotalTokens=1_000_000,
        activeDaysPerMonth=20,
        userCount=10,
        tokenRatios=TokenRatios(input=10, output=5, cacheRead=75, cacheWrite=10),
        models=[
            ModelAllocation(modelId="haiku", family="HAIKU", percentage=0),
            ModelAllocation(modelId="sonnet", family="SONNET", percentage=80),
            ModelAllocation(modelId="opus", family="OPUS", percentage=20),
            ModelAllocation(modelId="nova", family="OTHER", percentage=0),
        ],
    )


def prices() -> dict[str, ModelPrice]:
    return {
        "haiku": ModelPrice(
            modelId="haiku",
            displayName="Haiku",
            family="HAIKU",
            inputCostPerToken="0.000001",
            outputCostPerToken="0.000005",
            cacheReadCostPerToken="0.0000001",
            cacheWriteCostPerToken="0.00000125",
        ),
        "nova": ModelPrice(
            modelId="nova",
            displayName="Nova",
            family="OTHER",
            inputCostPerToken="0.000001",
            outputCostPerToken="0.000005",
            cacheReadCostPerToken="0.0000001",
            cacheWriteCostPerToken="0.00000125",
        ),
        "sonnet": ModelPrice(
            modelId="sonnet",
            displayName="Sonnet",
            family="SONNET",
            inputCostPerToken="0.000003",
            outputCostPerToken="0.000015",
            cacheReadCostPerToken="0.0000003",
            cacheWriteCostPerToken="0.00000375",
        ),
        "opus": ModelPrice(
            modelId="opus",
            displayName="Opus",
            family="OPUS",
            inputCostPerToken="0.000015",
            outputCostPerToken="0.000075",
            cacheReadCostPerToken="0.0000015",
            cacheWriteCostPerToken="0.00001875",
        ),
    }


def test_calculates_exact_breakdown_and_totals() -> None:
    result = calculate_estimate(request(), prices())

    assert sum(item.tokens for item in result.breakdown) == Decimal("1000000")
    assert result.perUserDailyUsd == Decimal("2.97000000")
    assert result.perUserMonthlyUsd == Decimal("59.40000000")
    assert result.totalMonthlyUsd == Decimal("594.00000000")
    assert result.totalAnnualUsd == Decimal("7128.00000000")
    assert sum(item.costUsd for item in result.breakdown) == result.perUserDailyUsd


def test_rejects_token_ratios_that_do_not_total_100() -> None:
    with pytest.raises(ValidationError):
        TokenRatios(input=10, output=5, cacheRead=70, cacheWrite=10)


def test_rejects_model_mix_that_does_not_total_100() -> None:
    with pytest.raises(ValidationError):
        EstimateRequest(
            dailyTotalTokens=100,
            activeDaysPerMonth=20,
            userCount=1,
            tokenRatios=TokenRatios(input=10, output=5, cacheRead=75, cacheWrite=10),
            models=[
                ModelAllocation(modelId="haiku", family="HAIKU", percentage=0),
                ModelAllocation(modelId="sonnet", family="SONNET", percentage=70),
                ModelAllocation(modelId="opus", family="OPUS", percentage=20),
            ],
        )


def test_rejects_duplicate_model_families() -> None:
    with pytest.raises(ValidationError):
        EstimateRequest(
            dailyTotalTokens=100,
            activeDaysPerMonth=20,
            userCount=1,
            tokenRatios=TokenRatios(input=10, output=5, cacheRead=75, cacheWrite=10),
            models=[
                ModelAllocation(modelId="haiku", family="HAIKU", percentage=0),
                ModelAllocation(modelId="sonnet-a", family="SONNET", percentage=50),
                ModelAllocation(modelId="sonnet-b", family="SONNET", percentage=50),
            ],
        )


def test_rejects_missing_model_price() -> None:
    with pytest.raises(ValueError, match="Missing price"):
        calculate_estimate(request(), {"sonnet": prices()["sonnet"]})
