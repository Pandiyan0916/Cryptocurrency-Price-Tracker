"""
parsers.py – Pure parsing functions; NO Selenium imports here.

All functions are stateless and can be tested without a browser.
"""

import re
import logging
from typing import Optional
from bs4 import BeautifulSoup  # used only in parse_table_html

from .models import Coin

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Subscript digit mapping  (Unicode subscript numerals → ASCII digits)
# ---------------------------------------------------------------------------
_SUBSCRIPT_DIGITS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")

# Unicode minus / en-dash → ASCII minus
_UNICODE_MINUS = str.maketrans("\u2212\u2013\u2014", "---")

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    """Strip whitespace and translate unicode minus/en-dash."""
    return text.strip().translate(_UNICODE_MINUS)


def _is_null(text: str) -> bool:
    """Return True for sentinel values that mean 'no data'."""
    return text in {"", "--", "N/A", "?", "n/a", "NA", "∞"}


def _parse_abbreviation(value: str) -> Optional[float]:
    """
    Convert abbreviated numeric strings to float.

    Handles K (thousands), M (millions), B (billions), T (trillions).
    Returns None if unparseable.

    Examples
    --------
    "1.23B"  →  1_230_000_000.0
    "456.7M" →  456_700_000.0
    "9.1T"   →  9_100_000_000_000.0
    """
    text = value.upper().strip()
    multipliers = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
    suffix = text[-1] if text else ""
    if suffix in multipliers:
        try:
            return float(text[:-1].replace(",", "")) * multipliers[suffix]
        except ValueError:
            return None
    return None


def _parse_subscript_price(text: str) -> Optional[float]:
    """
    Handle tiny prices that use Unicode subscript zero notation.

    CoinMarketCap renders very small prices like 0.0₅1234 which means
    0.000001234 (5 zeros after the decimal point before the significant
    digits).  This is purely a display shorthand — the subscript digit
    tells us how many zeros follow the "0." prefix.

    Pattern matched: 0.0<subscript_digit><remaining_digits>
    E.g. "0.0₅1234" → "0.000001234"
    """
    # Translate subscript digits to ASCII first
    translated = text.translate(_SUBSCRIPT_DIGITS)
    # Match pattern like "0.0<N><more-digits>" where N came from a subscript
    m = re.match(r"^\$?0\.0(\d)(\d+)$", translated.replace(",", ""))
    if m:
        zero_count = int(m.group(1))
        significant = m.group(2)
        return float("0." + "0" * zero_count + significant)
    return None


# ---------------------------------------------------------------------------
# Public parsing functions
# ---------------------------------------------------------------------------

def parse_price(text: str) -> Optional[float]:
    """
    Parse a USD price string into a float.

    Handles: "$67,500.12", "$0.0001", "$1.23B" (abbreviated),
    subscript tiny prices (0.0₅1234), "--", "N/A", empty → None.

    Parameters
    ----------
    text : str
        Raw price text as seen in the DOM.

    Returns
    -------
    float or None
    """
    text = _clean(text)
    if _is_null(text):
        return None

    # Try subscript tiny price first (0.0₅123 style)
    if "₀" <= text[-1] <= "₉" or any(c in text for c in "₀₁₂₃₄₅₆₇₈₉"):
        result = _parse_subscript_price(text)
        if result is not None:
            return result

    # Strip $ and commas
    text = text.replace("$", "").replace(",", "")

    # Try abbreviation (K/M/B/T suffix)
    abbr = _parse_abbreviation(text)
    if abbr is not None:
        return abbr

    # Plain float
    try:
        return float(text)
    except ValueError:
        logger.debug("parse_price: could not parse %r", text)
        return None


def parse_percent(text: str) -> Optional[float]:
    """
    Parse a 24-hour percentage change string into a signed float.

    Handles: "+3.42%", "-1.2%", "3.42%", unicode minus, "--", empty → None.
    A down arrow or negative sign results in a negative value.

    Parameters
    ----------
    text : str
        Raw percentage text, e.g. "+3.42%" or "-1.20%".

    Returns
    -------
    float or None
    """
    text = _clean(text)
    if _is_null(text):
        return None

    # Remove % and any arrow characters
    text = text.replace("%", "").replace("▲", "").replace("▼", "").strip()

    # Remove explicit + sign (negative is already kept)
    text = text.lstrip("+")

    try:
        return float(text)
    except ValueError:
        logger.debug("parse_percent: could not parse %r", text)
        return None


def parse_market_cap(text: str) -> Optional[float]:
    """
    Parse a market-cap string into a float (USD).

    Handles: "$1,234,567,890", "$1.23B", "$456.7M", "--" → None.

    Parameters
    ----------
    text : str
        Raw market-cap text.

    Returns
    -------
    float or None
    """
    text = _clean(text).replace("$", "").replace(",", "")
    if _is_null(text):
        return None

    abbr = _parse_abbreviation(text)
    if abbr is not None:
        return abbr

    try:
        return float(text)
    except ValueError:
        logger.debug("parse_market_cap: could not parse %r", text)
        return None


def parse_rank(text: str) -> Optional[int]:
    """
    Parse a rank string to int, e.g. "1", " 2 " → 1, 2.

    Returns None on failure.
    """
    try:
        return int(_clean(text))
    except (ValueError, TypeError):
        logger.debug("parse_rank: could not parse %r", text)
        return None


# ---------------------------------------------------------------------------
# HTML table parser
# ---------------------------------------------------------------------------

def parse_table_html(html: str, limit: int, timestamp: str) -> list[Coin]:
    """
    Parse the outer HTML of a CoinMarketCap table (or fixture) into Coins.

    This function is **pure** – no Selenium, no network calls.
    It uses BeautifulSoup to navigate the DOM.

    Strategy
    --------
    * Locate ``<table> <tbody> <tr>`` rows.
    * Column positions (0-indexed) verified against live DOM (2026-10-02):
        0  – watchlist star icon (empty, skip)
        1  – rank number
        2  – name + symbol  (e.g. "BitcoinBTC")
        3  – price (USD)
        4  – 1h change %   (skip)
        5  – 24h change %  (signed)
        6  – 7d change %   (skip)
        7  – market cap (USD)
        8  – volume 24h  (skip)
        9  – circulating supply (skip)
       10  – sentiment (skip)
       11  – (empty, skip)

    * For each row the sign of 24h % is determined by:
        a. explicit "-" prefix in the text, or
        b. presence of ``color:var(--c-color-negative)`` style / "down" class.

    Parameters
    ----------
    html : str
        Raw HTML containing the table.
    limit : int
        Maximum number of Coin objects to return.
    timestamp : str
        UTC timestamp string to embed in each Coin.

    Returns
    -------
    list[Coin]
    """
    soup = BeautifulSoup(html, "html.parser")

    # Find the main table body; accept <tbody> or fallback to all <tr>
    tbody = soup.find("tbody")
    if tbody:
        rows = tbody.find_all("tr", recursive=False)
    else:
        rows = soup.find_all("tr")

    if not rows:
        logger.warning("parse_table_html: no <tr> rows found in HTML")
        return []

    coins: list[Coin] = []
    for row in rows:
        if len(coins) >= limit:
            break
        tds = row.find_all("td")
        if len(tds) < 8:
            logger.debug("parse_table_html: skipping short row (%d cols)", len(tds))
            continue

        # --- Rank (col 1) ---
        # col[0] is the watchlist star; col[1] is the numeric rank.
        # Rows where col[1] is empty/non-numeric are skipped
        # (e.g. the CMC20 Index promotional row at position 0).
        rank_text = tds[1].get_text(strip=True)
        rank = parse_rank(rank_text)
        if rank is None:
            logger.debug("parse_table_html: skipping non-rank row (col1=%r)", rank_text)
            continue

        # --- Name + Symbol (col 2) ---
        # Must contain an anchor to a cryptocurrency page (/currencies/<slug>/)
        name_td = tds[2]
        name_anchor = name_td.find("a", href=lambda h: h and "/currencies/" in h)
        if not name_anchor:
            logger.debug("parse_table_html: skipping row without /currencies/ anchor")
            continue

        inner_texts = [t.strip() for t in name_anchor.stripped_strings]
        if len(inner_texts) >= 2:
            name = inner_texts[0]
            symbol = inner_texts[1]
        elif len(inner_texts) == 1:
            text_blob = inner_texts[0]
            # symbol is ALL-CAPS 2-10 chars at the end, e.g. "BitcoinBTC"
            m = re.match(r"^(.+?)([A-Z][A-Z0-9]{1,9})$", text_blob)
            name, symbol = (m.group(1).strip(), m.group(2)) if m else (text_blob, "")
        else:
            name, symbol = "", ""

        if not name or not symbol:
            logger.debug("parse_table_html: skipping row with empty name or symbol")
            continue

        # --- Price (col 3) ---
        price_text = tds[3].get_text(strip=True)
        price = parse_price(price_text)

        # --- 24h % (col 5) --- (col4=1h%, col5=24h%, col6=7d%)
        change_td = tds[5]
        change_text = change_td.get_text(strip=True)
        change_24h = parse_percent(change_text)

        # Determine sign from class / style if text has no explicit sign
        if change_24h is not None and change_24h > 0:
            # Check for a "down" / negative indicator in the cell's HTML
            cell_html = str(change_td)
            negative_signals = [
                "color-red",
                "down",
                "--c-color-negative",
                "negative",
                "icon-Caret-down",
                "bearish",
            ]
            if any(sig in cell_html for sig in negative_signals):
                change_24h = -abs(change_24h)

        # --- Market Cap (col 7) ---
        market_cap_text = tds[7].get_text(strip=True)
        market_cap = parse_market_cap(market_cap_text)
        logger.debug("Row %s: name=%r sym=%r price=%s chg=%s mcap=%s",
                     rank, name, symbol, price, change_24h, market_cap)

        coins.append(
            Coin(
                rank=rank,
                name=name,
                symbol=symbol,
                price=price,
                change_24h=change_24h,
                market_cap=market_cap,
                timestamp=timestamp,
            )
        )

    return coins
