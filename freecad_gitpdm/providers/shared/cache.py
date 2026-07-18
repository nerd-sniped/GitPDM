# -*- coding: utf-8 -*-
"""
Generic in-memory TTL cache for provider API responses.

Relocated verbatim (only the class/function names changed) from
`providers/github/cache.py`'s `GitHubApiCache` — that class never actually
contained any GitHub-specific logic; it was already a pure host-keyed
cache (`host` is part of the cache key precisely so different hosts don't
collide). `providers/github/cache.py` now re-exports from here under its
original names so nothing that imports the old path breaks.

No persistence to disk; cache is lost on process restart. Thread-safe via
basic locking.
"""

from __future__ import annotations

import time
import threading
from typing import Optional, Any, Dict, Tuple


class CacheEntry:
    """A single cached response with TTL tracking."""

    def __init__(self, data: Any, ttl_seconds: int = 120):
        self.data = data
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds

    def age_seconds(self) -> float:
        return time.time() - self.created_at


class ApiCache:
    """
    In-memory cache for provider API responses.

    Cache key format: f"{host}:{username}:{endpoint}[:{query_params}]" —
    `host` already disambiguates GitHub vs. GitLab vs. a self-hosted Gitea
    instance sharing one process-wide cache instance.
    """

    def __init__(self, ttl_seconds: int = 120):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._bypass = False
        self._stats = {"hits": 0, "misses": 0}

    def _make_key(
        self, host: str, username: str, endpoint: str, query_params: str = ""
    ) -> str:
        host = (host or "").lower().strip()
        username = (username or "").lower().strip()
        endpoint = (endpoint or "").lower().strip()
        query_params = (query_params or "").lower().strip()

        key = f"{host}:{username}:{endpoint}"
        if query_params:
            key = f"{key}:{query_params}"
        return key

    def get(
        self,
        host: str,
        username: str,
        endpoint: str,
        query_params: str = "",
    ) -> Tuple[Optional[Any], bool]:
        if self._bypass:
            self._stats["misses"] += 1
            return None, False

        key = self._make_key(host, username, endpoint, query_params)

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return None, False

            if entry.is_expired():
                del self._cache[key]
                self._stats["misses"] += 1
                return None, False

            self._stats["hits"] += 1
            return entry.data, True

    def set(
        self,
        host: str,
        username: str,
        endpoint: str,
        data: Any,
        query_params: str = "",
        ttl_seconds: Optional[int] = None,
    ) -> None:
        key = self._make_key(host, username, endpoint, query_params)
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds

        with self._lock:
            self._cache[key] = CacheEntry(data, ttl_seconds=ttl)

    def invalidate(
        self,
        host: str = "",
        username: str = "",
        endpoint: str = "",
    ) -> None:
        if not host and not username and not endpoint:
            with self._lock:
                self._cache.clear()
            return

        host_lower = (host or "").lower()
        username_lower = (username or "").lower()
        endpoint_lower = (endpoint or "").lower()

        with self._lock:
            keys_to_remove = []
            for key in self._cache:
                parts = key.split(":", 3)
                if len(parts) >= 1 and host_lower and parts[0] != host_lower:
                    continue
                if len(parts) >= 2 and username_lower and parts[1] != username_lower:
                    continue
                if len(parts) >= 3 and endpoint_lower and parts[2] != endpoint_lower:
                    continue
                keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._cache[key]

    def age(
        self,
        host: str,
        username: str,
        endpoint: str,
        query_params: str = "",
    ) -> Optional[float]:
        key = self._make_key(host, username, endpoint, query_params)

        with self._lock:
            entry = self._cache.get(key)
            if entry is None or entry.is_expired():
                return None
            return entry.age_seconds()

    def set_bypass(self, bypass: bool) -> None:
        """Temporarily bypass cache (for "Refresh" buttons)."""
        with self._lock:
            self._bypass = bypass

    def get_stats(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._stats)

    def clear_stats(self) -> None:
        with self._lock:
            self._stats = {"hits": 0, "misses": 0}


# Global singleton cache instance, shared across all providers (host is
# already part of every key, so GitHub/GitLab/Bitbucket/etc. entries never
# collide within it).
_global_cache: Optional[ApiCache] = None
_cache_lock = threading.Lock()


def get_api_cache() -> ApiCache:
    """Get or create the global provider API cache singleton."""
    global _global_cache
    if _global_cache is None:
        with _cache_lock:
            if _global_cache is None:
                _global_cache = ApiCache(ttl_seconds=120)
    return _global_cache


def invalidate_api_cache(
    host: str = "",
    username: str = "",
    endpoint: str = "",
) -> None:
    cache = get_api_cache()
    cache.invalidate(host, username, endpoint)
