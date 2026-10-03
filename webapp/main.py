"""
webapp/main.py - FastAPI application for CoinPulse Crypto Market Web Application.

Powered by CoinGecko API v3 REST Service with server-side caching, secure backend API key handling,
normalized schemas, explicit metadata (source='coingecko', as_of, data_age_seconds), and zero CSV snapshot fallback.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from webapp.config import (
    ALLOWED_CHART_DAYS,
    CACHE_TTL_CHART,
    CACHE_TTL_DETAIL,
    CACHE_TTL_GLOBAL,
    CACHE_TTL_MARKETS,
    CACHE_TTL_TRENDING,
)
from webapp.schemas import (
    RegisterRequest,
    LoginRequest,
    SyncRequest,
    CategoriesResponse,
    CoinChartResponse,
    CoinDetail,
    CoinDetailResponse,
    ExchangeDetail,
    ExchangeDetailResponse,
    ExchangesResponse,
    ExchangeTicker,
    GlobalResponse,
    GlobalStats,
    HealthStatus,
    MarketCoin,
    MarketsResponse,
    SearchCategory,
    SearchCoin,
    SearchExchange,
    SearchResponse,
    TrendingResponse,
)
from webapp.services.auth_db import (
    register_user,
    authenticate_user,
    get_user_by_token,
    get_user_sync_data,
    save_user_sync_data,
)
from webapp.services.cache import cache
from webapp.services.coingecko import (
    CoinGeckoClient,
    CoinGeckoError,
    CoinGeckoRateLimitError,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CoinPulse Crypto Market API",
    description="Live cryptocurrency market intelligence powered by CoinGecko API Service.",
    version="3.0.0",
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_coingecko_client() -> CoinGeckoClient:
    """Factory dependency for CoinGeckoClient."""
    return CoinGeckoClient()


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health_check(client: CoinGeckoClient = Depends(get_coingecko_client)):
    """Report API health, upstream CoinGecko status, data source, and cache entries."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    upstream_status = "ok"
    active_source = "coingecko"

    try:
        await client.fetch_global()
    except CoinGeckoRateLimitError:
        upstream_status = "rate_limited"
    except Exception:
        upstream_status = "unreachable"

    return {
        "status": "ok",
        "upstream_status": upstream_status,
        "active_source": active_source,
        "data_pipeline": "coingecko_api_v3",
        "cache_entries": cache.size(),
        "timestamp": now_str,
    }


@app.get("/api/markets", response_model=MarketsResponse)
async def get_markets(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    order: str = Query(default="market_cap_desc"),
    q: Optional[str] = Query(default=None),
    ids: Optional[str] = Query(default=None),
    refresh: bool = Query(default=False),
    client: CoinGeckoClient = Depends(get_coingecko_client),
):
    """
    Get top cryptocurrency market listings from CoinGecko API.
    Uses server-side cache and returns source='coingecko' with data freshness metadata.
    """
    query_str = (q or "").strip()
    id_list = [i.strip() for i in ids.split(",") if i.strip()] if ids else None
    cache_key = f"markets:{page}:{per_page}:{order}:{query_str}:{ids or ''}"

    if not refresh:
        cached_val = cache.get(cache_key)
        if cached_val:
            return cached_val

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        coins = await client.fetch_markets(
            page=page,
            per_page=per_page,
            order=order,
            ids=id_list,
        )

        if query_str:
            q_low = query_str.lower()
            coins = [c for c in coins if q_low in c.name.lower() or q_low in c.symbol.lower()]

        res = MarketsResponse(
            source="coingecko",
            as_of=now_str,
            page=page,
            per_page=per_page,
            total=len(coins),
            data=coins,
        )
        cache.set(cache_key, res, CACHE_TTL_MARKETS)
        return res

    except (CoinGeckoRateLimitError, CoinGeckoError, Exception) as exc:
        logger.warning("CoinGecko market fetch failed (%s). Checking stale cache...", exc)

        stale = cache.get_stale(cache_key)
        if stale:
            stale_res, created_at = stale
            stale_dt = datetime.fromtimestamp(created_at, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            stale_res.source = "coingecko"
            stale_res.as_of = f"Cached market data as of {stale_dt}"
            return stale_res

        raise HTTPException(
            status_code=503,
            detail="LIVE MARKET DATA TEMPORARILY UNAVAILABLE. CoinGecko API could not be reached or rate limit exceeded. Please retry.",
        )


@app.get("/api/global", response_model=GlobalResponse)
async def get_global_stats(client: CoinGeckoClient = Depends(get_coingecko_client)):
    """Get global cryptocurrency market stats from CoinGecko API."""
    cache_key = "global_stats"
    cached = cache.get(cache_key)
    if cached:
        return cached

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        stats = await client.fetch_global()
        res = GlobalResponse(source="coingecko", as_of=now_str, data=stats)
        cache.set(cache_key, res, CACHE_TTL_GLOBAL)
        return res
    except Exception as exc:
        stale = cache.get_stale(cache_key)
        if stale:
            stale_res, _ = stale
            return stale_res

        raise HTTPException(
            status_code=503,
            detail="Global market statistics temporarily unavailable from CoinGecko.",
        )


@app.get("/api/coin/{id}", response_model=CoinDetailResponse)
async def get_coin_detail(id: str, client: CoinGeckoClient = Depends(get_coingecko_client)):
    """Get comprehensive coin metadata and statistics from CoinGecko API."""
    coin_id = id.strip().lower()
    cache_key = f"coin_detail:{coin_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        detail = await client.fetch_coin_detail(coin_id)
        res = CoinDetailResponse(source="coingecko", as_of=now_str, data=detail)
        cache.set(cache_key, res, CACHE_TTL_DETAIL)
        return res
    except Exception:
        raise HTTPException(status_code=404, detail=f"Cryptocurrency '{coin_id}' not found.")


@app.get("/api/coin/{id}/chart", response_model=CoinChartResponse)
async def get_coin_chart(id: str, days: int = Query(default=7), client: CoinGeckoClient = Depends(get_coingecko_client)):
    """Get historical market price series from CoinGecko API."""
    if days not in ALLOWED_CHART_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid days parameter '{days}'. Must be one of {sorted(ALLOWED_CHART_DAYS)}."
        )

    coin_id = id.strip().lower()
    cache_key = f"coin_chart:{coin_id}:{days}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        prices = await client.fetch_coin_chart(coin_id, days=days)
        res = CoinChartResponse(source="coingecko", as_of=now_str, days=days, prices=prices)
        cache.set(cache_key, res, CACHE_TTL_CHART)
        return res
    except Exception:
        raise HTTPException(status_code=404, detail=f"Chart series for '{coin_id}' unavailable from CoinGecko.")


@app.get("/api/search", response_model=SearchResponse)
async def search_coins(q: str = Query(..., min_length=1), client: CoinGeckoClient = Depends(get_coingecko_client)):
    """Search cryptocurrencies, exchanges, and categories via CoinGecko API."""
    query_str = q.strip()
    cache_key = f"search:{query_str.lower()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        results = await client.search(query_str)
        res = SearchResponse(
            source="coingecko",
            query=query_str,
            coins=results.get("coins", []),
            exchanges=results.get("exchanges", []),
            categories=results.get("categories", []),
        )
        cache.set(cache_key, res, 300)
        return res
    except Exception:
        raise HTTPException(status_code=503, detail="Search service temporarily unavailable.")


@app.get("/api/trending", response_model=TrendingResponse)
async def get_trending_coins(client: CoinGeckoClient = Depends(get_coingecko_client)):
    """Get current top trending coins, gainers, and losers from CoinGecko API."""
    cache_key = "trending"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        results = await asyncio.gather(
            client.fetch_trending(),
            client.fetch_markets(page=1, per_page=50),
            return_exceptions=True
        )

        trending_res, markets_res = results[0], results[1]
        trending_coins = trending_res if isinstance(trending_res, list) else []
        top_markets = markets_res if isinstance(markets_res, list) else []

        valid_markets = [c for c in top_markets if c.price_change_percentage_24h_in_currency is not None]
        gainers = sorted(valid_markets, key=lambda c: c.price_change_percentage_24h_in_currency or 0.0, reverse=True)[:5]
        losers = sorted(valid_markets, key=lambda c: c.price_change_percentage_24h_in_currency or 0.0)[:5]

        if not trending_coins and not top_markets:
            raise Exception("Both trending and markets CoinGecko fetches failed")

        res = TrendingResponse(source="coingecko", coins=trending_coins if trending_coins else top_markets[:6], gainers=gainers, losers=losers)
        cache.set(cache_key, res, CACHE_TTL_TRENDING)
        return res
    except Exception:
        raise HTTPException(status_code=503, detail="Trending market data temporarily unavailable.")


@app.get("/api/exchanges", response_model=ExchangesResponse)
async def get_exchanges(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    client: CoinGeckoClient = Depends(get_coingecko_client),
):
    """Get list of verified exchanges with trust scores from CoinGecko API."""
    cache_key = f"exchanges:{page}:{per_page}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        exchanges = await client.fetch_exchanges(page=page, per_page=per_page)
        res = ExchangesResponse(
            source="coingecko",
            as_of=now_str,
            page=page,
            per_page=per_page,
            total=len(exchanges),
            data=exchanges,
        )
        cache.set(cache_key, res, 600)
        return res
    except Exception:
        raise HTTPException(status_code=503, detail="Exchanges list temporarily unavailable.")


@app.get("/api/exchange/{id}", response_model=ExchangeDetailResponse)
async def get_exchange_detail(id: str, client: CoinGeckoClient = Depends(get_coingecko_client)):
    """Get detailed exchange profile from CoinGecko API."""
    exchange_id = id.strip().lower()
    cache_key = f"exchange_detail:{exchange_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        detail = await client.fetch_exchange_detail(exchange_id)
        res = ExchangeDetailResponse(source="coingecko", as_of=now_str, data=detail)
        cache.set(cache_key, res, 600)
        return res
    except Exception:
        raise HTTPException(status_code=404, detail=f"Exchange '{exchange_id}' not found.")


@app.get("/api/categories")
async def get_categories(client: CoinGeckoClient = Depends(get_coingecko_client)):
    """Get crypto categories with market cap from CoinGecko API."""
    cache_key = "categories"
    cached = cache.get(cache_key)
    if cached:
        return cached

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        cats = await client.fetch_categories()
        res = CategoriesResponse(source="coingecko", as_of=now_str, data=cats)
        cache.set(cache_key, res, 600)
        return res
    except Exception:
        raise HTTPException(status_code=503, detail="Categories list temporarily unavailable.")


# ---------------------------------------------------------------------------
# Auth & User Sync Routes
# ---------------------------------------------------------------------------

@app.post("/api/auth/register")
async def api_register(req: RegisterRequest):
    """Register new user and return auth session token."""
    try:
        res = register_user(req.name, req.email, req.password)
        return {"status": "ok", "token": res["token"], "user": res["user"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed.")


@app.get("/api/auth/register")
async def api_register_info():
    """Auth registration endpoint info."""
    return {"status": "ok", "message": "Auth registration endpoint. Send POST request with JSON payload: {name, email, password}"}


@app.post("/api/auth/login")
async def api_login(req: LoginRequest):
    """Authenticate user with email and password."""
    try:
        res = authenticate_user(req.email, req.password)
        return {"status": "ok", "token": res["token"], "user": res["user"]}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed.")


@app.get("/api/auth/login")
async def api_login_info():
    """Auth login endpoint info."""
    return {"status": "ok", "message": "Auth login endpoint. Send POST request with JSON payload: {email, password}"}


@app.get("/api/user/sync")
async def api_get_sync(token: str = Query(...)):
    """Fetch user's synced watchlist and portfolio data."""
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session token.")
    data = get_user_sync_data(user["id"])
    return {"status": "ok", "user": user, "watchlist": data["watchlist"], "portfolio": data["portfolio"]}


@app.post("/api/user/sync")
async def api_save_sync(req: SyncRequest):
    """Save user's watchlist and portfolio items to database."""
    user = get_user_by_token(req.token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session token.")
    save_user_sync_data(user["id"], req.watchlist, req.portfolio)
    return {"status": "ok", "message": "Synced successfully"}


STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    fav_file = STATIC_DIR / "favicon.png"
    if fav_file.exists():
        return FileResponse(str(fav_file))
    raise HTTPException(status_code=404, detail="Favicon not found")


if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
