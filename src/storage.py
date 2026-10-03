"""
storage.py – Persist Coin data to CSV using pandas.

Two files are managed:
  * crypto_prices.csv    – Latest snapshot (overwritten each run).
  * historical_prices.csv – Append-only ledger; header written once.

Numeric columns are stored as machine-readable floats, never as
formatted strings like "$67,500" or "+3.42%".
"""

import logging
from pathlib import Path
from typing import Union

import pandas as pd

from .config import (
    CSV_SNAPSHOT,
    CSV_HISTORICAL,
    COLUMN_ORDER,
    DATA_DIR,
)
from .models import Coin

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_data_dir() -> None:
    """Create the data/ directory if it does not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _coins_to_df(coins: list[Coin]) -> pd.DataFrame:
    """Convert a list of Coin objects to a DataFrame in canonical column order."""
    records = []
    for c in coins:
        mcap = int(round(c.market_cap)) if c.market_cap is not None else None
        rank = int(c.rank) if c.rank is not None else None
        records.append(
            {
                "rank": rank,
                "name": c.name,
                "symbol": c.symbol,
                "price": c.price,
                "change_24h": c.change_24h,
                "market_cap": mcap,
                "timestamp": c.timestamp,
            }
        )
    df = pd.DataFrame(records, columns=COLUMN_ORDER)
    df["rank"] = df["rank"].astype("Int64")
    df["market_cap"] = df["market_cap"].astype("Int64")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["change_24h"] = pd.to_numeric(df["change_24h"], errors="coerce")
    return df


def _friendly_io_error(path: Path, exc: Exception) -> None:
    """Log a user-friendly message for IO errors (e.g. file open in Excel)."""
    logger.error(
        "Could not write to '%s': %s\n"
        "  Tip: close the file in Excel or any other program and try again.",
        path,
        exc,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_snapshot(coins: list[Coin]) -> None:
    """
    Overwrite crypto_prices.csv with the current snapshot.

    Parameters
    ----------
    coins : list[Coin]
        The fully validated list of coins for this run.
    """
    _ensure_data_dir()
    df = _coins_to_df(coins)
    try:
        df.to_csv(CSV_SNAPSHOT, index=False, encoding="utf-8")
        logger.info("Snapshot saved → %s (%d rows)", CSV_SNAPSHOT, len(df))
    except (PermissionError, OSError) as exc:
        _friendly_io_error(CSV_SNAPSHOT, exc)


def save_historical(coins: list[Coin]) -> None:
    """
    Append the current snapshot to historical_prices.csv.

    The header is written only when the file does not yet exist or is empty.
    Old rows are never overwritten.

    Parameters
    ----------
    coins : list[Coin]
        The fully validated list of coins for this run.
    """
    _ensure_data_dir()
    df = _coins_to_df(coins)

    write_header = not CSV_HISTORICAL.exists() or CSV_HISTORICAL.stat().st_size == 0
    try:
        df.to_csv(
            CSV_HISTORICAL,
            mode="a",
            index=False,
            header=write_header,
            encoding="utf-8",
        )
        logger.info(
            "Historical log updated → %s (+%d rows, header_written=%s)",
            CSV_HISTORICAL,
            len(df),
            write_header,
        )
    except (PermissionError, OSError) as exc:
        _friendly_io_error(CSV_HISTORICAL, exc)


def save_all(coins: list[Coin]) -> None:
    """
    Save both snapshot and historical CSV in one call.

    Parameters
    ----------
    coins : list[Coin]
    """
    save_snapshot(coins)
    save_historical(coins)


def count_historical_rows() -> int:
    """Return the current row count in historical_prices.csv (0 if missing)."""
    if not CSV_HISTORICAL.exists():
        return 0
    try:
        df = pd.read_csv(CSV_HISTORICAL)
        return len(df)
    except Exception:
        return 0
