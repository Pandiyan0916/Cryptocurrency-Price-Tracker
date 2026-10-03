"""
scraper.py - Selenium-based scraper for CoinMarketCap.

Responsibilities
----------------
* Build a Chrome WebDriver with sensible options.
* Navigate to CoinMarketCap, handle cookie banners, wait for the table.
* Scroll if needed to load enough rows.
* Delegate all HTML parsing to parsers.parse_table_html (no parsing here).
* Retry with exponential-like back-off on transient failures.
* Always quit the driver in a finally block.

ETHICAL NOTE
------------
This scraper uses polite delays, does not bypass CAPTCHAs or rate limits,
and respects robots.txt in spirit.  It is intended for educational/demo use.
"""

import logging
import socket
import time
from datetime import datetime, timezone

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from . import config
from .config import (
    CMC_URL,
    ELEMENT_WAIT_TIMEOUT,
    PAGE_LOAD_TIMEOUT,
    RETRY_BACKOFF,
    RETRY_COUNT,
    SCRAPE_DELAY,
    TIMESTAMP_FORMAT,
    WINDOW_SIZE,
)
from .models import Coin
from .parsers import parse_table_html

logger = logging.getLogger(__name__)


def _check_network_connectivity(host: str | None = None, port: int | None = None, timeout: float = 3.0) -> None:
    """Pre-check socket connectivity to host:port before launching Chrome."""
    target_host = host if host is not None else config.CHECK_HOST
    target_port = port if port is not None else config.CHECK_PORT
    logger.info("Performing socket pre-check to %s:%d (timeout=%.1fs)...", target_host, target_port, timeout)
    last_err = None
    candidates: list[str] = []
    try:
        addrs = socket.getaddrinfo(target_host, target_port, socket.AF_INET, socket.SOCK_STREAM)
        candidates.extend([sockaddr[0] for _, _, _, _, sockaddr in addrs])
    except Exception as dns_err:
        last_err = dns_err

    # Fallback Cloudflare/AWS edge IPs ONLY for coinmarketcap.com
    if target_host == "coinmarketcap.com":
        fallback_ips = ["108.157.238.12", "108.157.238.10", "18.161.246.69"]
        for ip in fallback_ips:
            if ip not in candidates:
                candidates.append(ip)

    for ip in candidates:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, target_port))
            sock.close()
            logger.info("Socket pre-check successful (%s:%d reachability confirmed via %s).", target_host, target_port, ip)
            return
        except (socket.timeout, OSError) as err:
            last_err = err
            continue

    logger.error("Socket pre-check failed for %s:%d: %s", target_host, target_port, last_err)
    raise RuntimeError(
        f"Network connection to {target_host}:{target_port} failed (unreachable/timeout: {last_err}). "
        "Please check your internet connection or firewall/DNS settings."
    ) from last_err


# Selectors - positional / semantic; no hashed class names
_TABLE_SELECTOR = "table tbody tr"         # CSS selector for table rows
_COOKIE_SELECTORS = [                      # tried in order to dismiss cookie banner
    "button#onetrust-accept-btn-handler",
    "button[id*='accept']",
    "button[class*='accept']",
    "button[data-role='accept']",
    ".cmc-cookie-policy-banner__close",
    "button[aria-label*='Accept']",
    "button[aria-label*='accept']",
]


# ---------------------------------------------------------------------------
# Driver factory
# ---------------------------------------------------------------------------

def _build_driver(headless: bool) -> webdriver.Chrome:
    """
    Create and return a Chrome WebDriver instance.

    Parameters
    ----------
    headless : bool
        Run Chrome in headless mode when True.

    Returns
    -------
    webdriver.Chrome

    Raises
    ------
    RuntimeError
        With a friendly message if Chrome or ChromeDriver cannot be found.
    """
    opts = Options()

    # page_load_strategy=none: driver.get() returns immediately without waiting
    # for the full page load.  We use explicit WebDriverWait for elements.
    # This avoids the ARM64 Windows renderer-timeout that occurs when Chrome
    # waits for a JS-heavy page to signal 'load' complete.
    opts.page_load_strategy = "none"

    if headless:
        # Legacy --headless is more stable on ARM64 Windows than --headless=new
        opts.add_argument("--headless")

    opts.add_argument(f"--window-size={WINDOW_SIZE}")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    # ARM64 / renderer stability flags
    opts.add_argument("--disable-renderer-backgrounding")
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-backgrounding-occluded-windows")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-infobars")

    opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--log-level=3")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
    except WebDriverException as exc:
        msg = str(exc)
        if "chrome not found" in msg.lower() or "cannot find chrome" in msg.lower():
            raise RuntimeError(
                "Chrome browser not found.  Please install Google Chrome from "
                "https://www.google.com/chrome/ and try again."
            ) from exc
        raise RuntimeError(
            f"Failed to start ChromeDriver: {exc}\n"
            "  Try: pip install --upgrade webdriver-manager"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Unexpected error starting the browser: {exc}") from exc

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    # Prevent basic Selenium detection
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


# ---------------------------------------------------------------------------
# Cookie banner dismissal
# ---------------------------------------------------------------------------

def _dismiss_cookie_banner(driver: webdriver.Chrome) -> None:
    """Try each known cookie-banner dismiss selector; silently ignore if absent."""
    for selector in _COOKIE_SELECTORS:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, selector)
            if btn.is_displayed():
                btn.click()
                logger.debug("Dismissed cookie banner via selector: %s", selector)
                time.sleep(0.5)
                return
        except NoSuchElementException:
            continue
        except Exception as exc:
            logger.debug("Cookie banner dismiss attempt failed (%s): %s", selector, exc)


# ---------------------------------------------------------------------------
# Row waiting + scrolling
# ---------------------------------------------------------------------------

def _wait_for_rows_polling(driver: webdriver.Chrome, min_rows: int, max_wait: int = 60) -> int:
    """
    Poll for <tr> elements in the table until at least min_rows appear
    or max_wait seconds elapse.

    Returns the number of rows found.
    """
    poll_interval = 2
    elapsed = 0
    found = 0
    while elapsed < max_wait:
        found = len(driver.find_elements(By.CSS_SELECTOR, _TABLE_SELECTOR))
        if found >= min_rows:
            return found
        logger.debug("Polling rows: %d/%d (elapsed %ds)", found, min_rows, elapsed)
        time.sleep(poll_interval)
        elapsed += poll_interval
    return found


def _scroll_to_load_rows(driver: webdriver.Chrome, needed: int) -> None:
    """
    Gently scroll the page to trigger lazy-loading of additional rows.

    CoinMarketCap loads the default visible rows eagerly; extra rows may
    require scrolling.  We scroll in increments and wait for new rows.
    """
    max_scroll_attempts = 10
    scroll_step = 600  # pixels
    current_pos = 0

    for _ in range(max_scroll_attempts):
        current_rows = len(driver.find_elements(By.CSS_SELECTOR, _TABLE_SELECTOR))
        if current_rows >= needed:
            return
        current_pos += scroll_step
        driver.execute_script(f"window.scrollTo(0, {current_pos});")
        time.sleep(0.8)

    current_rows = len(driver.find_elements(By.CSS_SELECTOR, _TABLE_SELECTOR))
    if current_rows < needed:
        logger.warning(
            "Only %d rows loaded after scrolling; requested %d.",
            current_rows,
            needed,
        )


# ---------------------------------------------------------------------------
# Single scrape attempt
# ---------------------------------------------------------------------------

def _scrape_once(driver: webdriver.Chrome, limit: int, timestamp: str) -> list[Coin]:
    """
    Perform one scrape attempt using an already-open driver.

    Parameters
    ----------
    driver    : Initialised WebDriver.
    limit     : Number of rows to collect.
    timestamp : UTC string to embed in each Coin.

    Returns
    -------
    list[Coin]
    """
    logger.info("Navigating to %s", CMC_URL)
    # With page_load_strategy=none, driver.get() returns as soon as navigation
    # starts, without waiting for the page to finish loading.
    try:
        driver.get(CMC_URL)
    except Exception as nav_exc:
        # Non-fatal with page_load_strategy=none
        logger.debug("Navigation returned exception (may be non-fatal with none strategy): %s", nav_exc)

    # Step 1: wait for document.readyState == 'complete'
    logger.info("Waiting for document.readyState=complete...")
    try:
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        logger.info("Page DOM ready.")
    except Exception:
        logger.debug("document.readyState wait timed out; JS may still be rendering.")

    # Check for Chrome error pages (e.g. net::ERR_CONNECTION_TIMED_OUT or #main-frame-error)
    try:
        page_src = driver.page_source or ""
    except Exception:
        page_src = ""

    if "#main-frame-error" in page_src or "net::ERR_" in page_src or "error-code" in page_src:
        raise RuntimeError(
            "Chrome loaded a browser error page (e.g. net::ERR_CONNECTION_TIMED_OUT or main-frame-error). "
            "Network connection to CoinMarketCap failed."
        )

    # Step 2: polite delay for JS framework to render the table
    logger.info("Waiting %.1fs for JS render...", SCRAPE_DELAY)
    time.sleep(SCRAPE_DELAY)

    # Step 3: dismiss cookie/consent banner
    _dismiss_cookie_banner(driver)

    # Step 4: poll for table rows (up to 60s)
    min_rows = min(limit, 10)
    logger.info("Polling for table rows (need %d, timeout 60s)...", min_rows)
    found = _wait_for_rows_polling(driver, min_rows, max_wait=60)

    if found < min_rows:
        raise TimeoutException(
            f"Table rows did not appear within 60s "
            f"(found {found}, needed {min_rows}). "
            "The page may have a different structure or is blocking automation."
        )

    logger.info("Table rows found: %d. Scrolling for more if needed...", found)

    # Step 5: scroll to load additional rows if limit > initial count
    _scroll_to_load_rows(driver, limit)

    # Step 6: extract the full table HTML
    try:
        table_el = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )
        table_html = table_el.get_attribute("outerHTML")
    except TimeoutException:
        raise TimeoutException(
            "Could not locate the main <table> element. "
            "CoinMarketCap's page structure may have changed."
        )

    logger.info("Table HTML captured (%d chars). Parsing...", len(table_html))
    coins = parse_table_html(table_html, limit=limit, timestamp=timestamp)
    logger.info("Parsed %d coins from table HTML.", len(coins))
    return coins


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrape(
    limit: int = 10,
    headless: bool = False,
    watchlist: list[str] | None = None,
) -> list[Coin]:
    """
    Scrape the top *limit* cryptocurrencies from CoinMarketCap.

    Retries up to RETRY_COUNT times on transient errors.
    If a watchlist is supplied the effective fetch limit is
    max(limit, 50) so watchlist coins are more likely to be found.

    Parameters
    ----------
    limit     : Number of coins to return (1..100).
    headless  : Run Chrome headlessly when True.
    watchlist : Optional list of ticker symbols; widens the fetch if given.

    Returns
    -------
    list[Coin]

    Raises
    ------
    RuntimeError
        On unrecoverable errors (Chrome missing, repeated timeouts, etc.).
    """
    # Perform socket pre-check to coinmarketcap.com:443 (5s timeout) before launching Chrome
    _check_network_connectivity()

    # Widen the fetch if watchlist coins might be beyond the default limit
    effective_limit = max(limit, 50) if watchlist else limit

    timestamp = datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)

    last_exc: Exception | None = None
    for attempt in range(1, RETRY_COUNT + 1):
        driver: webdriver.Chrome | None = None
        try:
            logger.info(
                "Browser start (attempt %d/%d, headless=%s)", attempt, RETRY_COUNT, headless
            )
            driver = _build_driver(headless=headless)

            coins = _scrape_once(driver, limit=effective_limit, timestamp=timestamp)

            # Trim to the originally requested limit AFTER watchlist widening
            if not watchlist:
                coins = coins[:limit]

            return coins

        except (TimeoutException, WebDriverException) as exc:
            last_exc = exc
            logger.warning(
                "Scrape attempt %d/%d failed: %s", attempt, RETRY_COUNT, exc
            )
            if attempt < RETRY_COUNT:
                sleep_time = RETRY_BACKOFF * attempt
                logger.info("Retrying in %.0fs...", sleep_time)
                time.sleep(sleep_time)

        except RuntimeError:
            raise  # propagate immediately; retrying won't help

        finally:
            if driver is not None:
                try:
                    driver.quit()
                    logger.debug("Browser closed.")
                except Exception:
                    pass

    # All retries exhausted
    raise RuntimeError(
        f"Failed to scrape after {RETRY_COUNT} attempts. "
        f"Last error: {last_exc}\n"
        "  Possible causes: no internet, CoinMarketCap is blocking automation, "
        "or the page structure has changed.  See README Limitations."
    )
