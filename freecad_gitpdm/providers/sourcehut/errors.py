# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
SourceHut GraphQL error classification.

Verified live: SourceHut mirrors auth errors to real HTTP status codes
(401 with `Www-Authenticate: Bearer`, body
`{"errors": [{"message": "...", "extensions": {"code": "ERR_UNAUTHORIZED"}}]}`)
rather than always returning 200 with an `errors` array the way many
GraphQL APIs do. Query/mutation-execution-time errors (e.g. a duplicate
repo name) are NOT verified live — GraphQL convention is a 200 response
with a top-level `errors` array in that case, which `graphql_errors_to_error()`
below handles defensively regardless of HTTP status, so this should degrade
correctly either way.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from freecad_gitpdm.providers.shared.errors import ProviderApiError


class SourceHutApiError(ProviderApiError):
    @staticmethod
    def from_http_error(
        status: int,
        headers: Optional[dict] = None,
        body: Optional[str] = None,
    ) -> "SourceHutApiError":
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
            return SourceHutApiError(
                code="UNAUTHORIZED",
                status=status,
                message="Your SourceHut token is invalid or has expired. "
                "Reconnect and try again.",
                details="HTTP 401: Authentication failed.",
            )
        if status == 403:
            return SourceHutApiError(
                code="FORBIDDEN",
                status=status,
                message="Access denied. Check your token's scopes.",
                details="HTTP 403: Forbidden.",
            )
        if status == 429:
            return SourceHutApiError(
                code="RATE_LIMITED",
                status=status,
                message="Rate limit reached. Please try again in a few minutes.",
                retry_after_s=retry_after_s,
                details="HTTP 429: Too Many Requests.",
            )
        if status in (502, 503, 504):
            return SourceHutApiError(
                code="NETWORK",
                status=status,
                message="SourceHut is temporarily unavailable. Retrying may help.",
                retry_after_s=retry_after_s or 5,
                details=f"HTTP {status}: Server error. May be transient.",
            )
        if status >= 500:
            return SourceHutApiError(
                code="NETWORK",
                status=status,
                message="SourceHut is experiencing issues. Please try again.",
                retry_after_s=retry_after_s or 10,
                details=f"HTTP {status}: Server error.",
            )
        return SourceHutApiError(
            code="UNKNOWN",
            status=status,
            message=f"SourceHut API error (status {status}). Please try again.",
            details=f"HTTP {status}: Unexpected response.",
        )

    @staticmethod
    def from_graphql_errors(errors: List[Dict[str, Any]]) -> "SourceHutApiError":
        """
        Build an error from a GraphQL `errors` array present in an
        otherwise-200 response (query/mutation-execution-time failure,
        e.g. a duplicate repo name) — distinct from transport-level HTTP
        errors, which from_http_error() above handles.
        """
        first = errors[0] if errors else {}
        message = (
            first.get("message") if isinstance(first, dict) else None
        ) or "SourceHut returned an error."
        extensions = first.get("extensions") if isinstance(first, dict) else None
        code = (
            (extensions or {}).get("code") if isinstance(extensions, dict) else None
        ) or "UNKNOWN"
        return SourceHutApiError(
            code=str(code),
            message=message,
            details=str(errors),
        )
