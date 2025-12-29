# -*- coding: utf-8 -*-
"""
GitHub API Error Handling
Sprint OAUTH-6: Centralized error handling with rate limit parsing and retry info

Provides structured error classification for GitHub API responses.
No tokens are exposed in error details.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class GitHubApiError(Exception):
    """
    Structured GitHub API error with context for retry, rate limits, and user messaging.
    
    Attributes:
        code: Error classification (UNAUTHORIZED, FORBIDDEN, RATE_LIMITED, NETWORK, TIMEOUT, BAD_RESPONSE, UNKNOWN)
        status: HTTP status code (or None for network errors)
        message: User-friendly message (no tokens, no sensitive headers)
        retry_after_s: Seconds to wait before retry (from Retry-After header or rate limit reset)
        rate_limit_reset_utc: ISO 8601 timestamp when rate limit resets (from X-RateLimit-Reset)
        details: Redacted technical details safe for copy-to-clipboard
    """
    
    code: str  # UNAUTHORIZED, FORBIDDEN, RATE_LIMITED, NETWORK, TIMEOUT, BAD_RESPONSE, UNKNOWN
    message: str
    status: Optional[int] = None
    retry_after_s: Optional[int] = None
    rate_limit_reset_utc: Optional[str] = None
    details: str = ""
    
    def __str__(self) -> str:
        """Return user-friendly message."""
        return self.message
    
    @staticmethod
    def from_http_error(
        status: int,
        headers: Optional[dict] = None,
        body: Optional[str] = None,
    ) -> GitHubApiError:
        """
        Classify an HTTP error response and create a GitHubApiError.
        
        Args:
            status: HTTP status code
            headers: Response headers (never includes Authorization)
            body: Response body text (for additional context)
            
        Returns:
            GitHubApiError with code, message, and retry/rate limit info
        """
        headers = headers or {}
        body = body or ""
        
        # Normalize header keys to lowercase for case-insensitive lookup
        headers_lower = {k.lower(): v for k, v in headers.items()}
        
        # Parse rate limit headers
        rate_limit_remaining = headers_lower.get("x-ratelimit-remaining")
        rate_limit_reset = headers_lower.get("x-ratelimit-reset")
        retry_after = headers_lower.get("retry-after")
        
        retry_after_s: Optional[int] = None
        rate_limit_reset_utc: Optional[str] = None
        
        # Convert rate limit reset (Unix timestamp) to retry_after
        if rate_limit_reset:
            try:
                reset_ts = int(rate_limit_reset)
                import time
                now = int(time.time())
                retry_after_s = max(0, reset_ts - now)
                # Also provide ISO 8601 for user display
                from datetime import datetime, timezone
                rate_limit_reset_utc = datetime.fromtimestamp(
                    reset_ts, tz=timezone.utc
                ).isoformat()
            except (ValueError, Exception):
                pass
        
        # Retry-After (in seconds)
        if retry_after:
            try:
                retry_after_s = int(retry_after)
            except ValueError:
                pass
        
        # Classify by status
        if status == 401:
            return GitHubApiError(
                code="UNAUTHORIZED",
                status=status,
                message="Your GitHub session has expired. Click Reconnect to sign in again.",
                retry_after_s=None,
                rate_limit_reset_utc=None,
                details="HTTP 401: Authentication failed. Token may be revoked or expired.",
            )
        
        if status == 403:
            # Check if this is a rate limit
            if rate_limit_remaining and str(rate_limit_remaining) == "0":
                reset_msg = ""
                if rate_limit_reset_utc:
                    reset_msg = f" (resets at {rate_limit_reset_utc})"
                return GitHubApiError(
                    code="RATE_LIMITED",
                    status=status,
                    message=f"GitHub rate limit reached. Please try again in a few minutes.{reset_msg}",
                    retry_after_s=retry_after_s,
                    rate_limit_reset_utc=rate_limit_reset_utc,
                    details="HTTP 403: Rate limit exhausted. X-RateLimit-Remaining=0.",
                )
            else:
                return GitHubApiError(
                    code="FORBIDDEN",
                    status=status,
                    message="Access denied. Check your GitHub permissions and token scopes.",
                    retry_after_s=None,
                    rate_limit_reset_utc=None,
                    details="HTTP 403: Forbidden. Missing required scopes or insufficient permissions.",
                )
        
        if status == 422:
            # Validation error (e.g., invalid input)
            return GitHubApiError(
                code="BAD_RESPONSE",
                status=status,
                message="Invalid data sent to GitHub. Check your input and try again.",
                retry_after_s=None,
                rate_limit_reset_utc=None,
                details="HTTP 422: Unprocessable Entity. Request validation failed.",
            )
        
        if status == 400:
            return GitHubApiError(
                code="BAD_RESPONSE",
                status=status,
                message="Bad request. Check your input and try again.",
                retry_after_s=None,
                rate_limit_reset_utc=None,
                details="HTTP 400: Bad Request.",
            )
        
        if status in (502, 503, 504):
            return GitHubApiError(
                code="NETWORK",
                status=status,
                message="GitHub is temporarily unavailable. Retrying may help.",
                retry_after_s=retry_after_s or 5,
                rate_limit_reset_utc=None,
                details=f"HTTP {status}: GitHub server error. May be transient.",
            )
        
        if status >= 500:
            return GitHubApiError(
                code="NETWORK",
                status=status,
                message="GitHub is experiencing issues. Please try again.",
                retry_after_s=retry_after_s or 10,
                rate_limit_reset_utc=None,
                details=f"HTTP {status}: Server error.",
            )
        
        # Default
        return GitHubApiError(
            code="UNKNOWN",
            status=status,
            message=f"GitHub API error (status {status}). Please try again.",
            retry_after_s=None,
            rate_limit_reset_utc=None,
            details=f"HTTP {status}: Unexpected response.",
        )
    
    @staticmethod
    def from_network_error(error_msg: str) -> GitHubApiError:
        """
        Create a network-level error (timeout, DNS, SSL, etc.).
        
        Args:
            error_msg: Network error message (redacted of sensitive data)
            
        Returns:
            GitHubApiError with NETWORK or TIMEOUT code
        """
        # Classify by error message
        error_lower = error_msg.lower()
        
        if "timeout" in error_lower:
            return GitHubApiError(
                code="TIMEOUT",
                status=None,
                message="Request timed out. Check your network connection and try again.",
                retry_after_s=2,
                rate_limit_reset_utc=None,
                details=f"Network timeout: {error_msg}",
            )
        
        if "connection" in error_lower or "ssl" in error_lower or "dns" in error_lower:
            return GitHubApiError(
                code="NETWORK",
                status=None,
                message="Network error. Check your internet connection and try again.",
                retry_after_s=3,
                rate_limit_reset_utc=None,
                details=f"Connection error: {error_msg}",
            )
        
        return GitHubApiError(
            code="NETWORK",
            status=None,
            message="Network error. Please check your connection and try again.",
            retry_after_s=2,
            rate_limit_reset_utc=None,
            details=f"Network error: {error_msg}",
        )
    
    @staticmethod
    def from_json_error(error_msg: str) -> GitHubApiError:
        """
        Create an error for invalid JSON response or parsing failures.
        
        Args:
            error_msg: Parse error message
            
        Returns:
            GitHubApiError with BAD_RESPONSE code
        """
        return GitHubApiError(
            code="BAD_RESPONSE",
            status=None,
            message="GitHub returned unexpected data. Try again.",
            retry_after_s=None,
            rate_limit_reset_utc=None,
            details=f"JSON parse error: {error_msg}",
        )


# Legacy compatibility: GitHubApiNetworkError maps to network errors
class GitHubApiNetworkError(GitHubApiError):
    """Legacy alias for network-level errors. Use GitHubApiError with code='NETWORK' instead."""
    
    def __init__(self, msg: str):
        err = GitHubApiError.from_network_error(msg)
        super().__init__(
            code=err.code,
            message=err.message,
            status=err.status,
            retry_after_s=err.retry_after_s,
            rate_limit_reset_utc=err.rate_limit_reset_utc,
            details=err.details,
        )
