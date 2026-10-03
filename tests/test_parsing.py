"""
test_parsing.py – Unit tests for parsers.py

No live internet required. The parse_table_html test uses
tests/fixtures/sample_table.html as a static fixture.
"""

import math
from pathlib import Path

import pytest

from src.parsers import (
    parse_market_cap,
    parse_percent,
    parse_price,
    parse_rank,
    parse_table_html,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_table.html"
TIMESTAMP = "2026-01-01 00:00:00"


# ──────────────────────────────────────────────────
# parse_price
# ──────────────────────────────────────────────────

class TestParsePrice:
    def test_standard_price_with_dollar_and_commas(self):
        assert parse_price("$67,500.12") == pytest.approx(67500.12)

    def test_price_no_dollar(self):
        assert parse_price("67500.12") == pytest.approx(67500.12)

    def test_price_with_only_commas(self):
        assert parse_price("$1,000") == pytest.approx(1000.0)

    def test_small_price(self):
        assert parse_price("$0.0001") == pytest.approx(0.0001)

    def test_very_small_price(self):
        assert parse_price("$0.00002543") == pytest.approx(0.00002543)

    def test_empty_string_returns_none(self):
        assert parse_price("") is None

    def test_double_dash_returns_none(self):
        assert parse_price("--") is None

    def test_na_returns_none(self):
        assert parse_price("N/A") is None

    def test_abbreviated_billion(self):
        result = parse_price("$1.23B")
        assert result == pytest.approx(1_230_000_000.0)

    def test_abbreviated_million(self):
        result = parse_price("$456.7M")
        assert result == pytest.approx(456_700_000.0)

    def test_abbreviated_thousand(self):
        result = parse_price("$9.1K")
        assert result == pytest.approx(9100.0)

    def test_abbreviated_trillion(self):
        result = parse_price("$1.5T")
        assert result == pytest.approx(1_500_000_000_000.0)

    def test_subscript_tiny_price(self):
        # 0.0₅1234 should become 0.000001234
        result = parse_price("$0.0₅1234")
        assert result == pytest.approx(0.000001234)

    def test_subscript_tiny_price_5898(self):
        # "$0.0₅5898" -> 0.000005898
        result = parse_price("$0.0₅5898")
        assert result == pytest.approx(0.000005898)


# ──────────────────────────────────────────────────
# parse_percent
# ──────────────────────────────────────────────────

class TestParsePercent:
    def test_positive_with_plus(self):
        assert parse_percent("+3.42%") == pytest.approx(3.42)

    def test_negative_with_minus(self):
        assert parse_percent("-1.20%") == pytest.approx(-1.20)

    def test_no_sign(self):
        assert parse_percent("3.42%") == pytest.approx(3.42)

    def test_unicode_minus(self):
        # U+2212 MINUS SIGN
        assert parse_percent("\u22121.5%") == pytest.approx(-1.5)

    def test_double_dash_returns_none(self):
        assert parse_percent("--") is None

    def test_empty_returns_none(self):
        assert parse_percent("") is None

    def test_na_returns_none(self):
        assert parse_percent("N/A") is None

    def test_zero_percent(self):
        assert parse_percent("+0.00%") == pytest.approx(0.0)

    def test_no_percent_symbol(self):
        assert parse_percent("2.5") == pytest.approx(2.5)


# ──────────────────────────────────────────────────
# parse_market_cap
# ──────────────────────────────────────────────────

class TestParseMarketCap:
    def test_full_number_with_commas(self):
        result = parse_market_cap("$1,234,567,890")
        assert result == pytest.approx(1_234_567_890.0)

    def test_abbreviated_trillion(self):
        result = parse_market_cap("$1.33T")
        assert result == pytest.approx(1_330_000_000_000.0)

    def test_abbreviated_billion(self):
        result = parse_market_cap("$414B")
        assert result == pytest.approx(414_000_000_000.0)

    def test_abbreviated_million(self):
        result = parse_market_cap("$500M")
        assert result == pytest.approx(500_000_000.0)

    def test_double_dash_returns_none(self):
        assert parse_market_cap("--") is None

    def test_empty_returns_none(self):
        assert parse_market_cap("") is None


# ──────────────────────────────────────────────────
# parse_rank
# ──────────────────────────────────────────────────

class TestParseRank:
    def test_integer_string(self):
        assert parse_rank("1") == 1

    def test_with_whitespace(self):
        assert parse_rank(" 42 ") == 42

    def test_non_numeric_returns_none(self):
        assert parse_rank("abc") is None

    def test_empty_returns_none(self):
        assert parse_rank("") is None


# ──────────────────────────────────────────────────
# parse_table_html (uses fixture)
# ──────────────────────────────────────────────────

class TestParseTableHtml:
    @pytest.fixture(autouse=True)
    def load_fixture(self):
        self.html = FIXTURE_PATH.read_text(encoding="utf-8")

    def test_returns_expected_row_count(self):
        coins = parse_table_html(self.html, limit=10, timestamp=TIMESTAMP)
        assert len(coins) == 10

    def test_limit_respected(self):
        coins = parse_table_html(self.html, limit=5, timestamp=TIMESTAMP)
        assert len(coins) == 5

    def test_real_fixture_ranks_and_btc(self):
        coins = parse_table_html(self.html, limit=10, timestamp=TIMESTAMP)
        assert len(coins) == 10
        ranks = [c.rank for c in coins]
        assert ranks == list(range(1, 11))
        assert coins[0].symbol == "BTC"
        assert coins[0].name == "Bitcoin"

    def test_promotional_index_first_row_skipped(self):
        promo_tr = "<tr><td></td><td>CMC20 Index</td><td>Featured</td><td>$100</td><td>0%</td><td>0%</td><td>0%</td><td>$1B</td></tr>"
        html_with_promo = self.html.replace("<tbody>", f"<tbody>\n{promo_tr}\n")
        coins = parse_table_html(html_with_promo, limit=10, timestamp=TIMESTAMP)
        assert len(coins) == 10
        assert coins[0].rank == 1
        assert coins[0].symbol == "BTC"
        assert [c.rank for c in coins] == list(range(1, 11))

    def test_first_coin_rank(self):
        coins = parse_table_html(self.html, limit=10, timestamp=TIMESTAMP)
        assert coins[0].rank == 1

    def test_first_coin_name(self):
        coins = parse_table_html(self.html, limit=10, timestamp=TIMESTAMP)
        assert coins[0].name == "Bitcoin"

    def test_first_coin_symbol(self):
        coins = parse_table_html(self.html, limit=10, timestamp=TIMESTAMP)
        assert coins[0].symbol == "BTC"

    def test_first_coin_price_is_float(self):
        coins = parse_table_html(self.html, limit=10, timestamp=TIMESTAMP)
        assert isinstance(coins[0].price, float)
        assert coins[0].price > 0

    def test_first_coin_change_positive(self):
        coins = parse_table_html(self.html, limit=10, timestamp=TIMESTAMP)
        assert isinstance(coins[0].change_24h, float)

    def test_second_coin_change_negative(self):
        coins = parse_table_html(self.html, limit=10, timestamp=TIMESTAMP)
        assert isinstance(coins[1].change_24h, float)

    def test_market_cap_is_float(self):
        coins = parse_table_html(self.html, limit=10, timestamp=TIMESTAMP)
        assert isinstance(coins[0].market_cap, float)
        assert coins[0].market_cap > 0

    def test_timestamp_propagated(self):
        coins = parse_table_html(self.html, limit=10, timestamp=TIMESTAMP)
        for c in coins:
            assert c.timestamp == TIMESTAMP

    def test_all_have_valid_symbols(self):
        coins = parse_table_html(self.html, limit=10, timestamp=TIMESTAMP)
        for c in coins:
            assert c.symbol and isinstance(c.symbol, str)

    def test_all_have_positive_rank(self):
        coins = parse_table_html(self.html, limit=10, timestamp=TIMESTAMP)
        for c in coins:
            assert c.rank > 0
