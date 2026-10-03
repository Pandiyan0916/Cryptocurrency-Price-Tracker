"""
webapp/services/fallback.py - Offline CSV snapshot fallback reader using src.storage structures.
"""

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

import pandas as pd

from webapp.config import CSV_SNAPSHOT_PATH
from webapp.schemas import MarketCoin, Sparkline7d


def get_snapshot_markets(
    csv_path: Optional[Path] = None,
    page: int = 1,
    per_page: int = 50,
    query: str = "",
) -> Tuple[List[MarketCoin], str, int]:
    """
    Read market data from data/crypto_prices.csv as a fallback.

    Returns
    -------
    Tuple[List[MarketCoin], str, int]
        (list of coins for the requested page, snapshot timestamp, total matching coins count)
    """
    target_path = csv_path or CSV_SNAPSHOT_PATH
    if not target_path.exists() or target_path.stat().st_size == 0:
        as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return [], as_of, 0

    try:
        df = pd.read_csv(target_path)
    except Exception:
        as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return [], as_of, 0

    if df.empty:
        as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return [], as_of, 0

    # Get timestamp from the first record if available
    first_ts = df["timestamp"].iloc[0] if "timestamp" in df.columns and len(df) > 0 else None
    as_of = str(first_ts) if first_ts and pd.notna(first_ts) else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Filter by search query if provided
    if query:
        q_lower = query.strip().lower()
        mask = df["name"].astype(str).str.lower().str.contains(q_lower) | \
               df["symbol"].astype(str).str.lower().str.contains(q_lower)
        df = df[mask]

    total_count = len(df)

    # Paginate
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paged_df = df.iloc[start_idx:end_idx]

    coins: List[MarketCoin] = []
    for _, row in paged_df.iterrows():
        rank = int(row["rank"]) if pd.notna(row.get("rank")) else None
        name = str(row["name"]) if pd.notna(row.get("name")) else "Unknown"
        symbol = str(row["symbol"]).lower() if pd.notna(row.get("symbol")) else "unk"
        price = float(row["price"]) if pd.notna(row.get("price")) else None
        change_24h = float(row["change_24h"]) if pd.notna(row.get("change_24h")) else None
        mcap = float(row["market_cap"]) if pd.notna(row.get("market_cap")) else None

        # Build simple flat sparkline array based on price and change
        sparkline_prices = []
        if price is not None:
            # Generate 7 synthetic points showing 7d trend matching 24h change direction
            chg = (change_24h or 0.0) / 100.0
            start_price = price / (1.0 + chg) if (1.0 + chg) != 0 else price
            for i in range(7):
                factor = 1.0 + (chg * (i / 6.0))
                sparkline_prices.append(round(start_price * factor, 6))

        coins.append(
            MarketCoin(
                id=symbol,
                symbol=symbol,
                name=name,
                image=f"https://assets.coingecko.com/coins/images/1/small/{symbol}.png",
                current_price=price,
                market_cap=mcap,
                market_cap_rank=rank,
                total_volume=mcap * 0.05 if mcap else None,
                price_change_percentage_24h_in_currency=change_24h,
                sparkline_in_7d=Sparkline7d(price=sparkline_prices) if sparkline_prices else None,
            )
        )

    return coins, as_of, total_count


def get_snapshot_exchanges(page: int = 1, per_page: int = 50) -> Tuple[List[Any], str, int]:
    """Provide structured offline fallback data for exchanges."""
    from webapp.schemas import ExchangeListItem

    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    sample_exchanges = [
        {"id": "binance", "name": "Binance", "year": 2017, "country": "Cayman Islands", "score": 10, "rank": 1, "vol_btc": 245000.0, "url": "https://www.binance.com"},
        {"id": "coinbase-exchange", "name": "Coinbase Exchange", "year": 2012, "country": "United States", "score": 10, "rank": 2, "vol_btc": 45000.0, "url": "https://www.coinbase.com"},
        {"id": "bybit-spot", "name": "Bybit", "year": 2018, "country": "British Virgin Islands", "score": 10, "rank": 3, "vol_btc": 68000.0, "url": "https://www.bybit.com"},
        {"id": "okex", "name": "OKX", "year": 2017, "country": "Seychelles", "score": 9, "rank": 4, "vol_btc": 54000.0, "url": "https://www.okx.com"},
        {"id": "kraken", "name": "Kraken", "year": 2011, "country": "United States", "score": 9, "rank": 5, "vol_btc": 22000.0, "url": "https://www.kraken.com"},
        {"id": "kucoin", "name": "KuCoin", "year": 2017, "country": "Seychelles", "score": 8, "rank": 6, "vol_btc": 18000.0, "url": "https://www.kucoin.com"},
        {"id": "gate", "name": "Gate.io", "year": 2013, "country": "Cayman Islands", "score": 8, "rank": 7, "vol_btc": 16000.0, "url": "https://www.gate.io"},
        {"id": "bitfinex", "name": "Bitfinex", "year": 2012, "country": "British Virgin Islands", "score": 8, "rank": 8, "vol_btc": 9500.0, "url": "https://www.bitfinex.com"},
    ]

    items = []
    for item in sample_exchanges:
        vol_btc = item["vol_btc"]
        items.append(
            ExchangeListItem(
                id=item["id"],
                name=item["name"],
                year_established=item["year"],
                country=item["country"],
                description=f"Offline snapshot entry for {item['name']}.",
                url=item["url"],
                image=f"https://assets.coingecko.com/markets/images/1/small/{item['id']}.png",
                trust_score=item["score"],
                trust_score_rank=item["rank"],
                trade_volume_24h_btc=vol_btc,
                trade_volume_24h_usd=vol_btc * 85000.0,
            )
        )
    return items, as_of, len(items)


def get_snapshot_categories() -> Tuple[List[Any], str]:
    """Provide structured offline fallback data for crypto categories."""
    from webapp.schemas import CategoryListItem

    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    sample_categories = [
        {"id": "layer-1", "name": "Layer 1 (L1)", "mcap": 1850000000000.0, "chg": 2.4, "vol": 45000000000.0, "top3": ["bitcoin", "ethereum", "solana"]},
        {"id": "smart-contract-platform", "name": "Smart Contract Platform", "mcap": 650000000000.0, "chg": 1.8, "vol": 22000000000.0, "top3": ["ethereum", "solana", "cardano"]},
        {"id": "decentralized-finance-defi", "name": "DeFi", "mcap": 95000000000.0, "chg": -0.8, "vol": 5200000000.0, "top3": ["uniswap", "aave", "maker"]},
        {"id": "meme-token", "name": "Meme", "mcap": 58000000000.0, "chg": 5.2, "vol": 8900000000.0, "top3": ["dogecoin", "shiba-inu", "pepe"]},
        {"id": "artificial-intelligence", "name": "AI & Big Data", "mcap": 32000000000.0, "chg": 3.1, "vol": 3100000000.0, "top3": ["render-token", "fetch-ai", "singularitynet"]},
        {"id": "layer-2", "name": "Layer 2 (L2)", "mcap": 24000000000.0, "chg": 0.5, "vol": 1800000000.0, "top3": ["polygon", "arbitrum", "optimism"]},
    ]

    items = []
    for c in sample_categories:
        items.append(
            CategoryListItem(
                id=c["id"],
                name=c["name"],
                market_cap=c["mcap"],
                market_cap_change_24h=c["chg"],
                volume_24h=c["vol"],
                top_3_coins=c["top3"],
                updated_at=as_of,
            )
        )
    return items, as_of

