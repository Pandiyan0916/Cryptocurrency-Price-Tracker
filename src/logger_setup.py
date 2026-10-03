"""
logger_setup.py – Configure file + console logging for the tracker.

Log file:  logs/tracker_YYYYMMDD.log
Console:   WARNING and above (unless --verbose → DEBUG)
File:      INFO and above

Usage
-----
    from src.logger_setup import setup_logging
    setup_logging(verbose=False)
"""

import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path

from .config import LOGS_DIR, TIMESTAMP_FORMAT


def setup_logging(verbose: bool = False) -> None:
    """
    Configure the root logger.

    Parameters
    ----------
    verbose : bool
        If True, set DEBUG level for both console and file handlers.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_date = datetime.now(timezone.utc).strftime("%Y%m%d")
    log_file = LOGS_DIR / f"tracker_{log_date}.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # capture everything at root; handlers filter

    # Remove any pre-existing handlers (important in monitor mode re-runs)
    root.handlers.clear()

    # --- File handler (INFO+, or DEBUG if verbose) ---
    file_level = logging.DEBUG if verbose else logging.INFO
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s – %(message)s",
            datefmt=TIMESTAMP_FORMAT,
        )
    )
    root.addHandler(file_handler)

    # --- Console handler (WARNING+, or DEBUG if verbose) ---
    console_level = logging.DEBUG if verbose else logging.WARNING
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(
        logging.Formatter(fmt="[%(levelname)s] %(message)s")
    )
    root.addHandler(console_handler)

    # Suppress third-party loggers even under --verbose
    for noisy_logger in ["selenium", "urllib3", "webdriver_manager", "WDM"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging initialised. File: %s | verbose=%s", log_file, verbose
    )
