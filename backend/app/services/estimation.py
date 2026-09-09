from decimal import Decimal

from app.schemas import estimate

_CATEGORIES = (
    ("input", "input", "inputCostPerToken"),
    ("output", "output", "outputCostPerToken"),
    ("cacheRead", "cacheRead", "cacheReadCostPerToken"),
    ("cacheWrite", "cacheWrite", "cacheWriteCostPerToken"),
)


def calculate_estimate(
    request: estimate.EstimateRequest, prices_by_id: dict[str, estimate.ModelPrice]
) -> estimate.EstimateResult:
    breakdown: list[estimate.BreakdownItem] = []
    daily_total = Decimal(request.dailyTotalTokens)

    for allocation in request.models:
        price = prices_by_id.get(allocation.modelId)
        if price is None:
            raise ValueError(f"Missing price for model {allocation.modelId}")
        if price.family != allocation.family:
            raise ValueError(f"Model family mismatch for {allocation.modelId}")

        model_ratio = allocation.percentage / Decimal("100")
        for category, ratio_field, price_field in _CATEGORIES:
            category_ratio = getattr(request.tokenRatios, ratio_field) / Decimal("100")
            tokens = daily_total * category_ratio * model_ratio
            unit_price = getattr(price, price_field)
            breakdown.append(
                estimate.BreakdownItem(
                    modelId=allocation.modelId,
                    family=allocation.family,
                    category=category,
                    tokens=tokens,
                    pricePerToken=unit_price,
                    costUsd=tokens * unit_price,
                )
            )

    daily = sum((item.costUsd for item in breakdown), Decimal())
    monthly = daily * request.activeDaysPerMonth
    total_monthly = monthly * request.userCount
    return estimate.EstimateResult(
        breakdown=breakdown,
        prices=[prices_by_id[allocation.modelId] for allocation in request.models],
        perUserDailyUsd=daily,
        perUserMonthlyUsd=monthly,
        totalMonthlyUsd=total_monthly,
        totalAnnualUsd=total_monthly * 12,
    )


def calculate_cohort_estimate(
    request: estimate.CohortEstimateRequest,
    prices_by_id: dict[str, estimate.ModelPrice],
) -> estimate.CohortEstimateResult:
    cohorts: list[estimate.CohortResult] = []
    total_monthly = Decimal()

    for cohort in request.cohorts:
        single_user = calculate_estimate(
            estimate.EstimateRequest(
                dailyTotalTokens=cohort.dailyTotalTokens,
                activeDaysPerMonth=request.activeDaysPerMonth,
                userCount=1,
                tokenRatios=cohort.tokenRatios,
                models=cohort.models,
            ),
            prices_by_id,
        )
        effective_users = Decimal(request.userCount) * cohort.percentage / Decimal("100")
        cohort_monthly = single_user.perUserMonthlyUsd * effective_users
        total_monthly += cohort_monthly
        cohorts.append(
            estimate.CohortResult(
                intensity=cohort.intensity,
                percentage=cohort.percentage,
                effectiveUsers=effective_users,
                perUserDailyUsd=single_user.perUserDailyUsd,
                breakdown=single_user.breakdown,
                totalMonthlyUsd=cohort_monthly,
                totalAnnualUsd=cohort_monthly * 12,
            )
        )

    return estimate.CohortEstimateResult(
        cohorts=cohorts,
        totalMonthlyUsd=total_monthly,
        totalAnnualUsd=total_monthly * 12,
    )
