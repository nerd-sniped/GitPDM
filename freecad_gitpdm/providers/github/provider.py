# -*- coding: utf-8 -*-
"""
GitHub provider: extends BaseProvider with device flow, repo-creation API,
and identity lookup on top of plain git.

Owns the GitHub OAuth endpoint configuration (R5.1) so the G1 credential
chain and the token-refresh path consult the provider instead of a
hardcoded URL. `freecad_gitpdm.auth.config` re-exports these values for
backward compatibility with existing callers.
"""

from __future__ import annotations

from typing import List, Optional

from freecad_gitpdm.providers.base import (
    BaseProvider,
    ProviderCapabilities,
    RemoteRepoInfo,
    ViewerIdentity,
)

# GitHub OAuth endpoints
GITHUB_HOST = "github.com"
GITHUB_API_BASE = "https://api.github.com"
DEVICE_CODE_URL = "https://github.com/login/device/code"
TOKEN_URL = "https://github.com/login/oauth/access_token"
VERIFICATION_URI_DEFAULT = "https://github.com/login/device"

# OAuth scopes requested
# - read:user: Get user profile (username, email)
# - repo: Full repository access (required for git push operations)
#
# NOTE: The 'repo' scope is broad but necessary because:
#   1. Git push via HTTPS requires 'repo' scope (GitHub requirement)
#   2. Repository creation via API requires 'repo' scope
#   3. Alternative 'public_repo' only works for public repos
#
# ARCHITECTURE NOTE: OAuth Apps (current architecture) grant access to ALL
# repositories. To limit access to specific repositories, GitPDM would need
# to migrate to GitHub Apps architecture, which supports per-repo installation.
# See docs/OAUTH_DEVICE_FLOW.md for detailed discussion.
DEFAULT_SCOPES = ["read:user", "repo"]

# Client ID for GitPDM GitHub OAuth App.
# "REPLACE_ME" indicates OAuth is not yet configured.
_CLIENT_ID = "Ov23li9bhJnBzf4o55fw"


class GitHubProvider(BaseProvider):
    provider_id = "github"
    display_name = "GitHub"
    capabilities = ProviderCapabilities(
        supports_device_flow=True,
        supports_repo_creation=True,
        supports_pull_requests=False,  # not implemented yet
    )
    default_host = GITHUB_HOST

    def get_client_id(self) -> Optional[str]:
        if _CLIENT_ID == "REPLACE_ME":
            return None
        return _CLIENT_ID

    @property
    def device_code_url(self) -> Optional[str]:
        return DEVICE_CODE_URL

    @property
    def token_url(self) -> Optional[str]:
        return TOKEN_URL

    @property
    def default_scopes(self) -> List[str]:
        return list(DEFAULT_SCOPES)

    def build_api_client(
        self, token: str, user_agent: str = "GitPDM/1.0", host: Optional[str] = None
    ):
        from freecad_gitpdm.providers.github.api_client import GitHubApiClient

        return GitHubApiClient("api.github.com", token, user_agent)

    def create_remote_repo(
        self,
        api_client,
        name: str,
        private: bool,
        description: Optional[str] = None,
        workspace: Optional[str] = None,
    ) -> RemoteRepoInfo:
        from freecad_gitpdm.providers.github.create_repo import (
            CreateRepoRequest,
            create_user_repo,
        )

        req = CreateRepoRequest(name=name, private=private, description=description)
        info = create_user_repo(api_client, req)
        return RemoteRepoInfo(
            full_name=info.full_name,
            html_url=info.html_url,
            clone_url=info.clone_url,
            default_branch=info.default_branch,
        )

    def fetch_identity(self, api_client) -> ViewerIdentity:
        from freecad_gitpdm.providers.github.identity import fetch_viewer_identity

        result = fetch_viewer_identity(api_client)
        return ViewerIdentity(
            ok=result.ok,
            login=result.login,
            message=result.message,
            error_code=result.error_code,
        )

    def list_repos(
        self,
        api_client,
        workspace: Optional[str] = None,
        use_cache: bool = True,
        cache_key_user: str = "default",
    ):
        from freecad_gitpdm.providers.github.repos import list_repos

        return list_repos(
            api_client, use_cache=use_cache, cache_key_user=cache_key_user
        )
