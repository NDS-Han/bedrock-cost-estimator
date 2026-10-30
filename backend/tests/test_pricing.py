from decimal import Decimal

import pytest

from app.services.pricing import catalog_models, normalize_catalog


def catalog_entry(model_id: str, **overrides) -> dict:
    data = model(model_id)
    data["litellm_provider"] = data.pop("provider")
    data.pop("id")
    data.update(overrides)
    return data


def test_catalog_models_filters_and_keys_entries() -> None:
    payload = {
        "global.anthropic.claude-sonnet-4": catalog_entry("unused"),
        "us.anthropic.claude-sonnet-4": catalog_entry("unused"),
        "gpt-4o": catalog_entry("unused", litellm_provider="openai"),
        "sample_spec": {"description": "not a model"},
    }

    result = catalog_models(payload)

    assert [item["id"] for item in result] == [
        "global.anthropic.claude-sonnet-4",
        "us.anthropic.claude-sonnet-4",
    ]
    assert all(item["provider"] == "bedrock_converse" for item in result)


def test_catalog_models_rejects_non_mapping_payload() -> None:
    with pytest.raises(ValueError, match="model map"):
        catalog_models([{"id": "global.anthropic.claude-sonnet-4"}])


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
