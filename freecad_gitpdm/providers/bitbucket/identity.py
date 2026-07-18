# -*- coding: utf-8 -*-
"""
Bitbucket Cloud identity verification via GET /2.0/user.

No int `id` field exists (unlike GitHub/GitLab/Gitea) - Bitbucket
identifies accounts by `account_id`/`uuid` strings, so `user_id` is always
None here; `login` maps to Bitbucket's `username` field.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from freecad_gitpdm.providers.bitbucket.api_client import BitbucketApiClient
from freecad_gitpdm.providers.bitbucket.errors import BitbucketApiError
from freecad_gitpdm.providers.shared.errors import ProviderApiNetworkError


@dataclass
class IdentityResult:
    ok: bool
    login: Optional[str]
    user_id: Optional[int]
    avatar_url: Optional[str]
    error_code: Optional[str]
    message: str
    raw_status: int


def fetch_viewer_identity(client: BitbucketApiClient) -> IdentityResult:
    request_json_result = getattr(client, "request_json_result", None)
    if callable(request_json_result):
        res = request_json_result("GET", "/user", headers=None, body=None, timeout_s=10)
        if not res.ok:
            err = res.error
            raw_status = 0
            try:
                raw_status = int((err.meta or {}).get("status") or 0) if err else 0
            except (TypeError, ValueError):
                raw_status = 0
            return IdentityResult(
                ok=False,
                login=None,
                user_id=None,
                avatar_url=None,
                error_code=err.code if err else "UNKNOWN",
                message=(err.message if err else "An unexpected error occurred."),
                raw_status=raw_status,
            )
        status, js, _headers = res.value
    else:
        try:
            status, js, _headers = client.request_json(
                "GET", "/user", headers=None, body=None, timeout_s=10
            )
        except ProviderApiNetworkError:
            return IdentityResult(
                ok=False,
                login=None,
                user_id=None,
                avatar_url=None,
                error_code="NETWORK_ERROR",
                message="Network error. Check connection and try again.",
                raw_status=0,
            )
        except BitbucketApiError as e:
            return IdentityResult(
                ok=False,
                login=None,
                user_id=None,
                avatar_url=None,
                error_code=e.code or "UNKNOWN",
                message=e.message or "Unexpected response from Bitbucket.",
                raw_status=int(e.status or 0),
            )

    login = None
    avatar_url = None
    try:
        if js:
            login = js.get("username") or js.get("display_name")
            links = js.get("links") or {}
            avatar_url = (links.get("avatar") or {}).get("href")
    except (AttributeError, TypeError):
        pass

    return IdentityResult(
        ok=True,
        login=login,
        user_id=None,
        avatar_url=avatar_url,
        error_code=None,
        message="",
        raw_status=status,
    )
