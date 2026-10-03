"""
test_validators.py – Unit tests for validators.py
"""

import pytest

from src.models import Coin
from src.validators import validate_coin, validate_coins


def make_coin(**overrides) -> Coin:
    """Return a valid Coin; caller can override any field."""
    defaults = {
        "rank": 1,
        "name": "Bitcoin",
        "symbol": "BTC",
        "price": 67500.0,
        "change_24h": 3.42,
        "market_cap": 1_330_000_000_000.0,
        "timestamp": "2026-01-01 00:00:00",
    }
    defaults.update(overrides)
    return Coin(**defaults)


# ──────────────────────────────────────────────────
# validate_coin (single record)
# ──────────────────────────────────────────────────

class TestValidateCoin:
    def test_valid_coin_passes(self):
        assert validate_coin(make_coin()) is True

    def test_none_price_is_accepted(self):
        assert validate_coin(make_coin(price=None)) is True

    def test_none_change_is_accepted(self):
        assert validate_coin(make_coin(change_24h=None)) is True

    def test_none_market_cap_is_accepted(self):
        assert validate_coin(make_coin(market_cap=None)) is True

    def test_empty_name_is_rejected(self):
        assert validate_coin(make_coin(name="")) is False

    def test_none_name_is_rejected(self):
        assert validate_coin(make_coin(name=None)) is False  # type: ignore[arg-type]

    def test_empty_symbol_is_rejected(self):
        assert validate_coin(make_coin(symbol="")) is False

    def test_none_symbol_is_rejected(self):
        assert validate_coin(make_coin(symbol=None)) is False  # type: ignore[arg-type]

    def test_non_int_rank_is_rejected(self):
        coin = make_coin()
        coin.rank = "one"  # type: ignore[assignment]
        assert validate_coin(coin) is False

    def test_zero_rank_is_rejected(self):
        assert validate_coin(make_coin(rank=0)) is False

    def test_negative_rank_is_rejected(self):
        assert validate_coin(make_coin(rank=-5)) is False

    def test_missing_timestamp_rejected(self):
        assert validate_coin(make_coin(timestamp="")) is False

    def test_string_price_rejected(self):
        coin = make_coin()
        coin.price = "$67,500"  # type: ignore[assignment]
        assert validate_coin(coin) is False

    def test_string_change_rejected(self):
        coin = make_coin()
        coin.change_24h = "3.42%"  # type: ignore[assignment]
        assert validate_coin(coin) is False

    def test_negative_price_accepted(self):
        # Negative price is mathematically valid (unusual but not filtered here)
        assert validate_coin(make_coin(price=-1.0)) is True

    def test_negative_change_accepted(self):
        assert validate_coin(make_coin(change_24h=-5.5)) is True


# ──────────────────────────────────────────────────
# validate_coins (list)
# ──────────────────────────────────────────────────

class TestValidateCoins:
    def test_empty_list_raises(self):
        with pytest.raises(RuntimeError, match="No cryptocurrency records"):
            validate_coins([])

    def test_all_invalid_raises(self):
        bad_coins = [make_coin(name=""), make_coin(symbol="")]
        with pytest.raises(RuntimeError, match="failed validation"):
            validate_coins(bad_coins)

    def test_mixed_drops_invalid(self):
        good = make_coin(rank=1)
        bad = make_coin(name="", rank=2)
        result = validate_coins([good, bad])
        assert len(result) == 1
        assert result[0].rank == 1

    def test_all_valid_passes(self):
        coins = [make_coin(rank=i, symbol=f"C{i}") for i in range(1, 6)]
        result = validate_coins(coins)
        assert len(result) == 5
