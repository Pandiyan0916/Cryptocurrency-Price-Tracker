"""
webapp/services/cache.py - Thread-safe in-memory TTL cache with stale-serve support.
"""

import time
import threading
from typing import Any, Optional, Tuple


class TTLCache:
    """In-memory key-value store with time-to-live expiration and stale data retrieval."""

    def __init__(self) -> None:
        self._store: dict[str, Tuple[Any, float, float]] = {}  # key -> (value, expire_at, created_at)
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get value if key exists and has not expired."""
        with self._lock:
            if key not in self._store:
                return None
            val, expire_at, _ = self._store[key]
            if time.time() > expire_at:
                return None
            return val

    def get_stale(self, key: str) -> Optional[Tuple[Any, float]]:
        """Get (value, created_at) even if expired (used for fallback when upstream fails)."""
        with self._lock:
            if key not in self._store:
                return None
            val, _, created_at = self._store[key]
            return val, created_at

    def set(self, key: str, value: Any, ttl: float) -> None:
        """Store value with ttl in seconds."""
        now = time.time()
        with self._lock:
            self._store[key] = (value, now + ttl, now)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        """Return number of cached entries."""
        with self._lock:
            return len(self._store)


# Global singleton cache instance for the web app
cache = TTLCache()
