# -*- coding: utf-8 -*-
"""
Shared provider API error shape.

Extracted from `providers/github/errors.py`'s `GitHubApiError` (which is
left untouched — it stays a separate, self-contained class rather than
being made to inherit from this one, to avoid any risk to the one
fully-verified provider's working code). New providers (GitLab, Bitbucket,
Gitea/Forgejo, SourceHut) define their own `<Host>ApiError(ProviderApiError)`
subclass with a host-specific `from_http_error()` (status codes and rate
limit header names differ per host), while `from_network_error()` and
`from_json_error()` are generic enough to inherit unmodified.

Code that needs to catch "any provider's API error" (e.g. the New Repo
wizard's session-expiry handling) should catch `(ProviderApiError,
GitHubApiError)` as a tuple rather than relying on inheritance, since
GitHubApiError intentionally isn't part of this hierarchy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderApiError(Exception):
    """
    Structured provider API error with context for retry, rate limits, and
    user messaging. Same shape as `providers.github.errors.GitHubApiError`
    by design, generalized to any host.
    """

    code: str  # UNAUTHORIZED, FORBIDDEN, RATE_LIMITED, NETWORK, TIMEOUT, BAD_RESPONSE, UNKNOWN
    message: str
    status: Optional[int] = None
    retry_after_s: Optional[int] = None
    rate_limit_reset_utc: Optional[str] = None
    details: str = ""

    def __str__(self) -> str:
        return self.message

    @staticmethod
    def from_http_error(
        status: int,
        headers: Optional[dict] = None,
        body: Optional[str] = None,
    ) -> "ProviderApiError":
        """
        Generic status-code classification, used as-is by providers with no
        special-cased status handling, or as the fallback tail of a
        subclass's own override. Doesn't know any host-specific rate-limit
        header names (subclasses should override for that).
        """
        headers = headers or {}
        headers_lower = {k.lower(): v for k, v in headers.items()}
        retry_after = headers_lower.get("retry-after")

        retry_after_s: Optional[int] = None
        if retry_after:
            try:
                retry_after_s = int(retry_after)
            except ValueError:
                pass

        if status == 401:
            return ProviderApiError(
                code="UNAUTHORIZED",
                status=status,
                message="Your session has expired or the token is invalid. "
                "Reconnect and try again.",
                details="HTTP 401: Authentication failed.",
            )
        if status == 403:
            return ProviderApiError(
                code="FORBIDDEN",
                status=status,
                message="Access denied. Check your token's permissions/scopes.",
                details="HTTP 403: Forbidden.",
            )
        if status == 429:
            return ProviderApiError(
                code="RATE_LIMITED",
                status=status,
                message="Rate limit reached. Please try again in a few minutes.",
                retry_after_s=retry_after_s,
                details="HTTP 429: Too Many Requests.",
            )
        if status == 422:
            return ProviderApiError(
                code="BAD_RESPONSE",
                status=status,
                message="Invalid data sent to the server. Check your input and try again.",
                details="HTTP 422: Unprocessable Entity.",
            )
        if status == 400:
            return ProviderApiError(
                code="BAD_RESPONSE",
                status=status,
                message="Bad request. Check your input and try again.",
                details="HTTP 400: Bad Request.",
            )
        if status in (502, 503, 504):
            return ProviderApiError(
                code="NETWORK",
                status=status,
                message="The server is temporarily unavailable. Retrying may help.",
                retry_after_s=retry_after_s or 5,
                details=f"HTTP {status}: Server error. May be transient.",
            )
        if status >= 500:
            return ProviderApiError(
                code="NETWORK",
                status=status,
                message="The server is experiencing issues. Please try again.",
                retry_after_s=retry_after_s or 10,
                details=f"HTTP {status}: Server error.",
            )
        return ProviderApiError(
            code="UNKNOWN",
            status=status,
            message=f"API error (status {status}). Please try again.",
            details=f"HTTP {status}: Unexpected response.",
        )

    @staticmethod
    def from_network_error(error_msg: str) -> "ProviderApiError":
        """Classify a network-level failure (timeout, DNS, SSL, etc.)."""
        error_lower = error_msg.lower()

        if "timeout" in error_lower:
            return ProviderApiError(
                code="TIMEOUT",
                message="Request timed out. Check your network connection and try again.",
                retry_after_s=2,
                details=f"Network timeout: {error_msg}",
            )
        if "connection" in error_lower or "ssl" in error_lower or "dns" in error_lower:
            return ProviderApiError(
                code="NETWORK",
                message="Network error. Check your internet connection and try again.",
                retry_after_s=3,
                details=f"Connection error: {error_msg}",
            )
        return ProviderApiError(
            code="NETWORK",
            message="Network error. Please check your connection and try again.",
            retry_after_s=2,
            details=f"Network error: {error_msg}",
        )

    @staticmethod
    def from_json_error(error_msg: str) -> "ProviderApiError":
        return ProviderApiError(
            code="BAD_RESPONSE",
            message="The server returned unexpected data. Try again.",
            details=f"JSON parse error: {error_msg}",
        )


class ProviderApiNetworkError(ProviderApiError):
    """Raised for transport-level failures (no HTTP response at all)."""

    def __init__(self, msg: str):
        err = ProviderApiError.from_network_error(msg)
        super().__init__(
            code=err.code,
            message=err.message,
            status=err.status,
            retry_after_s=err.retry_after_s,
            rate_limit_reset_utc=err.rate_limit_reset_utc,
            details=err.details,
        )
