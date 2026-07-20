# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
GitLab API error classification.

Header/status conventions verified live against gitlab.com/api/v4 (no
token needed): 401 body is `{"message": "401 Unauthorized"}`; rate-limit
headers are unprefixed (`ratelimit-limit`, `ratelimit-remaining`,
`ratelimit-reset`), unlike GitHub's `X-RateLimit-*`. GitLab returns 429
for rate-limit-exceeded (GitHub uses 403 for its primary limit); this
class checks both 429 and a zeroed `ratelimit-remaining` on other statuses.
"""

from __future__ import annotations

from typing import Optional

from freecad_gitpdm.providers.shared.errors import ProviderApiError


class GitLabApiError(ProviderApiError):
    @staticmethod
    def from_http_error(
        status: int,
        headers: Optional[dict] = None,
        body: Optional[str] = None,
    ) -> "GitLabApiError":
        headers = headers or {}
        headers_lower = {k.lower(): v for k, v in headers.items()}

        rate_limit_remaining = headers_lower.get("ratelimit-remaining")
        rate_limit_reset = headers_lower.get("ratelimit-reset")
        retry_after = headers_lower.get("retry-after")

        retry_after_s: Optional[int] = None
        rate_limit_reset_utc: Optional[str] = None

        if rate_limit_reset:
            try:
                reset_ts = int(rate_limit_reset)
                import time
                from datetime import datetime, timezone

                now = int(time.time())
                retry_after_s = max(0, reset_ts - now)
                rate_limit_reset_utc = datetime.fromtimestamp(
                    reset_ts, tz=timezone.utc
                ).isoformat()
            except (ValueError, OSError):
                pass

        if retry_after:
            try:
                retry_after_s = int(retry_after)
            except ValueError:
                pass

        if status == 401:
            return GitLabApiError(
                code="UNAUTHORIZED",
                status=status,
                message="Your GitLab token is invalid or has expired. "
                "Reconnect and try again.",
                details="HTTP 401: Authentication failed.",
            )

        is_rate_limited = status == 429 or (
            rate_limit_remaining is not None and str(rate_limit_remaining) == "0"
        )
        if is_rate_limited:
            reset_msg = (
                f" (resets at {rate_limit_reset_utc})" if rate_limit_reset_utc else ""
            )
            return GitLabApiError(
                code="RATE_LIMITED",
                status=status,
                message=f"GitLab rate limit reached. Please try again in a few minutes.{reset_msg}",
                retry_after_s=retry_after_s,
                rate_limit_reset_utc=rate_limit_reset_utc,
                details=f"HTTP {status}: Rate limit exceeded.",
            )

        if status == 403:
            return GitLabApiError(
                code="FORBIDDEN",
                status=status,
                message="Access denied. Check your token's scopes and project permissions.",
                details="HTTP 403: Forbidden.",
            )

        if status in (400, 422):
            return GitLabApiError(
                code="BAD_RESPONSE",
                status=status,
                message="Invalid data sent to GitLab. Check your input and try again.",
                details=f"HTTP {status}: Validation failed.",
            )

        if status in (502, 503, 504):
            return GitLabApiError(
                code="NETWORK",
                status=status,
                message="GitLab is temporarily unavailable. Retrying may help.",
                retry_after_s=retry_after_s or 5,
                details=f"HTTP {status}: GitLab server error. May be transient.",
            )

        if status >= 500:
            return GitLabApiError(
                code="NETWORK",
                status=status,
                message="GitLab is experiencing issues. Please try again.",
                retry_after_s=retry_after_s or 10,
                details=f"HTTP {status}: Server error.",
            )

        return GitLabApiError(
            code="UNKNOWN",
            status=status,
            message=f"GitLab API error (status {status}). Please try again.",
            details=f"HTTP {status}: Unexpected response.",
        )
