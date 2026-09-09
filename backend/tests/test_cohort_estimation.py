from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.estimate import (
    CohortEstimateRequest,
    CohortInput,
    ModelAllocation,
    ModelPrice,
    TokenRatios,
)
from app.services.estimation import calculate_cohort_estimate


def prices() -> dict[str, ModelPrice]:
    return {
        model_id: ModelPrice(
            modelId=model_id,
            displayName=model_id.title(),
            family=family,
            inputCostPerToken="0.000001",
            outputCostPerToken="0.000001",
            cacheReadCostPerToken="0.000001",
            cacheWriteCostPerToken="0.000001",
        )
        for model_id, family in (
            ("haiku", "HAIKU"),
            ("sonnet", "SONNET"),
            ("opus", "OPUS"),
            ("nova", "OTHER"),
        )
    }


def cohort(intensity: str, percentage: int, daily_tokens: int) -> CohortInput:
    return CohortInput(
        intensity=intensity,
        percentage=percentage,
        dailyTotalTokens=daily_tokens,
        tokenRatios=TokenRatios(input=25, output=25, cacheRead=25, cacheWrite=25),
        models=[
            ModelAllocation(modelId="haiku", family="HAIKU", percentage=20),
            ModelAllocation(modelId="sonnet", family="SONNET", percentage=60),
            ModelAllocation(modelId="opus", family="OPUS", percentage=10),
            ModelAllocation(modelId="nova", family="OTHER", percentage=10),
        ],
    )


def test_calculates_weighted_cohort_costs() -> None:
    request = CohortEstimateRequest(
        activeDaysPerMonth=20,
        userCount=100,
        cohorts=[cohort("lite", 70, 1_000_000), cohort("heavy", 30, 3_000_000)],
    )

    result = calculate_cohort_estimate(request, prices())

    assert result.cohorts[0].effectiveUsers == Decimal("70")
    assert len(result.cohorts[0].breakdown) == 16
    assert sum(item.costUsd for item in result.cohorts[0].breakdown) == Decimal("1.000000")
    assert result.cohorts[0].totalMonthlyUsd == Decimal("1400.000000")
    assert result.cohorts[1].totalMonthlyUsd == Decimal("1800.000000")
    assert result.totalMonthlyUsd == Decimal("3200.000000")
    assert result.totalAnnualUsd == Decimal("38400.000000")


def test_rejects_different_token_ratios_between_cohorts() -> None:
    light = cohort("lite", 70, 1_000_000)
    heavy = cohort("heavy", 30, 3_000_000)
    heavy.tokenRatios = TokenRatios(input=10, output=10, cacheRead=70, cacheWrite=10)

    with pytest.raises(ValidationError, match="same token ratios"):
        CohortEstimateRequest(
            activeDaysPerMonth=20,
            userCount=30,
            cohorts=[light, heavy],
        )


def test_rejects_different_model_mixes_between_cohorts() -> None:
    light = cohort("lite", 70, 1_000_000)
    heavy = cohort("heavy", 30, 3_000_000)
    heavy.models = list(reversed(heavy.models))

    with pytest.raises(ValidationError, match="same model mix"):
        CohortEstimateRequest(
            activeDaysPerMonth=20,
            userCount=30,
            cohorts=[light, heavy],
        )


def test_rejects_cohort_percentages_that_do_not_total_100() -> None:
    with pytest.raises(ValidationError, match="total 100"):
        CohortEstimateRequest(
            activeDaysPerMonth=20,
            userCount=30,
            cohorts=[cohort("lite", 60, 1_000_000), cohort("heavy", 30, 3_000_000)],
        )
