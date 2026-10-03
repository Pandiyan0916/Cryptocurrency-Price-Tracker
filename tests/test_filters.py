"""
test_filters.py – Unit tests for filters.py
"""

import pytest

from src.models import Coin
from src.filters import (
    apply_filters,
    apply_limit,
    filter_gainers,
    filter_losers,
    filter_max_change,
    filter_max_price,
    filter_min_change,
    filter_min_price,
    filter_watchlist,
)


TIMESTAMP = "2026-01-01 00:00:00"


def make_coin(
    rank: int = 1,
    name: str = "Coin",
    symbol: str = "COIN",
    price: float | None = 100.0,
    change_24h: float | None = 0.0,
    market_cap: float | None = 1_000_000.0,
) -> Coin:
    return Coin(
        rank=rank,
        name=name,
        symbol=symbol,
        price=price,
        change_24h=change_24h,
        market_cap=market_cap,
        timestamp=TIMESTAMP,
    )


@pytest.fixture
def sample_coins():
    return [
        make_coin(1, "Bitcoin",  "BTC",  price=67500.0, change_24h=3.42),
        make_coin(2, "Ethereum", "ETH",  price=3450.0,  change_24h=-1.20),
        make_coin(3, "Tether",   "USDT", price=1.0,     change_24h=0.01),
        make_coin(4, "Solana",   "SOL",  price=155.0,   change_24h=-2.50),
        make_coin(5, "XRP",      "XRP",  price=0.61,    change_24h=1.80),
    ]


# ──────────────────────────────────────────────────
# Price filters
# ──────────────────────────────────────────────────

class TestPriceFilters:
    def test_min_price_excludes_below(self, sample_coins):
        result = filter_min_price(sample_coins, min_price=100.0)
        symbols = {c.symbol for c in result}
        assert "XRP" not in symbols
        assert "BTC" in symbols

    def test_max_price_excludes_above(self, sample_coins):
        result = filter_max_price(sample_coins, max_price=1000.0)
        symbols = {c.symbol for c in result}
        assert "BTC" not in symbols
        assert "USDT" in symbols

    def test_min_price_none_value_excluded(self):
        coins = [make_coin(price=None), make_coin(price=500.0)]
        result = filter_min_price(coins, min_price=100.0)
        assert len(result) == 1
        assert result[0].price == 500.0

    def test_max_price_none_value_excluded(self):
        coins = [make_coin(price=None), make_coin(price=50.0)]
        result = filter_max_price(coins, max_price=100.0)
        assert len(result) == 1

    def test_min_price_equal_is_included(self, sample_coins):
        result = filter_min_price(sample_coins, min_price=155.0)
        assert any(c.symbol == "SOL" for c in result)


# ──────────────────────────────────────────────────
# Change filters
# ──────────────────────────────────────────────────

class TestChangeFilters:
    def test_min_change(self, sample_coins):
        result = filter_min_change(sample_coins, min_change=0.0)
        for c in result:
            assert c.change_24h is not None and c.change_24h >= 0.0

    def test_max_change(self, sample_coins):
        result = filter_max_change(sample_coins, max_change=0.0)
        for c in result:
            assert c.change_24h is not None and c.change_24h <= 0.0

    def test_min_change_none_excluded(self):
        coins = [make_coin(change_24h=None), make_coin(change_24h=2.0)]
        result = filter_min_change(coins, min_change=0.0)
        assert len(result) == 1

    def test_max_change_none_excluded(self):
        coins = [make_coin(change_24h=None), make_coin(change_24h=-1.0)]
        result = filter_max_change(coins, max_change=0.0)
        assert len(result) == 1


# ──────────────────────────────────────────────────
# Gainers / Losers
# ──────────────────────────────────────────────────

class TestGainersLosers:
    def test_gainers_only_positive(self, sample_coins):
        result = filter_gainers(sample_coins)
        for c in result:
            assert c.change_24h > 0

    def test_gainers_sorted_descending(self, sample_coins):
        result = filter_gainers(sample_coins)
        changes = [c.change_24h for c in result]
        assert changes == sorted(changes, reverse=True)

    def test_losers_only_negative(self, sample_coins):
        result = filter_losers(sample_coins)
        for c in result:
            assert c.change_24h < 0

    def test_losers_sorted_ascending(self, sample_coins):
        result = filter_losers(sample_coins)
        changes = [c.change_24h for c in result]
        assert changes == sorted(changes)

    def test_no_gainers_empty_result(self):
        all_losers = [make_coin(change_24h=-1.0), make_coin(change_24h=-2.0)]
        assert filter_gainers(all_losers) == []

    def test_no_losers_empty_result(self):
        all_gainers = [make_coin(change_24h=1.0), make_coin(change_24h=2.0)]
        assert filter_losers(all_gainers) == []

    def test_gainers_excludes_none_change(self):
        coins = [make_coin(change_24h=None), make_coin(change_24h=5.0)]
        result = filter_gainers(coins)
        assert len(result) == 1

    def test_losers_excludes_none_change(self):
        coins = [make_coin(change_24h=None), make_coin(change_24h=-5.0)]
        result = filter_losers(coins)
        assert len(result) == 1


# ──────────────────────────────────────────────────
# Watchlist
# ──────────────────────────────────────────────────

class TestWatchlist:
    def test_exact_match(self, sample_coins):
        result = filter_watchlist(sample_coins, ["BTC"])
        assert len(result) == 1
        assert result[0].symbol == "BTC"

    def test_case_insensitive(self, sample_coins):
        result = filter_watchlist(sample_coins, ["btc", "eth"])
        symbols = {c.symbol for c in result}
        assert "BTC" in symbols
        assert "ETH" in symbols

    def test_unknown_symbol_returns_empty(self, sample_coins):
        result = filter_watchlist(sample_coins, ["UNKNOWN"])
        assert result == []

    def test_multiple_symbols(self, sample_coins):
        result = filter_watchlist(sample_coins, ["BTC", "SOL", "XRP"])
        assert len(result) == 3


# ──────────────────────────────────────────────────
# Limit
# ──────────────────────────────────────────────────

class TestApplyLimit:
    def test_limit_trims_list(self, sample_coins):
        result = apply_limit(sample_coins, 3)
        assert len(result) == 3

    def test_limit_larger_than_list_returns_all(self, sample_coins):
        result = apply_limit(sample_coins, 100)
        assert len(result) == len(sample_coins)

    def test_limit_zero_returns_empty(self, sample_coins):
        result = apply_limit(sample_coins, 0)
        assert result == []


# ──────────────────────────────────────────────────
# Composite apply_filters
# ──────────────────────────────────────────────────

class TestApplyFilters:
    def test_empty_coins_with_filters_returns_empty(self):
        result = apply_filters([], min_price=100.0)
        assert result == []

    def test_no_filters_returns_all(self, sample_coins):
        result = apply_filters(sample_coins)
        assert len(result) == len(sample_coins)

    def test_combined_min_price_and_gainers(self, sample_coins):
        # BTC: price=67500, change=+3.42 → should appear
        # XRP: price=0.61, change=+1.80 → excluded by min_price=1.0
        result = apply_filters(sample_coins, min_price=1.0, gainers=True)
        for c in result:
            assert c.price >= 1.0
            assert c.change_24h > 0

    def test_watchlist_with_limit(self, sample_coins):
        result = apply_filters(sample_coins, watchlist=["BTC", "ETH", "SOL"], limit=2)
        assert len(result) == 2

    def test_no_match_returns_empty(self, sample_coins):
        result = apply_filters(sample_coins, min_price=1_000_000.0)
        assert result == []
