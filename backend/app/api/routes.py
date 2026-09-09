from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.presets import load_presets
from app.core.settings import get_settings
from app.db.models import PriceSyncRun
from app.db.session import get_db
from app.schemas.estimate import EstimateRequest, EstimateResult, ModelPrice
from app.services.estimation import calculate_estimate
from app.services.pricing import fetch_catalog, list_prices, store_catalog

router = APIRouter(prefix="/api/v1")
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/health")
def health(db: DbSession) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ready"}


@router.get("/presets")
def presets() -> dict:
    config = load_presets(get_settings().preset_path)
    return config.model_dump(mode="json")


@router.get("/models", response_model=list[ModelPrice])
def models(db: DbSession) -> list[ModelPrice]:
    return list_prices(db)


@router.post("/estimates", response_model=EstimateResult)
def estimates(request: EstimateRequest, db: DbSession) -> EstimateResult:
    prices = {price.modelId: price for price in list_prices(db)}
    try:
        return calculate_estimate(request, prices)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/prices/sync")
async def sync_prices(db: DbSession) -> dict:
    raw_models = await fetch_catalog(get_settings().litellm_catalog_url)
    stored_count = store_catalog(db, raw_models)
    return {"fetchedCount": len(raw_models), "storedCount": stored_count}


@router.get("/prices/sync-status")
def sync_status(db: DbSession) -> dict:
    run = db.scalar(select(PriceSyncRun).order_by(PriceSyncRun.id.desc()).limit(1))
    if run is None:
        return {"status": "never"}
    return {
        "status": run.status,
        "completedAt": run.completed_at,
        "fetchedCount": run.fetched_count,
        "storedCount": run.stored_count,
    }
