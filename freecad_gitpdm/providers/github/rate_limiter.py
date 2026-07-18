# -*- coding: utf-8 -*-
"""
Backward-compat re-export. The rate limiter moved to
`providers/shared/rate_limiter.py` (Phase: multi-provider support) since it
never contained any GitHub-specific logic (it deals only in abstract
"tokens" and an opaque `user_id` string). Kept here under the original
names so existing imports of `freecad_gitpdm.providers.github.rate_limiter`
keep working unchanged.
"""

from __future__ import annotations

from freecad_gitpdm.providers.shared.rate_limiter import (
    CircuitBreaker,
    CircuitState,
    RateLimitBucket,
    RateLimiter,
)

__all__ = ["CircuitBreaker", "CircuitState", "RateLimitBucket", "RateLimiter"]
