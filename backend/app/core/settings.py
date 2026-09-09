from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./cost_estimator.db"
    litellm_catalog_url: str = "https://api.litellm.ai/model_catalog"
    preset_path: Path = Path(__file__).resolve().parents[2] / "config" / "presets.yaml"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
