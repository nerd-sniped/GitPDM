# -*- coding: utf-8 -*-
"""
Gitea/Forgejo identity verification via GET /user.

No token-refresh-check step (PAT-paste only, no OAuth device flow for this
provider yet - see providers/gitea/provider.py). Field names (`login`,
`id`, `avatar_url`) match GitHub's, by Gitea's own API-compatibility design.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from freecad_gitpdm.providers.gitea.api_client import GiteaApiClient
from freecad_gitpdm.providers.gitea.errors import GiteaApiError
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


def fetch_viewer_identity(client: GiteaApiClient) -> IdentityResult:
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
        except GiteaApiError as e:
            return IdentityResult(
                ok=False,
                login=None,
                user_id=None,
                avatar_url=None,
                error_code=e.code or "UNKNOWN",
                message=e.message or "Unexpected response from the server.",
                raw_status=int(e.status or 0),
            )

    login = None
    user_id = None
    avatar_url = None
    try:
        if js:
            login = js.get("login") or js.get("username")
            uid = js.get("id")
            user_id = int(uid) if isinstance(uid, int) else None
            avatar_url = js.get("avatar_url")
    except (AttributeError, TypeError):
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
