"""
display.py – Terminal display of cryptocurrency data.

Renders a formatted ASCII table with aligned columns, a banner,
and a footer.  "N/A" is shown for missing (None) values.
"""

from datetime import datetime, timezone
from typing import Optional

from .models import Coin
from .config import TIMESTAMP_FORMAT


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_price(price: Optional[float]) -> str:
    """Format a USD price: >= $1 is 2 decimals with commas; < $1 is up to 6 sig digits trimmed."""
    if price is None:
        return "N/A"
    if price >= 1.0:
        return f"${price:,.2f}"

    # For price < 1.0: up to 6 significant figures, trailing zeros trimmed
    s = f"{price:.6g}"
    if "e" in s or "E" in s:
        s = f"{price:.10f}".rstrip("0").rstrip(".")
    elif "." in s:
        s = s.rstrip("0").rstrip(".")
    return f"${s}"


def _fmt_change(change: Optional[float]) -> str:
    """Format a 24h percentage change with sign."""
    if change is None:
        return "N/A"
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.2f}%"


def _fmt_market_cap(cap: Optional[float]) -> str:
    """Format a market cap with B/M/K suffix for readability."""
    if cap is None:
        return "N/A"
    if cap >= 1e12:
        return f"${cap / 1e12:.2f}T"
    if cap >= 1e9:
        return f"${cap / 1e9:.2f}B"
    if cap >= 1e6:
        return f"${cap / 1e6:.2f}M"
    if cap >= 1e3:
        return f"${cap / 1e3:.2f}K"
    return f"${cap:.2f}"


# ---------------------------------------------------------------------------
# Banner / footer
# ---------------------------------------------------------------------------

def _banner() -> str:
    lines = [
        "+--------------------------------------------------------------+",
        "|             Cryptocurrency Price Tracker                     |",
        "|              Live data from CoinMarketCap                    |",
        "+--------------------------------------------------------------+",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main display function
# ---------------------------------------------------------------------------

def display_coins(coins: list[Coin], timestamp: Optional[str] = None) -> None:
    """
    Print a formatted table of Coin data to stdout.

    If *coins* is empty, prints a 'no match' message instead.

    Parameters
    ----------
    coins     : Filtered (or unfiltered) list of Coin objects.
    timestamp : UTC timestamp string for the 'Last Updated' line.
                If None, the current UTC time is used.
    """
    print(_banner())
    print()

    ts = timestamp or datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)
    print(f"  Last Updated (UTC): {ts}")
    print()

    if not coins:
        print("  No cryptocurrencies match the filters.")
        print()
        return

    # --- Build rows ---
    headers = ["#", "Name", "Symbol", "Price (USD)", "24h Change", "Market Cap"]
    rows = []
    for c in coins:
        rows.append([
            str(c.rank),
            c.name,
            c.symbol,
            _fmt_price(c.price),
            _fmt_change(c.change_24h),
            _fmt_market_cap(c.market_cap),
        ])

    # --- Compute column widths ---
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    # --- Print table ---
    sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header_line = "|" + "|".join(
        f" {h:<{col_widths[i]}} " for i, h in enumerate(headers)
    ) + "|"

    print(sep)
    print(header_line)
    print(sep)
    for row in rows:
        line = "|" + "|".join(
            f" {cell:<{col_widths[i]}} " for i, cell in enumerate(row)
        ) + "|"
        print(line)
    print(sep)
    print()
    unit = "cryptocurrency" if len(coins) == 1 else "cryptocurrencies"
    print(f"  Showing {len(coins)} {unit}.")
    print()


def display_alert(symbol: str, price: float, threshold: float, direction: str) -> None:
    """
    Print a prominent ALERT line when a price threshold is crossed.

    Parameters
    ----------
    symbol    : Ticker symbol, e.g. "BTC".
    price     : Current price.
    threshold : The user-set threshold.
    direction : "above" or "below".
    """
    curr_str = _fmt_price(price)
    thresh_str = _fmt_price(threshold)
    print(f"\n  [ALERT] {symbol} price {curr_str} is {direction} target {thresh_str}!")
