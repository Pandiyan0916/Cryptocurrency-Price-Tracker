"""
test_webapp_new_endpoints.py - Integration tests for Exchanges, Categories, Search, and Chart Timeframe API endpoints using httpx.MockTransport.
"""

import httpx
import pytest
from fastapi.testclient import TestClient
from webapp.main import app, get_coingecko_client
from webapp.services.coingecko import CoinGeckoClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_coingecko_fixture(monkeypatch):
    """Provide offline mock data for webapp API endpoint unit tests."""
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
    mock_exchanges = [
        {"id": "binance", "name": "Binance", "trust_score": 10, "trade_volume_24h_btc": 120000.0}
    ]
    mock_categories = [
        {"id": "layer-1", "name": "Layer 1 (L1)", "market_cap": 1500000000000.0}
    ]
    mock_chart = {"prices": [[1700000000000, 84000.0], [1700086400000, 85000.0]]}
    mock_search = {
        "coins": [{"id": "bitcoin", "name": "Bitcoin", "symbol": "btc", "market_cap_rank": 1}],
        "exchanges": [{"id": "binance", "name": "Binance"}],
        "categories": [{"id": "layer-1", "name": "Layer 1 (L1)"}],
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "/global" in path:
            return httpx.Response(200, json=mock_global)
        elif "/exchanges/binance" in path:
            return httpx.Response(200, json={"id": "binance", "name": "Binance", "trust_score": 10})
        elif "/exchanges" in path:
            return httpx.Response(200, json=mock_exchanges)
        elif "/categories" in path:
            return httpx.Response(200, json=mock_categories)
        elif "/market_chart" in path:
            return httpx.Response(200, json=mock_chart)
        elif "/search" in path:
            return httpx.Response(200, json=mock_search)
        elif "/coins/markets" in path:
            return httpx.Response(200, json=mock_markets)
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(mock_handler)
    mock_client = CoinGeckoClient(transport=transport)
    app.dependency_overrides[get_coingecko_client] = lambda: mock_client
    yield
    app.dependency_overrides.clear()


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "upstream_status" in data
    assert "active_source" in data


def test_api_global_stats():
    response = client.get("/api/global")
    assert response.status_code == 200
    data = response.json()
    assert "source" in data
    assert "as_of" in data
    stats = data["data"]
    assert "btc_dominance" in stats
    assert "eth_dominance" in stats
    assert "total_market_cap_usd" in stats


def test_api_exchanges_endpoint():
    response = client.get("/api/exchanges?page=1&per_page=10")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] in ["live", "snapshot", "coingecko"]
    assert "data" in data
    assert isinstance(data["data"], list)
    if data["data"]:
        ex = data["data"][0]
        assert "id" in ex
        assert "name" in ex


def test_api_exchange_detail_endpoint():
    response = client.get("/api/exchange/binance")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    ex = data["data"]
    assert ex["id"] == "binance"
    assert "name" in ex


def test_api_categories_endpoint():
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    if data["data"]:
        cat = data["data"][0]
        assert "id" in cat
        assert "name" in cat


def test_api_search_categorized():
    response = client.get("/api/search?q=bit")
    assert response.status_code == 200
    data = response.json()
    assert "coins" in data
    assert "exchanges" in data
    assert "categories" in data


def test_api_chart_timeframes():
    for days in [1, 7, 30, 90, 365, 3650]:
        response = client.get(f"/api/coin/bitcoin/chart?days={days}")
        assert response.status_code == 200
        data = response.json()
        assert data["days"] == days
        assert "prices" in data
