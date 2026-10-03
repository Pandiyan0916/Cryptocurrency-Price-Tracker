"""
models.py – Data model for a single cryptocurrency entry.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Coin:
    """
    Represents one row of scraped cryptocurrency data.

    Fields
    ------
    rank        : Market-cap ranking (1 = largest).
    name        : Full coin name, e.g. "Bitcoin".
    symbol      : Ticker symbol, e.g. "BTC".
    price       : Current USD price; None if unavailable or N/A.
    change_24h  : 24-hour price change as a percentage (negative = drop);
                  None if unavailable.
    market_cap  : Market capitalisation in USD; None if unavailable.
    timestamp   : UTC timestamp string when the row was scraped
                  (format from config.TIMESTAMP_FORMAT).
    """

    rank: int
    name: str
    symbol: str
    price: Optional[float]
    change_24h: Optional[float]
    market_cap: Optional[float]
    timestamp: str
