# -*- coding: utf-8 -*-
"""
GitHub API Response Caching
Sprint OAUTH-6: Simple in-memory cache for API responses with TTL

Provides a lightweight caching layer for expensive API calls
(e.g., repo listing). Cache is keyed by host, username, and endpoint
to ensure correctness across multiple GitHub accounts/hosts.

No persistence to disk; cache is lost on process restart.
Thread-safe via basic locking.
"""

from __future__ import annotations

import time
import threading
from typing import Optional, Any, Dict, List, Tuple


class CacheEntry:
    """A single cached response with TTL tracking."""
    
    def __init__(self, data: Any, ttl_seconds: int = 120):
        """
        Initialize cache entry.
        
        Args:
            data: The data to cache (typically list of RepoInfo)
            ttl_seconds: Time-to-live in seconds (default 120)
        """
        self.data = data
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return (time.time() - self.created_at) > self.ttl_seconds
    
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds."""
        return time.time() - self.created_at


class GitHubApiCache:
    """
    In-memory cache for GitHub API responses.
    
    Cache key format: f"{host}:{username}:{endpoint}:{query_hash}"
    
    Example:
        cache = GitHubApiCache(ttl_seconds=120)
        
        # Store repos
        cache.set("api.github.com", "alice", "repos_list", repos_list)
        
        # Retrieve repos
        repos, hit = cache.get("api.github.com", "alice", "repos_list")
        if hit and repos:
            print(f"Cache hit! {len(repos)} repos (age {cache.age('api.github.com', 'alice', 'repos_list')}s)")
        else:
            print("Cache miss or expired, need to fetch")
        
        # Bypass cache
        cache.set_bypass(True)
        repos, hit = cache.get(...)  # hit will be False
        cache.set_bypass(False)
    """
    
    def __init__(self, ttl_seconds: int = 120):
        """
        Initialize cache.
        
        Args:
            ttl_seconds: Default time-to-live for cache entries
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._bypass = False
        self._stats = {"hits": 0, "misses": 0}
    
    def _make_key(self, host: str, username: str, endpoint: str, query_params: str = "") -> str:
        """Generate a cache key from request components."""
        # Normalize inputs
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
        """
        Retrieve cached data if valid.
        
        Args:
            host: GitHub host (e.g., "api.github.com")
            username: GitHub username (for key isolation)
            endpoint: API endpoint name (e.g., "repos_list")
            query_params: Optional query string for more specific caching
            
        Returns:
            (data, hit): data is cached value or None; hit is True if valid cache
        """
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
                # Optionally delete expired entry (or let it linger)
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
        """
        Store data in cache.
        
        Args:
            host: GitHub host
            username: GitHub username
            endpoint: API endpoint name
            data: Data to cache
            query_params: Optional query string for specificity
            ttl_seconds: Optional override of default TTL
        """
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
        """
        Invalidate cache entries matching the criteria.
        
        If all parameters are empty, clears entire cache.
        Otherwise, removes entries matching the provided filters.
        
        Args:
            host: GitHub host to invalidate (optional)
            username: GitHub username to invalidate (optional)
            endpoint: API endpoint to invalidate (optional)
        """
        if not host and not username and not endpoint:
            # Clear all
            with self._lock:
                self._cache.clear()
            return
        
        # Partial invalidation
        host_lower = (host or "").lower()
        username_lower = (username or "").lower()
        endpoint_lower = (endpoint or "").lower()
        
        with self._lock:
            keys_to_remove = []
            for key in self._cache:
                parts = key.split(":", 3)  # host:username:endpoint:query
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
        """
        Get age of cached entry in seconds, or None if not cached.
        
        Returns:
            Age in seconds, or None if entry doesn't exist or is expired
        """
        key = self._make_key(host, username, endpoint, query_params)
        
        with self._lock:
            entry = self._cache.get(key)
            if entry is None or entry.is_expired():
                return None
            return entry.age_seconds()
    
    def set_bypass(self, bypass: bool) -> None:
        """
        Temporarily bypass cache (for "Refresh" buttons).
        
        Args:
            bypass: True to bypass; False to use cache normally
        """
        with self._lock:
            self._bypass = bypass
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics (hits and misses)."""
        with self._lock:
            return dict(self._stats)
    
    def clear_stats(self) -> None:
        """Reset cache statistics."""
        with self._lock:
            self._stats = {"hits": 0, "misses": 0}


# Global singleton cache instance
_global_cache: Optional[GitHubApiCache] = None
_cache_lock = threading.Lock()


def get_github_api_cache() -> GitHubApiCache:
    """Get or create the global GitHub API cache singleton."""
    global _global_cache
    if _global_cache is None:
        with _cache_lock:
            if _global_cache is None:
                _global_cache = GitHubApiCache(ttl_seconds=120)
    return _global_cache


def invalidate_github_cache(
    host: str = "",
    username: str = "",
    endpoint: str = "",
) -> None:
    """Invalidate GitHub cache entries matching criteria."""
    cache = get_github_api_cache()
    cache.invalidate(host, username, endpoint)
