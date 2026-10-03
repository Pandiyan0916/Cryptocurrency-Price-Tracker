"""
test_cli.py – Unit tests for CLI argument parsing and orchestration in main.py

Uses a monkeypatched scraper that returns deterministic sample Coins,
so NO network or browser is required.
"""

import sys
import pytest
from unittest.mock import patch, MagicMock

from src.models import Coin
from src.main import _build_parser, _validate_args, main


TIMESTAMP = "2026-01-01 00:00:00"


def make_sample_coins() -> list[Coin]:
    return [
        Coin(1, "Bitcoin",  "BTC",  67500.0, 3.42,  1_330_000_000_000.0, TIMESTAMP),
        Coin(2, "Ethereum", "ETH",  3450.0,  -1.20, 414_000_000_000.0,  TIMESTAMP),
        Coin(3, "Tether",   "USDT", 1.0,     0.01,  109_000_000_000.0,  TIMESTAMP),
        Coin(4, "Solana",   "SOL",  155.0,   -2.50, 71_000_000_000.0,   TIMESTAMP),
        Coin(5, "XRP",      "XRP",  0.61,    1.80,  33_000_000_000.0,   TIMESTAMP),
    ]


# ──────────────────────────────────────────────────
# Argument parsing
# ──────────────────────────────────────────────────

class TestArgParsing:
    def setup_method(self):
        self.parser = _build_parser()

    def test_defaults(self):
        args = self.parser.parse_args([])
        assert args.limit == 10
        assert args.headless is False
        assert args.gainers is False
        assert args.losers is False
        assert args.monitor is False
        assert args.no_save is False
        assert args.verbose is False

    def test_headless_flag(self):
        args = self.parser.parse_args(["--headless"])
        assert args.headless is True

    def test_limit_parsed(self):
        args = self.parser.parse_args(["--limit", "20"])
        assert args.limit == 20

    def test_min_price_parsed(self):
        args = self.parser.parse_args(["--min-price", "1000"])
        assert args.min_price == 1000.0

    def test_watch_parsed(self):
        args = self.parser.parse_args(["--watch", "BTC", "ETH"])
        assert args.watch == ["BTC", "ETH"]

    def test_alert_above_parsed(self):
        args = self.parser.parse_args(["--alert-above", "BTC:70000"])
        assert args.alert_above == [("BTC", 70000.0)]

    def test_alert_below_parsed(self):
        args = self.parser.parse_args(["--alert-below", "ETH:2000"])
        assert args.alert_below == [("ETH", 2000.0)]

    def test_gainers_flag(self):
        args = self.parser.parse_args(["--gainers"])
        assert args.gainers is True

    def test_losers_flag(self):
        args = self.parser.parse_args(["--losers"])
        assert args.losers is True

    def test_no_save_flag(self):
        args = self.parser.parse_args(["--no-save"])
        assert args.no_save is True

    def test_interval_parsed(self):
        args = self.parser.parse_args(["--monitor", "--interval", "30"])
        assert args.interval == 30


# ──────────────────────────────────────────────────
# Argument validation
# ──────────────────────────────────────────────────

class TestArgValidation:
    def setup_method(self):
        self.parser = _build_parser()

    def _make_args(self, **kwargs):
        defaults = {
            "limit": 10, "headless": False, "gainers": False, "losers": False,
            "monitor": False, "interval": 60, "no_save": False, "verbose": False,
            "min_price": None, "max_price": None, "min_change": None,
            "max_change": None, "watch": None, "alert_above": None, "alert_below": None,
        }
        defaults.update(kwargs)
        import argparse
        return argparse.Namespace(**defaults)

    def test_limit_zero_raises(self):
        args = self._make_args(limit=0)
        with pytest.raises(SystemExit):
            _validate_args(args, self.parser)

    def test_limit_101_raises(self):
        args = self._make_args(limit=101)
        with pytest.raises(SystemExit):
            _validate_args(args, self.parser)

    def test_gainers_and_losers_conflict_raises(self):
        args = self._make_args(gainers=True, losers=True)
        with pytest.raises(SystemExit):
            _validate_args(args, self.parser)

    def test_monitor_interval_below_10_raises(self):
        args = self._make_args(monitor=True, interval=5)
        with pytest.raises(SystemExit):
            _validate_args(args, self.parser)

    def test_valid_args_pass(self):
        args = self._make_args(limit=10, gainers=False, losers=False)
        # Should not raise
        _validate_args(args, self.parser)


# ──────────────────────────────────────────────────
# Full main() with monkeypatched scraper
# ──────────────────────────────────────────────────

class TestMainWithMockScraper:
    """
    Test the full orchestration pipeline using a fake scraper.
    No network or browser required.
    """

    def _run_main(self, argv: list[str]) -> int:
        """Patch scraper and storage, then call main() with given argv."""
        with (
            patch("src.main.scrape", return_value=make_sample_coins()),
            patch("src.main.save_all"),  # don't write real CSV files
            patch("sys.argv", ["run.py"] + argv),
        ):
            return main()

    def test_basic_run_exits_zero(self):
        assert self._run_main(["--headless", "--no-save"]) == 0

    def test_gainers_mode_exits_zero(self):
        assert self._run_main(["--headless", "--no-save", "--gainers"]) == 0

    def test_losers_mode_exits_zero(self):
        assert self._run_main(["--headless", "--no-save", "--losers"]) == 0

    def test_min_price_filter_exits_zero(self):
        assert self._run_main(["--headless", "--no-save", "--min-price", "1000"]) == 0

    def test_watch_exits_zero(self):
        assert self._run_main(["--headless", "--no-save", "--watch", "BTC", "ETH"]) == 0

    def test_alert_above_exits_zero(self, capsys):
        # BTC price = 67500 in sample coins; alert-above at 60000 should trigger
        self._run_main(["--headless", "--no-save", "--alert-above", "BTC:60000"])
        captured = capsys.readouterr()
        assert "ALERT" in captured.out

    def test_alert_below_exits_zero(self, capsys):
        # ETH price = 3450; alert-below at 4000 should trigger
        self._run_main(["--headless", "--no-save", "--alert-below", "ETH:4000"])
        captured = capsys.readouterr()
        assert "ALERT" in captured.out

    def test_scraper_error_exits_nonzero(self):
        with (
            patch("src.main.scrape", side_effect=RuntimeError("no internet")),
            patch("sys.argv", ["run.py", "--headless"]),
        ):
            result = main()
        assert result != 0

    def test_no_save_does_not_call_save(self):
        with (
            patch("src.main.scrape", return_value=make_sample_coins()),
            patch("src.main.save_all") as mock_save,
            patch("sys.argv", ["run.py", "--headless", "--no-save"]),
        ):
            main()
        mock_save.assert_not_called()

    def test_save_called_without_no_save(self):
        with (
            patch("src.main.scrape", return_value=make_sample_coins()),
            patch("src.main.save_all") as mock_save,
            patch("sys.argv", ["run.py", "--headless"]),
        ):
            main()
        mock_save.assert_called_once()
