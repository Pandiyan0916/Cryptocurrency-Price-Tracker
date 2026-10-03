"""
validators.py – Validate scraped Coin records before saving.

Invalid records are dropped and logged at WARNING level.
If ALL records are invalid a RuntimeError is raised so the
caller can display a clear error and exit without saving.
"""

import logging
from typing import Optional
from .models import Coin

logger = logging.getLogger(__name__)


def _is_valid_numeric_or_none(value) -> bool:
    """Return True if value is None or a finite float/int."""
    if value is None:
        return True
    if isinstance(value, (int, float)):
        import math
        return math.isfinite(value)
    return False


def validate_coin(coin: Coin) -> bool:
    """
    Validate a single Coin record.

    Rules
    -----
    * rank    : must be a positive integer (> 0).
    * name    : must be a non-empty string.
    * symbol  : must be a non-empty string.
    * timestamp : must be a non-empty string.
    * price, change_24h, market_cap : must be float/int or None
                                      (None is acceptable; a string is not).

    Parameters
    ----------
    coin : Coin

    Returns
    -------
    bool
        True if valid; False (and a WARNING is logged) if invalid.
    """
    errors = []

    # rank
    if not isinstance(coin.rank, int) or coin.rank <= 0:
        errors.append(f"rank={coin.rank!r} is not a positive integer")

    # name
    if not coin.name or not isinstance(coin.name, str):
        errors.append(f"name={coin.name!r} is empty or not a string")

    # symbol
    if not coin.symbol or not isinstance(coin.symbol, str):
        errors.append(f"symbol={coin.symbol!r} is empty or not a string")

    # timestamp
    if not coin.timestamp or not isinstance(coin.timestamp, str):
        errors.append(f"timestamp={coin.timestamp!r} is empty or missing")

    # numeric-or-None fields
    for field_name, value in [
        ("price", coin.price),
        ("change_24h", coin.change_24h),
        ("market_cap", coin.market_cap),
    ]:
        if not _is_valid_numeric_or_none(value):
            errors.append(f"{field_name}={value!r} is not numeric or None")

    if errors:
        logger.warning(
            "Dropping coin rank=%s name=%r symbol=%r due to validation errors: %s",
            coin.rank,
            coin.name,
            coin.symbol,
            "; ".join(errors),
        )
        return False

    return True


def validate_coins(coins: list[Coin]) -> list[Coin]:
    """
    Validate a list of Coin records, dropping invalid ones.

    Raises RuntimeError if every record is invalid (nothing to save).

    Parameters
    ----------
    coins : list[Coin]

    Returns
    -------
    list[Coin]
        Only the valid records.

    Raises
    ------
    RuntimeError
        If the input is empty or every record fails validation.
    """
    if not coins:
        raise RuntimeError(
            "No cryptocurrency records were scraped. "
            "The page may not have loaded correctly."
        )

    valid = [c for c in coins if validate_coin(c)]

    if not valid:
        raise RuntimeError(
            f"All {len(coins)} scraped records failed validation. "
            "Nothing will be saved. Check WARNING logs for details."
        )

    dropped = len(coins) - len(valid)
    if dropped:
        logger.warning("%d of %d records failed validation and were dropped.", dropped, len(coins))

    return valid
