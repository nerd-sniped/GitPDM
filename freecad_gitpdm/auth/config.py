# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
GitPDM OAuth Configuration

Phase G4: the GitHub OAuth endpoints and client id are now owned by
`providers.github.provider.GitHubProvider` (R5.1 — provider classes own
their auth config so the G1 credential chain and refresh path can consult
them instead of a hardcoded GitHub URL). This module re-exports the same
names for backward compatibility with existing callers (`ui/github_auth.py`,
`providers/github/identity.py`) rather than churning every call site in
this phase.
"""

from freecad_gitpdm.providers.github.provider import (
    DEFAULT_SCOPES,
    DEVICE_CODE_URL,
    GITHUB_API_BASE,
    GITHUB_HOST,
    TOKEN_URL,
    VERIFICATION_URI_DEFAULT,
    GitHubProvider,
)

__all__ = [
    "GITHUB_HOST",
    "GITHUB_API_BASE",
    "DEVICE_CODE_URL",
    "TOKEN_URL",
    "VERIFICATION_URI_DEFAULT",
    "DEFAULT_SCOPES",
    "get_client_id",
]


def get_client_id():
    """
    Get the GitHub OAuth client ID.

    Returns:
        str | None: Client ID if configured, None if placeholder

    Notes:
        Delegates to GitHubProvider.get_client_id(), which returns None
        when the client id is still the "REPLACE_ME" placeholder so UI
        can show "Not configured" message to users.
    """
    return GitHubProvider().get_client_id()
