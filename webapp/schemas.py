"""
webapp/schemas.py - Pydantic schemas for CoinPulse API endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class SyncRequest(BaseModel):
    token: str
    watchlist: List[Any] = Field(default_factory=list)
    portfolio: List[Any] = Field(default_factory=list)


class Sparkline7d(BaseModel):
    price: List[float] = Field(default_factory=list)


class MarketCoin(BaseModel):
    id: str
    symbol: str
    name: str
    image: Optional[str] = None
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    market_cap_rank: Optional[int] = None
    total_volume: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    price_change_percentage_1h_in_currency: Optional[float] = None
    price_change_percentage_24h_in_currency: Optional[float] = None
    price_change_percentage_7d_in_currency: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    sparkline_in_7d: Optional[Sparkline7d] = None


class MarketsResponse(BaseModel):
    source: str  # "live" or "snapshot"
    as_of: str
    page: int
    per_page: int
    total: int
    data: List[MarketCoin]


class GlobalStats(BaseModel):
    active_cryptocurrencies: int
    total_market_cap_usd: float
    total_volume_usd: float
    btc_dominance: float
    eth_dominance: float = 0.0
    market_cap_change_percentage_24h_usd: Optional[float] = 0.0


class GlobalResponse(BaseModel):
    source: str
    as_of: str
    data: GlobalStats


class CoinDetail(BaseModel):
    id: str
    symbol: str
    name: str
    description: str = ""
    image: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    current_price_usd: Optional[float] = None
    market_cap_usd: Optional[float] = None
    market_cap_rank: Optional[int] = None
    total_volume_usd: Optional[float] = None
    high_24h_usd: Optional[float] = None
    low_24h_usd: Optional[float] = None
    price_change_percentage_24h: Optional[float] = None
    ath_usd: Optional[float] = None
    ath_change_percentage: Optional[float] = None
    ath_date: Optional[str] = None
    atl_usd: Optional[float] = None
    atl_change_percentage: Optional[float] = None
    atl_date: Optional[str] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    max_supply: Optional[float] = None
    fdv_usd: Optional[float] = None
    price_change_percentage_1h: Optional[float] = None
    price_change_percentage_7d: Optional[float] = None
    price_change_percentage_14d: Optional[float] = None
    price_change_percentage_30d: Optional[float] = None
    price_change_percentage_1y: Optional[float] = None
    homepage_url: Optional[str] = None
    blockchain_site: Optional[str] = None


class CoinDetailResponse(BaseModel):
    source: str
    as_of: str
    data: CoinDetail


class CoinChartResponse(BaseModel):
    source: str
    as_of: str
    days: int
    prices: List[List[float]] = Field(default_factory=list)  # [[timestamp_ms, price], ...]


class SearchCoin(BaseModel):
    id: str
    name: str
    symbol: str
    market_cap_rank: Optional[int] = None
    thumb: Optional[str] = None


class SearchExchange(BaseModel):
    id: str
    name: str
    thumb: Optional[str] = None


class SearchCategory(BaseModel):
    id: str
    name: str


class SearchResponse(BaseModel):
    source: str
    query: str
    coins: List[SearchCoin] = Field(default_factory=list)
    exchanges: List[SearchExchange] = Field(default_factory=list)
    categories: List[SearchCategory] = Field(default_factory=list)


class TrendingResponse(BaseModel):
    source: str
    coins: List[MarketCoin]
    gainers: List[MarketCoin] = Field(default_factory=list)
    losers: List[MarketCoin] = Field(default_factory=list)


class ExchangeListItem(BaseModel):
    id: str
    name: str
    year_established: Optional[int] = None
    country: Optional[str] = None
    description: Optional[str] = ""
    url: Optional[str] = None
    image: Optional[str] = None
    trust_score: Optional[int] = None
    trust_score_rank: Optional[int] = None
    trade_volume_24h_btc: Optional[float] = None
    trade_volume_24h_usd: Optional[float] = None


class ExchangesResponse(BaseModel):
    source: str
    as_of: str
    page: int
    per_page: int
    total: int
    data: List[ExchangeListItem]


class ExchangeTicker(BaseModel):
    base: str
    target: str
    market_name: str
    last_price: Optional[float] = None
    volume: Optional[float] = None
    converted_volume_usd: Optional[float] = None
    trade_url: Optional[str] = None


class ExchangeDetail(BaseModel):
    id: str
    name: str
    year_established: Optional[int] = None
    country: Optional[str] = None
    description: Optional[str] = ""
    url: Optional[str] = None
    image: Optional[str] = None
    trust_score: Optional[int] = None
    trust_score_rank: Optional[int] = None
    trade_volume_24h_btc: Optional[float] = None
    trade_volume_24h_usd: Optional[float] = None
    tickers: List[ExchangeTicker] = Field(default_factory=list)


class ExchangeDetailResponse(BaseModel):
    source: str
    as_of: str
    data: ExchangeDetail


class CategoryListItem(BaseModel):
    id: str
    name: str
    market_cap: Optional[float] = None
    market_cap_change_24h: Optional[float] = None
    volume_24h: Optional[float] = None
    top_3_coins: List[str] = Field(default_factory=list)
    updated_at: Optional[str] = None


class CategoriesResponse(BaseModel):
    source: str
    as_of: str
    data: List[CategoryListItem]


class CategoryDetailResponse(BaseModel):
    source: str
    as_of: str
    id: str
    name: str
    description: Optional[str] = ""
    market_cap: Optional[float] = None
    market_cap_change_24h: Optional[float] = None
    volume_24h: Optional[float] = None
    coins: List[MarketCoin] = Field(default_factory=list)


class HealthStatus(BaseModel):
    status: str = "ok"
    upstream_status: str  # "ok", "rate_limited", "unreachable"
    active_source: str    # "live" or "snapshot"
    snapshot_timestamp: Optional[str] = None
    cache_entries: int = 0
    timestamp: str

