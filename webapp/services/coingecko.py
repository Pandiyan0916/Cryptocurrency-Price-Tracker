"""
webapp/services/coingecko.py - Async HTTP client for CoinGecko API v3 using httpx.
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

from webapp.config import API_TIMEOUT, COINGECKO_API_KEY, COINGECKO_BASE_URL
from webapp.schemas import (
    CoinDetail,
    GlobalStats,
    MarketCoin,
    SearchCoin,
    Sparkline7d,
)

logger = logging.getLogger(__name__)


class CoinGeckoError(Exception):
    """Base exception for CoinGecko API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class CoinGeckoRateLimitError(CoinGeckoError):
    """Exception raised when CoinGecko API returns 429 Too Many Requests."""
    def __init__(self, message: str = "CoinGecko API rate limit exceeded (HTTP 429)."):
        super().__init__(message, status_code=429)


class CoinGeckoClient:
    """Async wrapper for CoinGecko REST API endpoints."""

    def __init__(
        self,
        base_url: str = COINGECKO_BASE_URL,
        api_key: str = COINGECKO_API_KEY,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        timeout: float = API_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.transport = transport

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-cg-demo-api-key"] = self.api_key
        return headers

    async def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(transport=self.transport, timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params, headers=self._get_headers())
                if response.status_code == 429:
                    logger.warning("CoinGecko API rate limit hit (429) on %s", endpoint)
                    raise CoinGeckoRateLimitError()
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                logger.error("CoinGecko HTTP error %d on %s: %s", exc.response.status_code, endpoint, exc)
                if exc.response.status_code == 429:
                    raise CoinGeckoRateLimitError()
                raise CoinGeckoError(f"CoinGecko HTTP error {exc.response.status_code}", status_code=exc.response.status_code) from exc
            except httpx.TimeoutException as exc:
                logger.warning("CoinGecko request timeout (%.1fs) on %s", self.timeout, endpoint)
                raise CoinGeckoError(f"CoinGecko API request timed out after {self.timeout}s") from exc
            except httpx.RequestError as exc:
                logger.error("CoinGecko network error on %s: %s", endpoint, exc)
                raise CoinGeckoError(f"CoinGecko network request failed: {exc}") from exc


    async def fetch_markets(
        self,
        page: int = 1,
        per_page: int = 50,
        order: str = "market_cap_desc",
        vs_currency: str = "usd",
        sparkline: bool = True,
        ids: Optional[List[str]] = None,
    ) -> List[MarketCoin]:
        """Fetch market listing from /coins/markets."""
        params: Dict[str, Any] = {
            "vs_currency": vs_currency,
            "order": order,
            "per_page": per_page,
            "page": page,
            "sparkline": "true" if sparkline else "false",
            "price_change_percentage": "1h,24h,7d",
        }
        if ids:
            params["ids"] = ",".join(ids)

        raw_data = await self._request("/coins/markets", params=params)
        if not isinstance(raw_data, list):
            return []

        coins: List[MarketCoin] = []
        for item in raw_data:
            if not isinstance(item, dict):
                continue
            sparkline_raw = item.get("sparkline_in_7d", {}) or {}
            prices_list = sparkline_raw.get("price", []) if isinstance(sparkline_raw, dict) else []

            coins.append(
                MarketCoin(
                    id=str(item.get("id", "")),
                    symbol=str(item.get("symbol", "")).lower(),
                    name=str(item.get("name", "")),
                    image=item.get("image"),
                    current_price=item.get("current_price"),
                    market_cap=item.get("market_cap"),
                    market_cap_rank=item.get("market_cap_rank"),
                    total_volume=item.get("total_volume"),
                    high_24h=item.get("high_24h"),
                    low_24h=item.get("low_24h"),
                    price_change_percentage_1h_in_currency=item.get("price_change_percentage_1h_in_currency"),
                    price_change_percentage_24h_in_currency=item.get("price_change_percentage_24h_in_currency") or item.get("price_change_percentage_24h"),
                    price_change_percentage_7d_in_currency=item.get("price_change_percentage_7d_in_currency"),
                    circulating_supply=item.get("circulating_supply"),
                    total_supply=item.get("total_supply"),
                    sparkline_in_7d=Sparkline7d(price=prices_list) if prices_list else None,
                )
            )
        return coins

    async def fetch_global(self) -> GlobalStats:
        """Fetch global cryptocurrency statistics from /global."""
        raw = await self._request("/global")
        data = raw.get("data", {}) if isinstance(raw, dict) else {}
        total_mcap = data.get("total_market_cap", {}).get("usd", 0.0)
        total_vol = data.get("total_volume", {}).get("usd", 0.0)
        mcap_percentage = data.get("market_cap_percentage", {})
        btc_dom = mcap_percentage.get("btc", 0.0)
        eth_dom = mcap_percentage.get("eth", 0.0)
        mcap_change = data.get("market_cap_change_percentage_24h_usd", 0.0)

        return GlobalStats(
            active_cryptocurrencies=int(data.get("active_cryptocurrencies", 0)),
            total_market_cap_usd=float(total_mcap),
            total_volume_usd=float(total_vol),
            btc_dominance=float(btc_dom),
            eth_dominance=float(eth_dom),
            market_cap_change_percentage_24h_usd=float(mcap_change),
        )

    async def fetch_coin_detail(self, coin_id: str) -> CoinDetail:
        """Fetch full coin metadata from /coins/{id}."""
        raw = await self._request(
            f"/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false",
            },
        )
        if not isinstance(raw, dict):
            raise CoinGeckoError(f"Invalid response for coin {coin_id}")

        market_data = raw.get("market_data", {}) or {}
        image_dict = raw.get("image", {}) or {}
        links_dict = raw.get("links", {}) or {}
        desc_dict = raw.get("description", {}) or {}

        # Strip HTML tags from description if present
        desc_text = desc_dict.get("en", "") or ""
        import re
        clean_desc = re.sub(r"<[^>]+>", "", desc_text).strip()

        homepage_list = links_dict.get("homepage", [])
        homepage = homepage_list[0] if homepage_list and homepage_list[0] else None
        blockchain_list = links_dict.get("blockchain_site", [])
        blockchain = blockchain_list[0] if blockchain_list and blockchain_list[0] else None

        return CoinDetail(
            id=str(raw.get("id", coin_id)),
            symbol=str(raw.get("symbol", "")).lower(),
            name=str(raw.get("name", "")),
            description=clean_desc,
            image=image_dict.get("large") or image_dict.get("small"),
            categories=raw.get("categories", []) or [],
            current_price_usd=market_data.get("current_price", {}).get("usd"),
            market_cap_usd=market_data.get("market_cap", {}).get("usd"),
            market_cap_rank=raw.get("market_cap_rank"),
            total_volume_usd=market_data.get("total_volume", {}).get("usd"),
            high_24h_usd=market_data.get("high_24h", {}).get("usd"),
            low_24h_usd=market_data.get("low_24h", {}).get("usd"),
            price_change_percentage_24h=market_data.get("price_change_percentage_24h"),
            ath_usd=market_data.get("ath", {}).get("usd"),
            ath_change_percentage=market_data.get("ath_change_percentage", {}).get("usd"),
            ath_date=market_data.get("ath_date", {}).get("usd"),
            atl_usd=market_data.get("atl", {}).get("usd"),
            atl_change_percentage=market_data.get("atl_change_percentage", {}).get("usd"),
            atl_date=market_data.get("atl_date", {}).get("usd"),
            circulating_supply=market_data.get("circulating_supply"),
            total_supply=market_data.get("total_supply"),
            max_supply=market_data.get("max_supply"),
            fdv_usd=market_data.get("fully_diluted_valuation", {}).get("usd"),
            price_change_percentage_1h=market_data.get("price_change_percentage_1h_in_currency", {}).get("usd"),
            price_change_percentage_7d=market_data.get("price_change_percentage_7d_in_currency", {}).get("usd") or market_data.get("price_change_percentage_7d"),
            price_change_percentage_14d=market_data.get("price_change_percentage_14d_in_currency", {}).get("usd") or market_data.get("price_change_percentage_14d"),
            price_change_percentage_30d=market_data.get("price_change_percentage_30d_in_currency", {}).get("usd") or market_data.get("price_change_percentage_30d"),
            price_change_percentage_1y=market_data.get("price_change_percentage_1y_in_currency", {}).get("usd") or market_data.get("price_change_percentage_1y"),
            homepage_url=homepage,
            blockchain_site=blockchain,
        )

    async def fetch_coin_chart(self, coin_id: str, days: int = 7) -> List[List[float]]:
        """Fetch historical price chart data from /coins/{id}/market_chart."""
        param_days = "max" if days >= 3650 else str(days)
        raw = await self._request(
            f"/coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": param_days},
        )
        if isinstance(raw, dict) and "prices" in raw:
            return raw["prices"]
        return []

    async def search(self, query: str) -> Dict[str, Any]:
        """Search coins, exchanges, and categories via /search."""
        raw = await self._request("/search", params={"query": query})
        coins_raw = raw.get("coins", []) if isinstance(raw, dict) else []
        exchanges_raw = raw.get("exchanges", []) if isinstance(raw, dict) else []
        categories_raw = raw.get("categories", []) if isinstance(raw, dict) else []

        coins = [
            SearchCoin(
                id=str(c.get("id", "")),
                name=str(c.get("name", "")),
                symbol=str(c.get("symbol", "")),
                market_cap_rank=c.get("market_cap_rank"),
                thumb=c.get("thumb"),
            )
            for c in coins_raw[:15]
        ]

        from webapp.schemas import SearchExchange, SearchCategory
        exchanges = [
            SearchExchange(
                id=str(e.get("id", "")),
                name=str(e.get("name", "")),
                thumb=e.get("thumb") or e.get("large"),
            )
            for e in exchanges_raw[:10]
        ]

        categories = [
            SearchCategory(
                id=str(cat.get("id", "")),
                name=str(cat.get("name", "")),
            )
            for cat in categories_raw[:10]
        ]

        return {"coins": coins, "exchanges": exchanges, "categories": categories}

    async def fetch_trending(self) -> List[MarketCoin]:
        """Fetch trending coins via /search/trending and resolve their market details."""
        raw = await self._request("/search/trending")
        items = raw.get("coins", []) if isinstance(raw, dict) else []
        trending_ids = [str(item.get("item", {}).get("id")) for item in items if item.get("item", {}).get("id")]
        if not trending_ids:
            return []

        return await self.fetch_markets(page=1, per_page=len(trending_ids), ids=trending_ids)

    async def fetch_exchanges(self, page: int = 1, per_page: int = 50) -> List[Any]:
        """Fetch exchanges listing from /exchanges."""
        from webapp.schemas import ExchangeListItem
        raw = await self._request("/exchanges", params={"per_page": per_page, "page": page})
        if not isinstance(raw, list):
            return []

        exchanges: List[ExchangeListItem] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            exchanges.append(
                ExchangeListItem(
                    id=str(item.get("id", "")),
                    name=str(item.get("name", "")),
                    year_established=item.get("year_established"),
                    country=item.get("country"),
                    description=item.get("description", "") or "",
                    url=item.get("url"),
                    image=item.get("image"),
                    trust_score=item.get("trust_score"),
                    trust_score_rank=item.get("trust_score_rank"),
                    trade_volume_24h_btc=item.get("trade_volume_24h_btc"),
                    trade_volume_24h_usd=item.get("trade_volume_24h_btc", 0.0) * 85000.0 if item.get("trade_volume_24h_btc") else None,
                )
            )
        return exchanges

    async def fetch_exchange_detail(self, exchange_id: str) -> Any:
        """Fetch exchange detail and tickers from /exchanges/{id}."""
        from webapp.schemas import ExchangeDetail, ExchangeTicker
        raw = await self._request(f"/exchanges/{exchange_id}")
        if not isinstance(raw, dict):
            raise CoinGeckoError(f"Invalid response for exchange {exchange_id}")

        tickers_raw = raw.get("tickers", []) or []
        tickers: List[ExchangeTicker] = []
        for t in tickers_raw[:30]:
            market_info = t.get("market", {}) or {}
            tickers.append(
                ExchangeTicker(
                    base=str(t.get("base", "")),
                    target=str(t.get("target", "")),
                    market_name=str(market_info.get("name", raw.get("name", ""))),
                    last_price=t.get("last"),
                    volume=t.get("volume"),
                    converted_volume_usd=t.get("converted_volume", {}).get("usd"),
                    trade_url=t.get("trade_url"),
                )
            )

        vol_btc = raw.get("trade_volume_24h_btc")
        return ExchangeDetail(
            id=str(raw.get("id", exchange_id)),
            name=str(raw.get("name", "")),
            year_established=raw.get("year_established"),
            country=raw.get("country"),
            description=raw.get("description", "") or "",
            url=raw.get("url"),
            image=raw.get("image"),
            trust_score=raw.get("trust_score"),
            trust_score_rank=raw.get("trust_score_rank"),
            trade_volume_24h_btc=vol_btc,
            trade_volume_24h_usd=vol_btc * 85000.0 if vol_btc else None,
            tickers=tickers,
        )

    async def fetch_categories(self) -> List[Any]:
        """Fetch crypto categories from /coins/categories."""
        from webapp.schemas import CategoryListItem
        raw = await self._request("/coins/categories")
        if not isinstance(raw, list):
            return []

        categories: List[CategoryListItem] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            top_3 = item.get("top_3_coins", []) or []
            categories.append(
                CategoryListItem(
                    id=str(item.get("id", "")),
                    name=str(item.get("name", "")),
                    market_cap=item.get("market_cap"),
                    market_cap_change_24h=item.get("market_cap_change_24h"),
                    volume_24h=item.get("volume_24h"),
                    top_3_coins=top_3,
                    updated_at=item.get("updated_at"),
                )
            )
        return categories

