from decimal import Decimal

import pytest

from app.services.pricing import normalize_catalog


def model(model_id: str, **overrides) -> dict:
    data = {
        "id": model_id,
        "provider": "bedrock_converse",
        "mode": "chat",
        "input_cost_per_token": "0.000003",
        "output_cost_per_token": "0.000015",
        "cache_read_input_token_cost": "0.0000003",
        "cache_creation_input_token_cost": "0.00000375",
    }
    data.update(overrides)
    return data


def test_normalizes_only_supported_complete_models() -> None:
    result = normalize_catalog(
        [
            model("global.anthropic.claude-haiku-4"),
            model("global.anthropic.claude-sonnet-4"),
            model("global.anthropic.claude-opus-4"),
            model("global.amazon.nova-pro"),
            model("us.anthropic.claude-sonnet-4"),
            model("anthropic.claude-opus-4"),
            model("amazon.nova-pro"),
        ]
    )

    assert [item.id for item in result] == [
        "global.anthropic.claude-haiku-4",
        "global.anthropic.claude-sonnet-4",
        "global.anthropic.claude-opus-4",
        "global.amazon.nova-pro",
    ]
    assert result[0].cache_read_input_token_cost == Decimal("0.0000003")


def test_rejects_missing_cache_price() -> None:
    with pytest.raises(ValueError, match="Sonnet"):
        normalize_catalog(
            [
                model("global.anthropic.claude-haiku-4"),
                model("global.anthropic.claude-sonnet-4", cache_read_input_token_cost=None),
                model("global.anthropic.claude-opus-4"),
            ]
        )


def test_rejects_catalog_without_both_families() -> None:
    with pytest.raises(ValueError, match="Opus"):
        normalize_catalog(
            [
                model("global.anthropic.claude-haiku-4"),
                model("global.anthropic.claude-sonnet-4"),
            ]
        )
