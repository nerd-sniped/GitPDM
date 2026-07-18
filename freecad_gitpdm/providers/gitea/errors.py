# -*- coding: utf-8 -*-
"""
Gitea/Forgejo API error classification.

Verified live against Codeberg (codeberg.org — a public Forgejo instance,
used as a stand-in for "a Gitea/Forgejo server" since this provider is
inherently self-hosted with no single fixed host to test against): error
bodies are `{"message": "...", "url": "https://<host>/api/swagger"}` — a
single string message, not GitHub's nested `errors` array. Rate-limit
headers use the RFC-draft structured format (`ratelimit`, `ratelimit-policy`
— e.g. `"baseline";r=1999;t=600`), different enough from GitHub's/GitLab's
that this class doesn't attempt to parse the exact remaining-request count
out of it; a bare 429 status is treated as the rate-limit signal instead,
which is the standard, host-agnostic HTTP convention.
"""

from __future__ import annotations

from typing import Optional

from freecad_gitpdm.providers.shared.errors import ProviderApiError


class GiteaApiError(ProviderApiError):
    @staticmethod
    def from_http_error(
        status: int,
        headers: Optional[dict] = None,
        body: Optional[str] = None,
    ) -> "GiteaApiError":
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
            return GiteaApiError(
                code="UNAUTHORIZED",
                status=status,
                message="Your Gitea/Forgejo token is invalid or has expired. "
                "Reconnect and try again.",
                details="HTTP 401: Authentication failed.",
            )
        if status == 403:
            return GiteaApiError(
                code="FORBIDDEN",
                status=status,
                message="Access denied. Check your token's permissions.",
                details="HTTP 403: Forbidden.",
            )
        if status == 404:
            return GiteaApiError(
                code="BAD_RESPONSE",
                status=status,
                message="Not found. Check the server URL and repository name.",
                details="HTTP 404: Not Found.",
            )
        if status == 429:
            return GiteaApiError(
                code="RATE_LIMITED",
                status=status,
                message="Rate limit reached. Please try again in a few minutes.",
                retry_after_s=retry_after_s,
                details="HTTP 429: Too Many Requests.",
            )
        if status in (400, 422):
            return GiteaApiError(
                code="BAD_RESPONSE",
                status=status,
                message="Invalid data sent to the server. Check your input and try again.",
                details=f"HTTP {status}: Validation failed.",
            )
        if status in (502, 503, 504):
            return GiteaApiError(
                code="NETWORK",
                status=status,
                message="The server is temporarily unavailable. Retrying may help.",
                retry_after_s=retry_after_s or 5,
                details=f"HTTP {status}: Server error. May be transient.",
            )
        if status >= 500:
            return GiteaApiError(
                code="NETWORK",
                status=status,
                message="The server is experiencing issues. Please try again.",
                retry_after_s=retry_after_s or 10,
                details=f"HTTP {status}: Server error.",
            )
        return GiteaApiError(
            code="UNKNOWN",
            status=status,
            message=f"API error (status {status}). Please try again.",
            details=f"HTTP {status}: Unexpected response.",
        )
