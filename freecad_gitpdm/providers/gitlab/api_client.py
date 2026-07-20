# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
GitLab REST API v4 client (stdlib-only, built on the shared BaseApiClient).

Auth: `PRIVATE-TOKEN: <token>` header (GitLab's convention for personal/
project access tokens over the REST API — distinct from `Authorization:
Bearer` which GitLab reserves for OAuth application tokens). Verified live
against gitlab.com/api/v4 that an unauthenticated request returns 401 with
this endpoint reachable and JSON-shaped as expected.
"""

from __future__ import annotations

from freecad_gitpdm.providers.gitlab.errors import GitLabApiError
from freecad_gitpdm.providers.shared.http_client import BaseApiClient


class GitLabApiClient(BaseApiClient):
    provider_id = "gitlab"
    error_cls = GitLabApiError

    def __init__(self, host: str, token: str, user_agent: str = "GitPDM/1.0"):
        super().__init__(f"https://{host}/api/v4", token, user_agent)

    def _auth_headers(self):
        if self._token:
            return {"PRIVATE-TOKEN": self._token}
        return {}
