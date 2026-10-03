"""
tests/test_webapp_api.py - Integration tests for FastAPI endpoints using httpx.MockTransport.
"""

import httpx
import pytest
from fastapi.testclient import TestClient
from webapp.main import app, get_coingecko_client
from webapp.services.cache import cache
from webapp.services.coingecko import CoinGeckoClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_coingecko_api_fixture(monkeypatch):
    cache.clear()
    mock_markets = [
        {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "image": "https://assets.coingecko.com/btc.png",
            "current_price": 85000.0,
            "market_cap": 1700000000000,
            "market_cap_rank": 1,
            "total_volume": 35000000000,
            "price_change_percentage_24h_in_currency": 2.5,
            "sparkline_in_7d": {"price": [83000.0, 84000.0, 85000.0]},
        }
    ]
    mock_global = {
        "data": {
            "active_cryptocurrencies": 12500,
            "total_market_cap": {"usd": 2500000000000.0},
            "total_volume": {"usd": 90000000000.0},
            "market_cap_percentage": {"btc": 54.2, "eth": 14.5},
            "market_cap_change_percentage_24h_usd": 2.1,
        }
    }
    mock_search = {
        "coins": [{"id": "bitcoin", "name": "Bitcoin", "symbol": "btc", "market_cap_rank": 1}],
        "exchanges": [],
        "categories": [],
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "/global" in path:
            return httpx.Response(200, json=mock_global)
        elif "/search" in path:
            return httpx.Response(200, json=mock_search)
        elif "/coins/markets" in path:
            return httpx.Response(200, json=mock_markets)
        elif "/trending" in path:
            return httpx.Response(200, json={"coins": [{"item": mock_markets[0]}]})
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(mock_handler)
    mock_client = CoinGeckoClient(transport=transport)
    app.dependency_overrides[get_coingecko_client] = lambda: mock_client
    yield
    app.dependency_overrides.clear()
    cache.clear()


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "upstream_status" in data
    assert "active_source" in data
    assert "timestamp" in data


def test_markets_endpoint():
    response = client.get("/api/markets?page=1&per_page=10")
    assert response.status_code == 200
    data = response.json()
    assert "source" in data
    assert "data" in data
    assert isinstance(data["data"], list)


def test_markets_endpoint_invalid_per_page():
    response = client.get("/api/markets?per_page=150")  # > 100 limit
    assert response.status_code == 422  # Validation error from FastAPI Query constraint


def test_global_endpoint():
    response = client.get("/api/global")
    assert response.status_code == 200
    data = response.json()
    assert "source" in data
    assert "data" in data
    assert "total_market_cap_usd" in data["data"]


def test_coin_chart_invalid_days():
    response = client.get("/api/coin/bitcoin/chart?days=15")  # 15 not allowed
    assert response.status_code == 400
    assert "Invalid days parameter" in response.json()["detail"]


def test_search_endpoint():
    response = client.get("/api/search?q=btc")
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert data["query"] == "btc"
    assert "coins" in data


def test_trending_endpoint():
    response = client.get("/api/trending")
    assert response.status_code == 200
    data = response.json()
    assert "coins" in data
