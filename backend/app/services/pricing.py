from datetime import UTC, datetime
from decimal import Decimal

import httpx
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ModelPriceRecord, PriceSyncRun
from app.schemas.estimate import ModelPrice


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    provider: str
    mode: str
    input_cost_per_token: Decimal = Field(ge=0)
    output_cost_per_token: Decimal = Field(ge=0)
    cache_read_input_token_cost: Decimal = Field(ge=0)
    cache_creation_input_token_cost: Decimal = Field(ge=0)


class CatalogPage(BaseModel):
    data: list[dict]
    has_more: bool


async def fetch_catalog(url: str, page_size: int = 100) -> list[dict]:
    models: list[dict] = []
    async with httpx.AsyncClient(timeout=30) as client:
        for page in range(1, 101):
            response = await client.get(
                url,
                params={"provider": "bedrock_converse", "page": page, "page_size": page_size},
            )
            response.raise_for_status()
            payload = CatalogPage.model_validate(response.json())
            models.extend(payload.data)
            if not payload.has_more:
                return models
    raise ValueError("LiteLLM catalog exceeded pagination limit")


def normalize_catalog(raw_models: list[dict]) -> list[CatalogModel]:
    normalized = []
    for raw in raw_models:
        model_id = str(raw.get("id", "")).lower()
        if raw.get("mode") != "chat" or "anthropic" not in model_id:
            continue
        if "sonnet" not in model_id and "opus" not in model_id:
            continue
        normalized.append(CatalogModel.model_validate(raw))
    if not any("sonnet" in item.id.lower() for item in normalized):
        raise ValueError("Catalog contains no complete Sonnet prices")
    if not any("opus" in item.id.lower() for item in normalized):
        raise ValueError("Catalog contains no complete Opus prices")
    return normalized


def list_prices(db: Session) -> list[ModelPrice]:
    records = db.scalars(
        select(ModelPriceRecord)
        .where(ModelPriceRecord.is_active.is_(True))
        .order_by(ModelPriceRecord.family, ModelPriceRecord.display_name)
    ).all()
    return [record_to_schema(record) for record in records]


def record_to_schema(record: ModelPriceRecord) -> ModelPrice:
    return ModelPrice(
        modelId=record.model_id,
        displayName=record.display_name,
        family=record.family,
        inputCostPerToken=record.input_cost_per_token,
        outputCostPerToken=record.output_cost_per_token,
        cacheReadCostPerToken=record.cache_read_cost_per_token,
        cacheWriteCostPerToken=record.cache_write_cost_per_token,
    )


def store_catalog(db: Session, raw_models: list[dict]) -> int:
    started = datetime.now(UTC)
    models = normalize_catalog(raw_models)
    now = datetime.now(UTC)
    active_ids = {model.id for model in models}
    with db.begin():
        for record in db.scalars(select(ModelPriceRecord)).all():
            record.is_active = record.model_id in active_ids
        for model in models:
            record = db.get(ModelPriceRecord, model.id) or ModelPriceRecord(model_id=model.id)
            record.display_name = model.id
            record.family = "SONNET" if "sonnet" in model.id.lower() else "OPUS"
            record.provider = model.provider
            record.input_cost_per_token = model.input_cost_per_token
            record.output_cost_per_token = model.output_cost_per_token
            record.cache_read_cost_per_token = model.cache_read_input_token_cost
            record.cache_write_cost_per_token = model.cache_creation_input_token_cost
            record.synced_at = now
            record.is_active = True
            db.add(record)
        db.add(
            PriceSyncRun(
                status="success",
                started_at=started,
                completed_at=now,
                fetched_count=len(raw_models),
                stored_count=len(models),
            )
        )
    return len(models)
