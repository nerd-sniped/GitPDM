# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
Bitbucket Cloud API error classification.

Verified live against api.bitbucket.org/2.0: a bogus Bearer token returns
`{"type": "error", "error": {"message": "Token is invalid, expired, or not
supported for this endpoint."}}` with a `Www-Authenticate: OAuth realm=...`
header - confirming Bearer/API-token auth is real and recognized. No
rate-limit headers were observed on error responses during this
verification pass (Bitbucket's rate-limit headers, if any, may only appear
on authenticated calls - a real-token acceptance pass should confirm this
before trusting any header-based rate-limit parsing; this class falls back
to the generic 429-status signal only).
"""

from __future__ import annotations

from typing import Optional

from freecad_gitpdm.providers.shared.errors import ProviderApiError


class BitbucketApiError(ProviderApiError):
    @staticmethod
    def from_http_error(
        status: int,
        headers: Optional[dict] = None,
        body: Optional[str] = None,
    ) -> "BitbucketApiError":
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
            return BitbucketApiError(
                code="UNAUTHORIZED",
                status=status,
                message="Your Bitbucket token is invalid or has expired. "
                "Reconnect and try again.",
                details="HTTP 401: Authentication failed.",
            )
        if status == 403:
            return BitbucketApiError(
                code="FORBIDDEN",
                status=status,
                message="Access denied. Check your token's scopes and "
                "workspace permissions.",
                details="HTTP 403: Forbidden.",
            )
        if status == 404:
            return BitbucketApiError(
                code="BAD_RESPONSE",
                status=status,
                message="Not found. Check the workspace and repository name.",
                details="HTTP 404: Not Found.",
            )
        if status == 429:
            return BitbucketApiError(
                code="RATE_LIMITED",
                status=status,
                message="Rate limit reached. Please try again in a few minutes.",
                retry_after_s=retry_after_s,
                details="HTTP 429: Too Many Requests.",
            )
        if status in (400, 422):
            return BitbucketApiError(
                code="BAD_RESPONSE",
                status=status,
                message="Invalid data sent to Bitbucket. Check your input and try again.",
                details=f"HTTP {status}: Validation failed.",
            )
        if status in (502, 503, 504):
            return BitbucketApiError(
                code="NETWORK",
                status=status,
                message="Bitbucket is temporarily unavailable. Retrying may help.",
                retry_after_s=retry_after_s or 5,
                details=f"HTTP {status}: Server error. May be transient.",
            )
        if status >= 500:
            return BitbucketApiError(
                code="NETWORK",
                status=status,
                message="Bitbucket is experiencing issues. Please try again.",
                retry_after_s=retry_after_s or 10,
                details=f"HTTP {status}: Server error.",
            )
        return BitbucketApiError(
            code="UNKNOWN",
            status=status,
            message=f"Bitbucket API error (status {status}). Please try again.",
            details=f"HTTP {status}: Unexpected response.",
        )
