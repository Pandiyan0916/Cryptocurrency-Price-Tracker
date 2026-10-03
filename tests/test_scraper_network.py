"""
tests/test_scraper_network.py
-------------------------------
Unit test for network pre-check failure handling without monkeypatching internal methods.
Points the socket pre-check to a closed local port (127.0.0.1:59999) using config/environment
overrides, asserting that a friendly RuntimeError is raised quickly.
"""

import pytest
import src.config
from src.scraper import _check_network_connectivity, scrape


def test_network_precheck_failure_on_closed_port(monkeypatch):
    """
    Test that pointing socket pre-check to a closed local port raises a friendly RuntimeError quickly.
    Uses monkeypatching of config values (or environment variables), not mocking/monkeypatching internal code.
    """
    monkeypatch.setattr(src.config, "CHECK_HOST", "127.0.0.1")
    monkeypatch.setattr(src.config, "CHECK_PORT", 59999)

    with pytest.raises(RuntimeError) as exc_info:
        _check_network_connectivity(timeout=0.5)

    err_msg = str(exc_info.value)
    assert "Network connection to 127.0.0.1:59999 failed" in err_msg
    assert "Please check your internet connection or firewall/DNS settings" in err_msg


def test_scrape_aborts_immediately_on_network_failure(monkeypatch, tmp_path):
    """
    Test that scrape() fails fast on pre-check failure without starting Chrome or modifying output files.
    """
    monkeypatch.setattr(src.config, "CHECK_HOST", "127.0.0.1")
    monkeypatch.setattr(src.config, "CHECK_PORT", 59999)

    with pytest.raises(RuntimeError) as exc_info:
        scrape(limit=10, headless=True)

    assert "Network connection to 127.0.0.1:59999 failed" in str(exc_info.value)
