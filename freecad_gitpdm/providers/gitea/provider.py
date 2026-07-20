# -*- coding: utf-8 -*-
"""
Gitea/Forgejo provider: self-hosted, PAT-paste auth, GitHub-API-compatible
REST v1. No fixed `default_host` — `requires_host_url=True` drives the
wizard/panel UI to collect the instance's base URL, which then must be
threaded into `build_api_client(host=...)`.

No device flow: the open proposal to add it (go-gitea/gitea#27309) hasn't
been accepted (R5.2), and even where a host implements device flow, a
self-hosted instance needs its own OAuth app registration — no universal
client id exists off-SaaS. PAT/SSH is "the universal floor" (R5.2).
"""

from __future__ import annotations

from typing import Optional

from freecad_gitpdm.providers.base import (
    BaseProvider,
    ProviderCapabilities,
    RemoteRepoInfo,
    ViewerIdentity,
)


class GiteaProvider(BaseProvider):
    provider_id = "gitea"
    display_name = "Gitea / Forgejo"
    capabilities = ProviderCapabilities(
        supports_device_flow=False,
        supports_repo_creation=True,
        supports_pull_requests=False,
        requires_manual_token=True,
        requires_host_url=True,
    )
    default_host = ""
    # Any non-empty value works over Gitea's git-over-HTTPS auth (like
    # GitHub); "x-access-token" (the BaseProvider default) is fine.

    def build_api_client(
        self, token: str, user_agent: str = "GitPDM/1.0", host: Optional[str] = None
    ):
        from freecad_gitpdm.providers.gitea.api_client import GiteaApiClient

        if not host:
            return None
        return GiteaApiClient(host, token, user_agent)

    def create_remote_repo(
        self,
        api_client,
        name: str,
        private: bool,
        description: Optional[str] = None,
        workspace: Optional[str] = None,
    ) -> RemoteRepoInfo:
        from freecad_gitpdm.providers.gitea.create_repo import (
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
        from freecad_gitpdm.providers.gitea.identity import fetch_viewer_identity

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
        from freecad_gitpdm.providers.gitea.repos import list_repos

        return list_repos(
            api_client, use_cache=use_cache, cache_key_user=cache_key_user
        )
