# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
GitLab identity verification via GET /user.

No token-refresh-check step here (unlike GitHub's identity.py): that
machinery exists for OAuth device-flow tokens with a refresh_token, which
GitLab support doesn't have in GitPDM yet (PAT-paste only — see
Dev_Docs/GITPDM_DEV_PLAN.md's multi-provider entry). A pasted personal access token
has no refresh concept; if it's expired or revoked, GitLab just returns
401 and the user re-pastes a new one.

Field name note: GitLab's response uses `username`, not GitHub's `login`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from freecad_gitpdm.providers.gitlab.api_client import GitLabApiClient
from freecad_gitpdm.providers.gitlab.errors import GitLabApiError
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


def fetch_viewer_identity(client: GitLabApiClient) -> IdentityResult:
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
        except GitLabApiError as e:
            return IdentityResult(
                ok=False,
                login=None,
                user_id=None,
                avatar_url=None,
                error_code=e.code or "UNKNOWN",
                message=e.message or "Unexpected response from GitLab.",
                raw_status=int(e.status or 0),
            )

    login = None
    user_id = None
    avatar_url = None
    try:
        if js:
            login = js.get("username")
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
