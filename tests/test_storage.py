"""
test_storage.py – Unit tests for storage.py (no network, uses tmp_path).
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch

from src.models import Coin
from src import storage as storage_module
from src.config import COLUMN_ORDER


TIMESTAMP = "2026-01-01 00:00:00"


def make_coins(n: int = 3) -> list[Coin]:
    return [
        Coin(
            rank=i,
            name=f"Coin{i}",
            symbol=f"C{i}",
            price=float(i * 100),
            change_24h=float(i * 0.5),
            market_cap=float(i * 1_000_000),
            timestamp=TIMESTAMP,
        )
        for i in range(1, n + 1)
    ]


@pytest.fixture(autouse=True)
def redirect_paths(tmp_path, monkeypatch):
    """Redirect all CSV writes to tmp_path for isolation."""
    snapshot = tmp_path / "crypto_prices.csv"
    historical = tmp_path / "historical_prices.csv"
    monkeypatch.setattr(storage_module, "CSV_SNAPSHOT", snapshot)
    monkeypatch.setattr(storage_module, "CSV_HISTORICAL", historical)
    monkeypatch.setattr(storage_module, "DATA_DIR", tmp_path)
    return snapshot, historical


# ──────────────────────────────────────────────────
# save_snapshot
# ──────────────────────────────────────────────────

class TestSaveSnapshot:
    def test_file_created(self, tmp_path):
        storage_module.save_snapshot(make_coins())
        assert storage_module.CSV_SNAPSHOT.exists()

    def test_column_order(self, tmp_path):
        storage_module.save_snapshot(make_coins())
        df = pd.read_csv(storage_module.CSV_SNAPSHOT)
        assert list(df.columns) == COLUMN_ORDER

    def test_row_count_matches(self, tmp_path):
        coins = make_coins(5)
        storage_module.save_snapshot(coins)
        df = pd.read_csv(storage_module.CSV_SNAPSHOT)
        assert len(df) == 5

    def test_snapshot_overwritten(self, tmp_path):
        storage_module.save_snapshot(make_coins(3))
        storage_module.save_snapshot(make_coins(7))  # second call
        df = pd.read_csv(storage_module.CSV_SNAPSHOT)
        assert len(df) == 7, "Snapshot should be overwritten, not appended"

    def test_numeric_dtypes(self, tmp_path):
        storage_module.save_snapshot(make_coins())
        df = pd.read_csv(storage_module.CSV_SNAPSHOT)
        assert pd.api.types.is_numeric_dtype(df["price"])
        assert pd.api.types.is_numeric_dtype(df["change_24h"])
        assert pd.api.types.is_numeric_dtype(df["market_cap"])

    def test_no_dollar_sign_in_price(self, tmp_path):
        storage_module.save_snapshot(make_coins())
        text = storage_module.CSV_SNAPSHOT.read_text()
        assert "$" not in text

    def test_no_scientific_notation_in_csv(self, tmp_path):
        large_coin = [
            Coin(
                rank=1,
                name="Bitcoin",
                symbol="BTC",
                price=86559.58,
                change_24h=3.16,
                market_cap=1_730_000_000_000.0,
                timestamp=TIMESTAMP,
            )
        ]
        storage_module.save_snapshot(large_coin)
        text = storage_module.CSV_SNAPSHOT.read_text(encoding="utf-8")
        assert "e+" not in text.lower(), f"CSV contains scientific notation: {text}"
        assert "1730000000000" in text

    def test_timestamp_format(self, tmp_path):
        storage_module.save_snapshot(make_coins())
        df = pd.read_csv(storage_module.CSV_SNAPSHOT)
        assert df["timestamp"].iloc[0] == TIMESTAMP

    def test_none_values_become_nan(self, tmp_path):
        coins = [Coin(1, "Test", "TST", None, None, None, TIMESTAMP)]
        storage_module.save_snapshot(coins)
        df = pd.read_csv(storage_module.CSV_SNAPSHOT)
        assert df["price"].isna().all()


# ──────────────────────────────────────────────────
# save_historical
# ──────────────────────────────────────────────────

class TestSaveHistorical:
    def test_file_created_on_first_call(self, tmp_path):
        storage_module.save_historical(make_coins())
        assert storage_module.CSV_HISTORICAL.exists()

    def test_header_written_once(self, tmp_path):
        storage_module.save_historical(make_coins(3))
        storage_module.save_historical(make_coins(3))
        text = storage_module.CSV_HISTORICAL.read_text()
        # Header should appear exactly once
        assert text.count("rank,name,symbol") == 1

    def test_append_grows_file(self, tmp_path):
        storage_module.save_historical(make_coins(3))  # 3 rows
        storage_module.save_historical(make_coins(4))  # 4 more rows
        df = pd.read_csv(storage_module.CSV_HISTORICAL)
        assert len(df) == 7

    def test_old_rows_preserved(self, tmp_path):
        coins_first = make_coins(2)
        storage_module.save_historical(coins_first)
        coins_second = make_coins(2)
        coins_second[0].symbol = "NEW"
        storage_module.save_historical(coins_second)
        df = pd.read_csv(storage_module.CSV_HISTORICAL)
        assert len(df) == 4


# ──────────────────────────────────────────────────
# PermissionError handling
# ──────────────────────────────────────────────────

class TestPermissionError:
    def test_snapshot_permission_error_logged(self, tmp_path, caplog):
        import logging
        with patch.object(pd.DataFrame, "to_csv", side_effect=PermissionError("locked")):
            with caplog.at_level(logging.ERROR):
                # Should NOT raise; should log a friendly message
                storage_module.save_snapshot(make_coins())
        assert any("Could not write" in r.message for r in caplog.records)

    def test_historical_permission_error_logged(self, tmp_path, caplog):
        import logging
        with patch.object(pd.DataFrame, "to_csv", side_effect=PermissionError("locked")):
            with caplog.at_level(logging.ERROR):
                storage_module.save_historical(make_coins())
        assert any("Could not write" in r.message for r in caplog.records)


# ──────────────────────────────────────────────────
# count_historical_rows
# ──────────────────────────────────────────────────

class TestCountHistoricalRows:
    def test_returns_zero_when_missing(self, tmp_path):
        assert storage_module.count_historical_rows() == 0

    def test_returns_correct_count(self, tmp_path):
        storage_module.save_historical(make_coins(5))
        assert storage_module.count_historical_rows() == 5
