"""
tests/test_webapp_coingecko.py - Unit tests for CoinGeckoClient with httpx.MockTransport.
"""

import httpx
import pytest
from webapp.services.coingecko import (
    CoinGeckoClient,
    CoinGeckoError,
    CoinGeckoRateLimitError,
)


@pytest.mark.anyio
async def test_fetch_markets_success():
    mock_data = [
        {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "image": "https://assets.coingecko.com/btc.png",
            "current_price": 67000.0,
            "market_cap": 1300000000000,
            "market_cap_rank": 1,
            "total_volume": 25000000000,
            "price_change_percentage_24h_in_currency": 3.42,
            "sparkline_in_7d": {"price": [65000.0, 66000.0, 67000.0]},
        }
    ]

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(mock_handler)
    client = CoinGeckoClient(transport=transport)
    coins = await client.fetch_markets(page=1, per_page=10)

    assert len(coins) == 1
    assert coins[0].id == "bitcoin"
    assert coins[0].symbol == "btc"
    assert coins[0].current_price == 67000.0
    assert coins[0].sparkline_in_7d is not None
    assert coins[0].sparkline_in_7d.price == [65000.0, 66000.0, 67000.0]


@pytest.mark.anyio
async def test_fetch_markets_rate_limit_429():
    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"status": {"error_code": 429, "error_message": "Rate limit exceeded"}})

    transport = httpx.MockTransport(mock_handler)
    client = CoinGeckoClient(transport=transport)

    with pytest.raises(CoinGeckoRateLimitError) as exc_info:
        await client.fetch_markets(page=1)

    assert exc_info.value.status_code == 429


@pytest.mark.anyio
async def test_fetch_global_stats_success():
    mock_global = {
        "data": {
            "active_cryptocurrencies": 12500,
            "total_market_cap": {"usd": 2500000000000.0},
            "total_volume": {"usd": 90000000000.0},
            "market_cap_percentage": {"btc": 54.2},
            "market_cap_change_percentage_24h_usd": 2.1,
        }
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_global)

    transport = httpx.MockTransport(mock_handler)
    client = CoinGeckoClient(transport=transport)
    stats = await client.fetch_global()

    assert stats.active_cryptocurrencies == 12500
    assert stats.total_market_cap_usd == 2500000000000.0
    assert stats.btc_dominance == 54.2
