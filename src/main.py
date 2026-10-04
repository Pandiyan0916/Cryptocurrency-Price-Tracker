"""
main.py – CLI entry point and orchestration for the Cryptocurrency Price Tracker.

Argument parsing, filter orchestration, alert checking, monitor mode,
and friendly top-level error handling live here.
Exit code 0 on success, non-zero on failure.
"""

import argparse
import logging
import sys
import time
from typing import Optional

from .config import (
    DEFAULT_LIMIT,
    DEFAULT_MONITOR_INTERVAL,
    MAX_CONSECUTIVE_FAILURES,
)
from .display import display_alert, display_coins
from .filters import apply_filters
from .logger_setup import setup_logging
from .models import Coin
from .scraper import scrape
from .storage import save_all
from .validators import validate_coins

logger = logging.getLogger(__name__)

# Reconfigure stdout/stderr to UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Alert helpers
# ---------------------------------------------------------------------------

def _parse_alert_arg(raw: str) -> tuple[str, float]:
    """
    Parse "SYM:PRICE" alert argument.

    Parameters
    ----------
    raw : str  e.g. "BTC:70000" or "ETH:2500.50"

    Returns
    -------
    (symbol, price) tuple

    Raises
    ------
    argparse.ArgumentTypeError on bad format.
    """
    try:
        sym, price_str = raw.split(":", 1)
        return sym.upper().strip(), float(price_str.strip())
    except (ValueError, AttributeError):
        raise argparse.ArgumentTypeError(
            f"Invalid alert format {raw!r}. Expected SYM:PRICE, e.g. BTC:70000"
        )


def _check_alerts(
    coins: list[Coin],
    alert_above: list[tuple[str, float]],
    alert_below: list[tuple[str, float]],
) -> None:
    """Check all alert thresholds and print ALERT lines when triggered."""
    sym_map = {c.symbol.upper(): c for c in coins}

    for sym, threshold in alert_above:
        coin = sym_map.get(sym)
        if coin and coin.price is not None and coin.price > threshold:
            display_alert(sym, coin.price, threshold, "above")
            logger.info("ALERT triggered: %s above %.4f (current %.4f)", sym, threshold, coin.price)

    for sym, threshold in alert_below:
        coin = sym_map.get(sym)
        if coin and coin.price is not None and coin.price < threshold:
            display_alert(sym, coin.price, threshold, "below")
            logger.info("ALERT triggered: %s below %.4f (current %.4f)", sym, threshold, coin.price)


# ---------------------------------------------------------------------------
# Single-cycle orchestration
# ---------------------------------------------------------------------------

def _run_cycle(args: argparse.Namespace) -> list[Coin]:
    """
    Execute one full scrape → validate → save → filter → display cycle.

    Parameters
    ----------
    args : argparse.Namespace  (parsed CLI arguments)

    Returns
    -------
    list[Coin]  – validated coins (pre-filter, full dataset)
    """
    logger.info("Scrape cycle starting (limit=%d, headless=%s)", args.limit, args.headless)

    # 1. Scrape
    coins_raw = scrape(
        limit=args.limit,
        headless=args.headless,
        watchlist=args.watch,
    )
    logger.info("Scraped %d coins.", len(coins_raw))

    # 2. Validate (raises RuntimeError if all invalid)
    coins_valid = validate_coins(coins_raw)
    logger.info("Valid coins after validation: %d", len(coins_valid))

    # 3. Save (full validated set, before any filters)
    if not args.no_save:
        save_all(coins_valid, output_path=getattr(args, "output", None))

    # 4. Apply filters (for display only)
    displayed = apply_filters(
        coins_valid,
        min_price=args.min_price,
        max_price=args.max_price,
        min_change=args.min_change,
        max_change=args.max_change,
        gainers=args.gainers,
        losers=args.losers,
        watchlist=args.watch,
        limit=args.limit,
    )

    # 5. Check alerts (against full validated set, not just displayed)
    _check_alerts(
        coins_valid,
        alert_above=args.alert_above or [],
        alert_below=args.alert_below or [],
    )

    # 6. Display
    ts = coins_valid[0].timestamp if coins_valid else None
    display_coins(displayed, timestamp=ts)

    # 7. Warn about watchlist symbols not found
    if args.watch:
        found_symbols = {c.symbol.upper() for c in coins_valid}
        for sym in args.watch:
            if sym.upper() not in found_symbols:
                print(f"  ⚠  Symbol '{sym.upper()}' was not found in the scraped data.")

    return coins_valid


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crypto-tracker",
        description=(
            "Cryptocurrency Price Tracker – scrapes live data from CoinMarketCap\n"
            "and displays, filters, and stores it as CSV."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
--------
  # Fetch top 10 coins (visible Chrome window):
  python run.py

  # Headless, top 20:
  python run.py --headless --limit 20

  # Only coins priced above $1000:
  python run.py --headless --min-price 1000

  # Today's gainers (coins with positive 24h change):
  python run.py --headless --gainers

  # Today's losers, top 5:
  python run.py --headless --losers --limit 5

  # Watch specific coins:
  python run.py --headless --watch BTC ETH SOL

  # Set price alerts:
  python run.py --headless --alert-above BTC:70000 --alert-below ETH:2000

  # Monitor mode, refresh every 30s:
  python run.py --headless --monitor --interval 30
        """,
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run Chrome in headless mode (no visible window).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        metavar="N",
        help=f"Number of top cryptocurrencies to fetch (1..100, default {DEFAULT_LIMIT}).",
    )
    parser.add_argument(
        "--min-price",
        type=float,
        default=None,
        metavar="X",
        dest="min_price",
        help="Display only coins with price >= X USD.",
    )
    parser.add_argument(
        "--max-price",
        type=float,
        default=None,
        metavar="X",
        dest="max_price",
        help="Display only coins with price <= X USD.",
    )
    parser.add_argument(
        "--min-change",
        type=float,
        default=None,
        metavar="X",
        dest="min_change",
        help="Display only coins with 24h change >= X%%.",
    )
    parser.add_argument(
        "--max-change",
        type=float,
        default=None,
        metavar="X",
        dest="max_change",
        help="Display only coins with 24h change <= X%%.",
    )
    parser.add_argument(
        "--gainers",
        action="store_true",
        default=False,
        help="Display only coins with a positive 24h change, sorted best-first.",
    )
    parser.add_argument(
        "--top-gainers",
        nargs="?",
        const=True,
        default=None,
        metavar="N",
        help="Display top N gainers (or all positive gainers if N is omitted).",
    )
    parser.add_argument(
        "--losers",
        action="store_true",
        default=False,
        help="Display only coins with a negative 24h change, sorted worst-first.",
    )
    parser.add_argument(
        "--top-losers",
        nargs="?",
        const=True,
        default=None,
        metavar="N",
        help="Display top N losers (or all negative losers if N is omitted).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        metavar="FILE",
        help="Custom CSV file output path (e.g. data/custom_export.csv).",
    )
    parser.add_argument(
        "--watch",
        nargs="+",
        metavar="SYM",
        default=None,
        help="Display only the listed ticker symbols (case-insensitive). E.g. --watch BTC ETH SOL",
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        default=False,
        help="Run in continuous monitor mode, re-scraping on each interval.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_MONITOR_INTERVAL,
        metavar="SECONDS",
        help=(
            f"Seconds between monitor cycles (min 10, default {DEFAULT_MONITOR_INTERVAL}). "
            "Only used with --monitor."
        ),
    )
    parser.add_argument(
        "--alert-above",
        nargs="+",
        type=_parse_alert_arg,
        default=None,
        metavar="SYM:PRICE",
        dest="alert_above",
        help="Print an ALERT when a coin's price exceeds PRICE. E.g. --alert-above BTC:70000",
    )
    parser.add_argument(
        "--alert-below",
        nargs="+",
        type=_parse_alert_arg,
        default=None,
        metavar="SYM:PRICE",
        dest="alert_below",
        help="Print an ALERT when a coin's price falls below PRICE. E.g. --alert-below ETH:2000",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        default=False,
        dest="no_save",
        help="Display results only; do not write any CSV files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable DEBUG logging to console and log file.",
    )
    return parser


def _validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Validate argument constraints not expressible in argparse alone."""
    # Process --top-gainers alias
    top_gainers = getattr(args, "top_gainers", None)
    if top_gainers is not None:
        args.gainers = True
        if isinstance(top_gainers, str) and top_gainers.isdigit():
            args.limit = int(top_gainers)
        elif isinstance(top_gainers, int):
            args.limit = top_gainers

    # Process --top-losers alias
    top_losers = getattr(args, "top_losers", None)
    if top_losers is not None:
        args.losers = True
        if isinstance(top_losers, str) and top_losers.isdigit():
            args.limit = int(top_losers)
        elif isinstance(top_losers, int):
            args.limit = top_losers

    if not (1 <= args.limit <= 100):
        parser.error(f"--limit must be between 1 and 100 (got {args.limit}).")
    if args.gainers and args.losers:
        parser.error("--gainers and --losers are mutually exclusive.")
    if args.monitor and args.interval < 10:
        parser.error(f"--interval must be at least 10 seconds (got {args.interval}).")


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> int:
    """
    CLI entry point.

    Returns
    -------
    int – exit code (0 = success, 1 = error).
    """
    parser = _build_parser()
    args = parser.parse_args()
    _validate_args(args, parser)

    setup_logging(verbose=args.verbose)
    logger.info("Crypto Price Tracker starting. args=%s", vars(args))

    if args.monitor:
        return _monitor_loop(args)
    else:
        return _single_run(args)


def _single_run(args: argparse.Namespace) -> int:
    """Execute a single scrape cycle."""
    try:
        _run_cycle(args)
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 1
    except RuntimeError as exc:
        # Friendly message; stack trace only in verbose mode
        print(f"\n  Error: {exc}", file=sys.stderr)
        logger.error("Runtime error: %s", exc, exc_info=args.verbose)
        return 1
    except Exception as exc:
        print(f"\n  Unexpected error: {exc}", file=sys.stderr)
        logger.error("Unexpected error: %s", exc, exc_info=True)
        return 1


def _monitor_loop(args: argparse.Namespace) -> int:
    """Run continuous monitor mode until Ctrl+C or 3 consecutive failures."""
    print(f"\n  Monitor mode active. Refreshing every {args.interval}s. (Ctrl+C to stop)\n")
    consecutive_failures = 0
    cycle = 0

    while True:
        cycle += 1
        logger.info("Monitor cycle %d starting.", cycle)
        print(f"\n─── Cycle {cycle} ───────────────────────────────────────────────")
        try:
            _run_cycle(args)
            consecutive_failures = 0  # reset on success
        except KeyboardInterrupt:
            print("\n\n  Monitoring stopped by user. Goodbye!")
            logger.info("Monitor stopped by KeyboardInterrupt.")
            return 0
        except Exception as exc:
            consecutive_failures += 1
            print(f"\n  [Cycle {cycle}] Error: {exc}", file=sys.stderr)
            logger.error(
                "Monitor cycle %d failed (%d consecutive): %s",
                cycle,
                consecutive_failures,
                exc,
                exc_info=args.verbose,
            )
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(
                    f"\n  Stopping: {consecutive_failures} consecutive failures. "
                    "See logs for details.",
                    file=sys.stderr,
                )
                logger.error(
                    "Monitor stopped after %d consecutive failures.", consecutive_failures
                )
                return 1

        try:
            print(f"\n  Next update in {args.interval}s… (Ctrl+C to stop)")
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n\n  Monitoring stopped by user. Goodbye!")
            logger.info("Monitor stopped by KeyboardInterrupt during sleep.")
            return 0
