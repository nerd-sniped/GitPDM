# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
Backward-compat re-export. The cache implementation moved to
`providers/shared/cache.py` (Phase: multi-provider support) since it never
contained any GitHub-specific logic — `host` was already part of every
cache key. Kept here under the original names so existing imports of
`freecad_gitpdm.providers.github.cache` keep working unchanged.
"""

from __future__ import annotations

from freecad_gitpdm.providers.shared.cache import (
    ApiCache as GitHubApiCache,
    CacheEntry,
    get_api_cache as get_github_api_cache,
    invalidate_api_cache as invalidate_github_cache,
)

__all__ = [
    "GitHubApiCache",
    "CacheEntry",
    "get_github_api_cache",
    "invalidate_github_cache",
]
