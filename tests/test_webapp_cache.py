"""
tests/test_webapp_cache.py - Unit tests for TTLCache service.
"""

import time
import pytest
from webapp.services.cache import TTLCache


def test_cache_set_and_get():
    cache = TTLCache()
    cache.set("key1", "value1", ttl=60)
    assert cache.get("key1") == "value1"


def test_cache_expiration():
    cache = TTLCache()
    cache.set("key_short", "temp_value", ttl=0.05)
    assert cache.get("key_short") == "temp_value"
    time.sleep(0.1)
    assert cache.get("key_short") is None


def test_cache_get_stale():
    cache = TTLCache()
    cache.set("stale_key", "old_value", ttl=0.05)
    time.sleep(0.1)
    # Standard get returns None
    assert cache.get("stale_key") is None

    # Stale get returns value and timestamp
    stale = cache.get_stale("stale_key")
    assert stale is not None
    val, created_at = stale
    assert val == "old_value"
    assert created_at > 0


def test_cache_clear_and_size():
    cache = TTLCache()
    cache.set("a", 1, ttl=60)
    cache.set("b", 2, ttl=60)
    assert cache.size() == 2
    cache.clear()
    assert cache.size() == 0
    assert cache.get("a") is None
