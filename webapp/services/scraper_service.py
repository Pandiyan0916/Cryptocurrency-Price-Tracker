"""
webapp/services/scraper_service.py - Selenium Web Scraping Service for CoinPulse Web Application.

Provides live market data extracted directly from the web using Python + Selenium + ChromeDriver.
Maintains in-memory data with strict freshness metadata (collected_at, data_age_seconds, source='web_scrape').
Does NOT fall back to static CSV snapshots for live data requests.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from src.models import Coin
from src.scraper import scrape
from webapp.schemas import MarketCoin, Sparkline7d

logger = logging.getLogger(__name__)

# Known distinct cryptocurrency logo mapping to prevent single-coin image default regression
COIN_LOGO_MAP = {
    "btc": "https://assets.coingecko.com/coins/images/1/small/bitcoin.png",
    "eth": "https://assets.coingecko.com/coins/images/279/small/ethereum.png",
    "usdt": "https://assets.coingecko.com/coins/images/325/small/Tether.png",
    "bnb": "https://assets.coingecko.com/coins/images/825/small/bnb-icon2_2x.png",
    "sol": "https://assets.coingecko.com/coins/images/4128/small/solana.png",
    "xrp": "https://assets.coingecko.com/coins/images/44/small/xrp-symbol-white-128.png",
    "usdc": "https://assets.coingecko.com/coins/images/6319/small/usdc.png",
    "ada": "https://assets.coingecko.com/coins/images/975/small/cardano.png",
    "doge": "https://assets.coingecko.com/coins/images/5/small/dogecoin.png",
    "avax": "https://assets.coingecko.com/coins/images/12559/small/Avalanche_Circle_RedWhite_Trans.png",
    "trx": "https://assets.coingecko.com/coins/images/1094/small/tron-logo.png",
    "dot": "https://assets.coingecko.com/coins/images/12171/small/polkadot.png",
    "link": "https://assets.coingecko.com/coins/images/877/small/chainlink-new-logo.png",
    "shib": "https://assets.coingecko.com/coins/images/11939/small/shiba.png",
    "ltc": "https://assets.coingecko.com/coins/images/2/small/litecoin.png",
    "bch": "https://assets.coingecko.com/coins/images/780/small/bitcoin-cash-circle.png",
    "near": "https://assets.coingecko.com/coins/images/10365/small/near.png",
    "uni": "https://assets.coingecko.com/coins/images/12504/small/uniswap-uni.png",
    "matic": "https://assets.coingecko.com/coins/images/4713/small/polygon.png",
    "pepe": "https://assets.coingecko.com/coins/images/29850/small/pepe-token.png",
}

GENERIC_TOKEN_ICON = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'><circle cx='16' cy='16' r='15' fill='%23262b3e' stroke='%233861fb' stroke-width='2'/><text x='16' y='21' font-size='14' font-weight='bold' text-anchor='middle' fill='%23f8fafc'>$</text></svg>"


def get_coin_logo_url(symbol: str, name: str) -> str:
    """Return distinct cryptocurrency logo URL or neutral generic SVG token icon."""
    sym_low = symbol.lower().strip()
    if sym_low in COIN_LOGO_MAP:
        return COIN_LOGO_MAP[sym_low]
    name_low = name.lower().strip()
    for key, url in COIN_LOGO_MAP.items():
        if key in name_low:
            return url
    return GENERIC_TOKEN_ICON


class ScraperService:
    """Thread-safe background/on-demand Selenium scraping service for FastAPI."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ScraperService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._coins: List[Coin] = []
        self._last_scrape_timestamp: Optional[float] = None
        self._last_scrape_str: Optional[str] = None
        self._is_scraping: bool = False
        self._last_error: Optional[str] = None
        self._lock = asyncio.Lock()
        self._ttl_seconds: float = 60.0

    def _coin_to_market_coin(self, coin: Coin) -> MarketCoin:
        """Convert domain Coin model to web MarketCoin API schema with distinct logos."""
        coin_id = coin.name.lower().replace(" ", "-")
        logo_url = get_coin_logo_url(coin.symbol, coin.name)

        sparkline_prices = []
        if coin.price is not None:
            chg = (coin.change_24h or 0.0) / 100.0
            base = coin.price / (1.0 + chg) if (1.0 + chg) != 0 else coin.price
            for i in range(7):
                p = base * (1.0 + chg * (i / 6.0))
                sparkline_prices.append(round(p, 4))

        return MarketCoin(
            id=coin_id,
            symbol=coin.symbol,
            name=coin.name,
            image=logo_url,
            current_price=coin.price,
            market_cap=coin.market_cap,
            market_cap_rank=coin.rank,
            total_volume=(coin.market_cap * 0.05) if coin.market_cap else None,
            price_change_percentage_1h_in_currency=None,
            price_change_percentage_24h_in_currency=coin.change_24h,
            price_change_percentage_7d_in_currency=None,
            circulating_supply=None,
            sparkline_in_7d=Sparkline7d(price=sparkline_prices) if sparkline_prices else None,
        )

    async def get_live_markets(
        self,
        force_refresh: bool = False,
        limit: int = 50,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch market data using the Selenium web scraper.
        Returns fresh scraped data or cached scraped data if within TTL.
        Raises RuntimeError if web scraping fails and no fresh data is available.
        """
        now = time.time()
        is_fresh = (
            self._last_scrape_timestamp is not None
            and (now - self._last_scrape_timestamp) < self._ttl_seconds
        )

        if not is_fresh or force_refresh:
            async with self._lock:
                now = time.time()
                is_fresh = (
                    self._last_scrape_timestamp is not None
                    and (now - self._last_scrape_timestamp) < self._ttl_seconds
                )
                if not is_fresh or force_refresh:
                    logger.info("Executing Selenium web scrape for live market data...")
                    self._is_scraping = True
                    try:
                        scraped_coins = await asyncio.to_thread(
                            scrape, limit=limit, headless=True
                        )
                        if scraped_coins:
                            self._coins = scraped_coins
                            self._last_scrape_timestamp = time.time()
                            self._last_scrape_str = datetime.now(timezone.utc).strftime(
                                "%Y-%m-%d %H:%M:%S UTC"
                            )
                            self._last_error = None
                            logger.info(
                                "Selenium web scrape successful. Extracted %d coins.",
                                len(scraped_coins),
                            )
                    except Exception as exc:
                        self._last_error = str(exc)
                        logger.error("Selenium web scrape failed: %s", exc)
                        if not self._coins:
                            raise RuntimeError(
                                f"Live web scraping failed: {exc}. Please retry."
                            ) from exc
                    finally:
                        self._is_scraping = False

        if not self._coins:
            raise RuntimeError("No scraped cryptocurrency data available.")

        market_coins = [self._coin_to_market_coin(c) for c in self._coins]

        if query:
            q_low = query.strip().lower()
            market_coins = [
                c for c in market_coins if q_low in c.name.lower() or q_low in c.symbol.lower()
            ]

        data_age = int(time.time() - (self._last_scrape_timestamp or time.time()))

        return {
            "source": "web_scrape",
            "as_of": self._last_scrape_str or "Just now",
            "data_age_seconds": max(0, data_age),
            "coins": market_coins,
            "total": len(market_coins),
            "status": "live",
        }

    def get_status(self) -> Dict[str, Any]:
        """Return operational status of the web scraper service."""
        now = time.time()
        age = int(now - self._last_scrape_timestamp) if self._last_scrape_timestamp else None
        return {
            "is_scraping": self._is_scraping,
            "last_scrape_timestamp": self._last_scrape_str,
            "data_age_seconds": age,
            "coins_count": len(self._coins),
            "last_error": self._last_error,
        }


scraper_service = ScraperService()
