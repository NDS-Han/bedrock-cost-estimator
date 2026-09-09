from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.presets import load_presets
from app.core.settings import get_settings


def test_loads_all_workload_levels() -> None:
    config = load_presets(get_settings().preset_path)

    assert set(config.workloads) == {"codingAgent", "internalChatbot"}
    assert set(config.workloads["codingAgent"].levels) == {"lite", "general", "heavy"}
    assert config.references["claudeCode"]["averageDailyUsd"] == 13


def test_rejects_invalid_model_ratio(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text(
        """version: 1
references: {}
metadata: {}
workloads:
  codingAgent:
    label: Coding
    levels:
      lite:
        label: Lite
        description: invalid
        dailyTotalTokens: 100
        tokenRatios: {input: 25, output: 25, cacheRead: 25, cacheWrite: 25}
        modelRatios: {sonnet: 80, opus: 10}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_presets(path)
