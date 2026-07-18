# -*- coding: utf-8 -*-
"""
Gitea/Forgejo REST API v1 client (stdlib-only, built on BaseApiClient).

Self-hosted: `base_url` is the user-entered server URL, not a fixed host
like GitHub/GitLab. Auth: `Authorization: token <token>` — verified live
against a public Forgejo instance (Codeberg) that this header is accepted
as a real auth attempt (a bogus token produces a "token is malformed"
error, not a "wrong header format" error).
"""

from __future__ import annotations

from freecad_gitpdm.providers.gitea.errors import GiteaApiError
from freecad_gitpdm.providers.shared.http_client import BaseApiClient


class GiteaApiClient(BaseApiClient):
    provider_id = "gitea"
    error_cls = GiteaApiError

    def __init__(self, server_url: str, token: str, user_agent: str = "GitPDM/1.0"):
        base = (server_url or "").rstrip("/")
        super().__init__(f"{base}/api/v1", token, user_agent)

    def _auth_headers(self):
        if self._token:
            return {"Authorization": f"token {self._token}"}
        return {}
