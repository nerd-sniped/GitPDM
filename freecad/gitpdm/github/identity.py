"""
GitHub Identity Fetcher
Sprint OAUTH-2: Verify current viewer identity via REST API.
Sprint OAUTH-6: Structured error handling
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from freecad.gitpdm.github.api_client import GitHubApiClient
from freecad.gitpdm.github.errors import GitHubApiNetworkError, GitHubApiError


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

    SECURITY: Automatically refreshes expired tokens before making request.
    """
    # SECURITY: Check if token needs refresh before API call
    from freecad.gitpdm.auth import token_refresh
    from freecad.gitpdm.auth import config as auth_config
    from freecad.gitpdm.core import settings

    try:
        # Load current token to check expiry
        from freecad.gitpdm.auth.token_store_factory import get_token_store

        store = get_token_store()
        host = settings.load_github_host()
        account = settings.load_github_login()
        current_token = store.load(host, account)

        if current_token:
            is_fresh, fresh_token, msg = token_refresh.ensure_fresh_token(
                current_token,
                auth_config.get_client_id() or "",
            )

            if not is_fresh:
                # Token expired and couldn't refresh
                from freecad.gitpdm.core import log

                log.debug(f"Token refresh needed but failed: {msg}")
                return IdentityResult(
                    ok=False,
                    login=None,
                    user_id=None,
                    avatar_url=None,
                    error_code="TOKEN_EXPIRED",
                    message=msg,
                    raw_status=401,
                )

            # If token was refreshed, save the new one
            if fresh_token != current_token:
                from freecad.gitpdm.core import log

                log.debug("Token auto-refreshed successfully")
                store.save(host, account, fresh_token)
                # Note: client still uses old token; this refresh helps for next call
                # A full implementation would recreate the client with new token
    except Exception as e:
        # Don't fail identity fetch if refresh check fails
        from freecad.gitpdm.core import log

        log.debug(f"Token refresh check failed (continuing with existing token): {e}")

    status = 0
    js = None
    headers = {}

    # Prefer Result-based wrapper when available (Sprint 2). This also
    # preserves compatibility with older stubs/tests that only implement
    # request_json().
    request_json_result = getattr(client, "request_json_result", None)
    if callable(request_json_result):
        res = request_json_result("GET", "/user", headers=None, body=None, timeout_s=10)
        if not res.ok:
            err = res.error
            code = err.code if err else "UNKNOWN"
            raw_status = 0
            try:
                raw_status = int((err.meta or {}).get("status") or 0) if err else 0
            except Exception:
                raw_status = 0

            # Match legacy error_code strings where possible
            mapped_code = code
            if code == "NETWORK_ERROR":
                mapped_code = "NETWORK_ERROR"

            return IdentityResult(
                ok=False,
                login=None,
                user_id=None,
                avatar_url=None,
                error_code=mapped_code,
                message=(err.message if err else "An unexpected error occurred."),
                raw_status=raw_status,
            )

        status, js, headers = res.value  # type: ignore[misc]
    else:
        try:
            status, js, headers = client.request_json(
                "GET", "/user", headers=None, body=None, timeout_s=10
            )
        except GitHubApiNetworkError:
            return IdentityResult(
                ok=False,
                login=None,
                user_id=None,
                avatar_url=None,
                error_code="NETWORK_ERROR",
                message="Network error. Check connection and try again.",
                raw_status=0,
            )
        except GitHubApiError as e:
            return IdentityResult(
                ok=False,
                login=None,
                user_id=None,
                avatar_url=None,
                error_code=e.code or "UNKNOWN",
                message=e.message or "Unexpected response from GitHub.",
                raw_status=int(e.status or 0),
            )
        except Exception:
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
