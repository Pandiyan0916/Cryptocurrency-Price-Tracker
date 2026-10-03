"""
tests/test_webapp_fallback.py - Unit tests for CSV snapshot fallback reader.
"""

from pathlib import Path
import pytest
import pandas as pd

from webapp.services.fallback import get_snapshot_markets


def test_get_snapshot_markets_with_valid_csv(tmp_path):
    csv_file = tmp_path / "crypto_prices.csv"
    df = pd.DataFrame([
        {
            "rank": 1,
            "name": "Bitcoin",
            "symbol": "BTC",
            "price": 86000.0,
            "change_24h": 3.5,
            "market_cap": 1700000000000,
            "timestamp": "2026-10-02 12:00:00",
        },
        {
            "rank": 2,
            "name": "Ethereum",
            "symbol": "ETH",
            "price": 2700.0,
            "change_24h": 1.2,
            "market_cap": 330000000000,
            "timestamp": "2026-10-02 12:00:00",
        },
    ])
    df.to_csv(csv_file, index=False)

    coins, as_of, total = get_snapshot_markets(csv_path=csv_file, page=1, per_page=10)

    assert total == 2
    assert len(coins) == 2
    assert coins[0].name == "Bitcoin"
    assert coins[0].symbol == "btc"
    assert coins[0].current_price == 86000.0
    assert coins[0].market_cap_rank == 1
    assert coins[0].sparkline_in_7d is not None
    assert len(coins[0].sparkline_in_7d.price) == 7


def test_get_snapshot_markets_search_filter(tmp_path):
    csv_file = tmp_path / "crypto_prices.csv"
    df = pd.DataFrame([
        {"rank": 1, "name": "Bitcoin", "symbol": "BTC", "price": 86000.0, "change_24h": 3.5, "market_cap": 1700000000000, "timestamp": "2026-10-02 12:00:00"},
        {"rank": 2, "name": "Ethereum", "symbol": "ETH", "price": 2700.0, "change_24h": 1.2, "market_cap": 330000000000, "timestamp": "2026-10-02 12:00:00"},
    ])
    df.to_csv(csv_file, index=False)

    coins, _, total = get_snapshot_markets(csv_path=csv_file, query="eth")
    assert total == 1
    assert len(coins) == 1
    assert coins[0].name == "Ethereum"


def test_get_snapshot_markets_missing_file():
    non_existent = Path("non_existent_file_path_123.csv")
    coins, as_of, total = get_snapshot_markets(csv_path=non_existent)
    assert total == 0
    assert coins == []
