from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

from app.schemas.estimate import TokenRatios


class ModelRatios(BaseModel):
    sonnet: int = Field(ge=0, le=100)
    opus: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def total_is_100(self) -> "ModelRatios":
        if self.sonnet + self.opus != 100:
            raise ValueError("Model ratios must total 100")
        return self


class PresetLevel(BaseModel):
    label: str
    description: str
    dailyTotalTokens: int = Field(gt=0)
    tokenRatios: TokenRatios
    modelRatios: ModelRatios


class Workload(BaseModel):
    label: str
    levels: dict[str, PresetLevel]


class PresetConfig(BaseModel):
    version: int
    references: dict
    workloads: dict[str, Workload]
    metadata: dict


def load_presets(path: Path) -> PresetConfig:
    with path.open(encoding="utf-8") as file:
        return PresetConfig.model_validate(yaml.safe_load(file))
