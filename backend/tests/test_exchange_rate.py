from decimal import Decimal

import httpx
import pytest

from app.services.exchange_rate import fetch_usd_krw_rate


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_fetches_and_validates_usd_krw_rate() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/rate/USD/KRW"
        return httpx.Response(
            200,
            json={"date": "2026-09-09", "base": "USD", "quote": "KRW", "rate": 1344.33},
        )

    result = await fetch_usd_krw_rate(
        "https://api.frankfurter.dev/v2/rate/USD/KRW",
        transport=httpx.MockTransport(handler),
    )

    assert result.rate == Decimal("1344.33")
    assert result.effectiveDate.isoformat() == "2026-09-09"
    assert result.source == "Frankfurter"


@pytest.mark.anyio
async def test_rejects_unexpected_currency_pair() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"date": "2026-09-09", "base": "EUR", "quote": "KRW", "rate": 1500},
        )

    with pytest.raises(ValueError, match="currency pair"):
        await fetch_usd_krw_rate(
            "https://api.frankfurter.dev/v2/rate/USD/KRW",
            transport=httpx.MockTransport(handler),
        )
