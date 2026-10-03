"""
webapp/config.py - Configuration constants for CoinPulse web app.
"""

import os
from pathlib import Path

# Base Directory & Data Paths
_BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = _BASE_DIR / "data"
CSV_SNAPSHOT_PATH = DATA_DIR / "crypto_prices.csv"

# Upstream API Settings (CoinGecko)
COINGECKO_BASE_URL = os.getenv("COINGECKO_API_URL", "https://api.coingecko.com/api/v3")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "4.0"))


# Server-Side Cache TTLs (in seconds)
CACHE_TTL_MARKETS = int(os.getenv("CACHE_TTL_MARKETS", "60"))      # 60s for market prices
CACHE_TTL_GLOBAL = int(os.getenv("CACHE_TTL_GLOBAL", "120"))       # 2 min for global stats
CACHE_TTL_CHART = int(os.getenv("CACHE_TTL_CHART", "300"))         # 5 min for charts
CACHE_TTL_DETAIL = int(os.getenv("CACHE_TTL_DETAIL", "600"))       # 10 min for coin detail
CACHE_TTL_TRENDING = int(os.getenv("CACHE_TTL_TRENDING", "600"))   # 10 min for trending
CACHE_TTL_EXCHANGES = int(os.getenv("CACHE_TTL_EXCHANGES", "600")) # 10 min for exchanges
CACHE_TTL_CATEGORIES = int(os.getenv("CACHE_TTL_CATEGORIES", "600")) # 10 min for categories

# Server Settings
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
ALLOWED_CHART_DAYS = {1, 7, 30, 90, 365, 3650}

