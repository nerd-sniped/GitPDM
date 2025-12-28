# -*- coding: utf-8 -*-
"""
GitHub Identity Fetcher
Sprint OAUTH-2: Verify current viewer identity via REST API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from freecad_gitpdm.github.api_client import (
    GitHubApiClient,
    GitHubApiNetworkError,
)


@dataclass
class IdentityResult:
    ok: bool
    login: Optional[str]
    user_id: Optional[int]
    avatar_url: Optional[str]
    error_code: Optional[str]
    message: str
    raw_status: int


def fetch_viewer_identity(client: GitHubApiClient) -> IdentityResult:
    """
    Fetch the authenticated user's identity using GET /user.

    Classifies common errors and returns a friendly message.
    """
    try:
        status, js, headers = client.request_json(
            "GET", "/user", headers=None, body=None, timeout_s=10
        )
    except GitHubApiNetworkError as e:
        return IdentityResult(
            ok=False,
            login=None,
            user_id=None,
            avatar_url=None,
            error_code="NETWORK_ERROR",
            message="Network error. Check connection and try again.",
            raw_status=0,
        )
    except Exception as e:
        return IdentityResult(
            ok=False,
            login=None,
            user_id=None,
            avatar_url=None,
            error_code="UNKNOWN",
            message="An unexpected error occurred.",
            raw_status=0,
        )

    # Classify status codes
    if status == 401:
        return IdentityResult(
            ok=False,
            login=None,
            user_id=None,
            avatar_url=None,
            error_code="UNAUTHORIZED",
            message="Your GitHub session expired or was revoked.",
            raw_status=status,
        )
    if status == 403:
        # Detect rate limit exhaustion
        try:
            remaining = headers.get("X-RateLimit-Remaining")
            if remaining is not None and str(remaining) == "0":
                return IdentityResult(
                    ok=False,
                    login=None,
                    user_id=None,
                    avatar_url=None,
                    error_code="RATE_LIMITED",
                    message="GitHub rate limit reached. Try again later.",
                    raw_status=status,
                )
        except Exception:
            pass
        return IdentityResult(
            ok=False,
            login=None,
            user_id=None,
            avatar_url=None,
            error_code="FORBIDDEN",
            message="Access forbidden. Check token scopes and permissions.",
            raw_status=status,
        )

    if status < 200 or status >= 300:
        return IdentityResult(
            ok=False,
            login=None,
            user_id=None,
            avatar_url=None,
            error_code="UNKNOWN",
            message="Unexpected response from GitHub.",
            raw_status=status,
        )

    # Success: parse fields safely
    login = None
    user_id = None
    avatar_url = None
    try:
        if js:
            login = js.get("login")
            uid = js.get("id")
            user_id = int(uid) if isinstance(uid, int) else None
            avatar_url = js.get("avatar_url")
    except Exception:
        # If parsing fails, still mark ok but omit fields
        pass

    return IdentityResult(
        ok=True,
        login=login,
        user_id=user_id,
        avatar_url=avatar_url,
        error_code=None,
        message="",
        raw_status=status,
    )
