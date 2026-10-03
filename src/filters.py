"""
filters.py – Pure filter functions on list[Coin] or DataFrame.

None values are skipped safely (a coin with price=None is excluded
from price filters rather than raising an error).
"""

from typing import Optional
from .models import Coin


# ---------------------------------------------------------------------------
# Price filters
# ---------------------------------------------------------------------------

def filter_min_price(coins: list[Coin], min_price: float) -> list[Coin]:
    """Keep only coins with price >= min_price (None price excluded)."""
    return [c for c in coins if c.price is not None and c.price >= min_price]


def filter_max_price(coins: list[Coin], max_price: float) -> list[Coin]:
    """Keep only coins with price <= max_price (None price excluded)."""
    return [c for c in coins if c.price is not None and c.price <= max_price]


# ---------------------------------------------------------------------------
# Change filters
# ---------------------------------------------------------------------------

def filter_min_change(coins: list[Coin], min_change: float) -> list[Coin]:
    """Keep only coins with change_24h >= min_change (None excluded)."""
    return [c for c in coins if c.change_24h is not None and c.change_24h >= min_change]


def filter_max_change(coins: list[Coin], max_change: float) -> list[Coin]:
    """Keep only coins with change_24h <= max_change (None excluded)."""
    return [c for c in coins if c.change_24h is not None and c.change_24h <= max_change]


# ---------------------------------------------------------------------------
# Gainers / Losers
# ---------------------------------------------------------------------------

def filter_gainers(coins: list[Coin]) -> list[Coin]:
    """Keep only coins with change_24h > 0, sorted descending."""
    gainers = [c for c in coins if c.change_24h is not None and c.change_24h > 0]
    return sorted(gainers, key=lambda c: c.change_24h, reverse=True)  # type: ignore[arg-type]


def filter_losers(coins: list[Coin]) -> list[Coin]:
    """Keep only coins with change_24h < 0, sorted ascending (biggest loss first)."""
    losers = [c for c in coins if c.change_24h is not None and c.change_24h < 0]
    return sorted(losers, key=lambda c: c.change_24h)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

def filter_watchlist(coins: list[Coin], symbols: list[str]) -> list[Coin]:
    """
    Keep only coins whose symbol appears in *symbols* (case-insensitive).

    Parameters
    ----------
    coins   : list[Coin]
    symbols : list[str]   e.g. ["BTC", "eth", "SOL"]

    Returns
    -------
    list[Coin] – preserves original ordering from *coins*.
    """
    upper_symbols = {s.upper() for s in symbols}
    return [c for c in coins if c.symbol.upper() in upper_symbols]


# ---------------------------------------------------------------------------
# Limit
# ---------------------------------------------------------------------------

def apply_limit(coins: list[Coin], limit: int) -> list[Coin]:
    """Return at most *limit* coins from the front of the list."""
    return coins[:limit]


# ---------------------------------------------------------------------------
# Composite apply_filters – called by main.py
# ---------------------------------------------------------------------------

def apply_filters(
    coins: list[Coin],
    *,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_change: Optional[float] = None,
    max_change: Optional[float] = None,
    gainers: bool = False,
    losers: bool = False,
    watchlist: Optional[list[str]] = None,
    limit: Optional[int] = None,
) -> list[Coin]:
    """
    Apply all requested filters in sequence:
    price → change → gainers/losers → watchlist → limit.

    Parameters
    ----------
    coins      : Full validated list (pre-filter).
    min_price  : Lower price bound (USD).
    max_price  : Upper price bound (USD).
    min_change : Lower 24h-change bound (%).
    max_change : Upper 24h-change bound (%).
    gainers    : If True, keep only positive-change coins (sorted desc).
    losers     : If True, keep only negative-change coins (sorted asc).
    watchlist  : List of ticker symbols to keep (case-insensitive).
    limit      : Max rows to return.

    Returns
    -------
    list[Coin]
    """
    result = list(coins)

    if min_price is not None:
        result = filter_min_price(result, min_price)
    if max_price is not None:
        result = filter_max_price(result, max_price)
    if min_change is not None:
        result = filter_min_change(result, min_change)
    if max_change is not None:
        result = filter_max_change(result, max_change)
    if gainers:
        result = filter_gainers(result)
    if losers:
        result = filter_losers(result)
    if watchlist:
        result = filter_watchlist(result, watchlist)
    if limit is not None:
        result = apply_limit(result, limit)

    return result
