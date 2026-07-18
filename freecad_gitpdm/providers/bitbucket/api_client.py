# -*- coding: utf-8 -*-
"""
Bitbucket Cloud REST API 2.0 client (stdlib-only, built on BaseApiClient).

Auth: `Authorization: Bearer <token>` — verified live against
api.bitbucket.org/2.0 that this is a real, recognized auth mechanism (API
tokens/repository access tokens, Atlassian's current-generation PAT
equivalent — not the older, now-deprecated App Passwords, which use Basic
auth with a username instead and aren't supported by this client).
"""

from __future__ import annotations

from freecad_gitpdm.providers.bitbucket.errors import BitbucketApiError
from freecad_gitpdm.providers.shared.http_client import BaseApiClient

BITBUCKET_API_BASE = "https://api.bitbucket.org/2.0"


class BitbucketApiClient(BaseApiClient):
    provider_id = "bitbucket"
    error_cls = BitbucketApiError

    def __init__(self, token: str, user_agent: str = "GitPDM/1.0"):
        super().__init__(BITBUCKET_API_BASE, token, user_agent)

    def _auth_headers(self):
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}
