from datetime import date
from decimal import Decimal

import httpx
from pydantic import BaseModel, ConfigDict, Field


class FrankfurterRate(BaseModel):
    date: date
    base: str
    quote: str
    rate: Decimal = Field(gt=0)


class ExchangeRate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rate: Decimal
    effectiveDate: date
    source: str = "Frankfurter"


async def fetch_usd_krw_rate(
    url: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> ExchangeRate:
    async with httpx.AsyncClient(timeout=10, transport=transport) as client:
        response = await client.get(url)
        response.raise_for_status()
    payload = FrankfurterRate.model_validate(response.json())
    if payload.base != "USD" or payload.quote != "KRW":
        raise ValueError("Frankfurter returned an unexpected currency pair")
    return ExchangeRate(rate=payload.rate, effectiveDate=payload.date)
