# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
SourceHut identity verification via the git.sr.ht GraphQL `me` query.

**Unverified against the live schema** - see providers/sourcehut/__init__.py.
`login` maps to `canonicalName` (SourceHut's ~-prefixed public identifier,
e.g. "~alice") rather than a separate "username" field, since that's the
identifier used in clone URLs and is what matters for GitPDM's purposes.
`user_id` is likely an opaque ID (not necessarily an int) in SourceHut's
schema, so it's left None here rather than guessed at.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from freecad_gitpdm.providers.sourcehut.api_client import SourceHutApiClient
from freecad_gitpdm.providers.sourcehut.errors import SourceHutApiError
from freecad_gitpdm.providers.shared.errors import ProviderApiNetworkError

_ME_QUERY = """
query Me {
  me {
    canonicalName
    username
    email
  }
}
"""


@dataclass
class IdentityResult:
    ok: bool
    login: Optional[str]
    user_id: Optional[int]
    avatar_url: Optional[str]
    error_code: Optional[str]
    message: str
    raw_status: int


def fetch_viewer_identity(client: SourceHutApiClient) -> IdentityResult:
    try:
        data = client.graphql(_ME_QUERY, timeout_s=10)
    except SourceHutApiError as e:
        return IdentityResult(
            ok=False,
            login=None,
            user_id=None,
            avatar_url=None,
            error_code=e.code or "UNKNOWN",
            message=e.message or "Unexpected response from SourceHut.",
            raw_status=int(e.status or 0),
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

    me = data.get("me") if isinstance(data, dict) else None
    if not me:
        return IdentityResult(
            ok=False,
            login=None,
            user_id=None,
            avatar_url=None,
            error_code="BAD_RESPONSE",
            message="SourceHut returned no user data for this token.",
            raw_status=200,
        )

    login = None
    try:
        login = me.get("canonicalName") or me.get("username")
    except (AttributeError, TypeError):
        pass

    return IdentityResult(
        ok=True,
        login=login,
        user_id=None,
        avatar_url=None,
        error_code=None,
        message="",
        raw_status=200,
    )
