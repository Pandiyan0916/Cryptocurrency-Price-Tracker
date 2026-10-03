"""
tests/test_regressions.py - Regression prevention tests for CoinPulse.

Verifies:
1. Logo distinctness (BTC logo != ETH logo; no single Bitcoin default for all coins).
2. ScraperService coin mapping and image URL assignment.
3. API endpoints return distinct logo URLs.
"""

import httpx
import pytest
from fastapi.testclient import TestClient
from src.models import Coin
from webapp.main import app, get_coingecko_client
from webapp.services.coingecko import CoinGeckoClient
from webapp.services.scraper_service import scraper_service, get_coin_logo_url

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_coingecko_regressions_fixture():
    mock_markets = [
        {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "image": "https://assets.coingecko.com/coins/images/1/large/bitcoin.png",
            "current_price": 85000.0,
            "market_cap": 1700000000000,
            "market_cap_rank": 1,
        },
        {
            "id": "ethereum",
            "symbol": "eth",
            "name": "Ethereum",
            "image": "https://assets.coingecko.com/coins/images/279/large/ethereum.png",
            "current_price": 2600.0,
            "market_cap": 310000000000,
            "market_cap_rank": 2,
        },
    ]

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_markets)

    transport = httpx.MockTransport(mock_handler)
    mock_client = CoinGeckoClient(transport=transport)
    app.dependency_overrides[get_coingecko_client] = lambda: mock_client
    yield
    app.dependency_overrides.clear()


def test_logo_url_distinctness():
    """Verify distinct cryptocurrencies get distinct logo URLs and not all Bitcoin's logo."""
    btc_logo = get_coin_logo_url("BTC", "Bitcoin")
    eth_logo = get_coin_logo_url("ETH", "Ethereum")
    sol_logo = get_coin_logo_url("SOL", "Solana")

    assert btc_logo != eth_logo, "BTC and ETH logos must be distinct!"
    assert btc_logo != sol_logo, "BTC and SOL logos must be distinct!"
    assert "bitcoin.png" in btc_logo
    assert "ethereum.png" in eth_logo


def test_scraper_service_coin_to_market_coin_logos():
    """Verify ScraperService converts domain Coin objects with distinct image URLs."""
    btc_coin = Coin(rank=1, name="Bitcoin", symbol="BTC", price=85000.0, change_24h=1.5, market_cap=1700000000000, timestamp="2026-10-03 10:00:00 UTC")
    eth_coin = Coin(rank=2, name="Ethereum", symbol="ETH", price=2600.0, change_24h=-0.5, market_cap=31000000000, timestamp="2026-10-03 10:00:00 UTC")

    btc_market = scraper_service._coin_to_market_coin(btc_coin)
    eth_market = scraper_service._coin_to_market_coin(eth_coin)

    assert btc_market.image != eth_market.image
    assert btc_market.image is not None
    assert eth_market.image is not None


def test_markets_api_returns_distinct_logos():
    """Verify /api/markets endpoint returns distinct logo URLs for coins."""
    response = client.get("/api/markets?page=1&per_page=10")
    assert response.status_code == 200
    data = response.json()
    coins = data.get("data", [])
    assert len(coins) >= 2
    logo_0 = coins[0].get("image")
    logo_1 = coins[1].get("image")
    assert logo_0 is not None
    assert logo_1 is not None
    assert logo_0 != logo_1, "Top two market coins must have distinct logo URLs!"
