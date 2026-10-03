"""
config.py – Central configuration for the Cryptocurrency Price Tracker.

All constants are defined here. No credentials or personal data.
All times are UTC.
"""

# ---------------------------------------------------------------------------
# Source URL
# ---------------------------------------------------------------------------
import os

CMC_URL: str = "https://coinmarketcap.com/"
CHECK_HOST: str = os.getenv("CMC_CHECK_HOST", "coinmarketcap.com")
CHECK_PORT: int = int(os.getenv("CMC_CHECK_PORT", "443"))

# ---------------------------------------------------------------------------
# Scraping behaviour
# ---------------------------------------------------------------------------
DEFAULT_LIMIT: int = 10          # Top-N coins to collect (1..100)
PAGE_LOAD_TIMEOUT: int = 30      # seconds – hard browser timeout
ELEMENT_WAIT_TIMEOUT: int = 20   # seconds – WebDriverWait
SCRAPE_DELAY: float = 2.0        # seconds – polite pause after page load
RETRY_COUNT: int = 3             # max retry attempts on failure
RETRY_BACKOFF: float = 5.0       # seconds – sleep between retries

# ---------------------------------------------------------------------------
# Monitor mode
# ---------------------------------------------------------------------------
DEFAULT_MONITOR_INTERVAL: int = 60   # seconds between scrape cycles (min 10)
MAX_CONSECUTIVE_FAILURES: int = 3    # stop monitor after N consecutive errors

# ---------------------------------------------------------------------------
# Browser
# ---------------------------------------------------------------------------
HEADLESS_DEFAULT: bool = False        # False = visible window by default
WINDOW_SIZE: str = "1920,1080"

# ---------------------------------------------------------------------------
# Timestamp
# ---------------------------------------------------------------------------
TIMESTAMP_FORMAT: str = "%Y-%m-%d %H:%M:%S"   # UTC, ISO-8601-like

# ---------------------------------------------------------------------------
# CSV paths
# ---------------------------------------------------------------------------
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent  # project root
DATA_DIR: Path = _BASE_DIR / "data"
LOGS_DIR: Path = _BASE_DIR / "logs"

CSV_SNAPSHOT: Path = DATA_DIR / "crypto_prices.csv"          # overwritten each run
CSV_HISTORICAL: Path = DATA_DIR / "historical_prices.csv"    # append-only

# ---------------------------------------------------------------------------
# Column order (used by storage and display)
# ---------------------------------------------------------------------------
COLUMN_ORDER: list[str] = [
    "rank",
    "name",
    "symbol",
    "price",
    "change_24h",
    "market_cap",
    "timestamp",
]
