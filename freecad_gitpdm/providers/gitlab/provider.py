# -*- coding: utf-8 -*-
"""
GitLab provider: PAT-paste auth + repo creation/listing via REST API v4.

No device flow: GitLab 17.9+ does support OAuth device flow (R5.2), but
device flow needs a pre-registered OAuth application per host, which
GitPDM doesn't have for GitLab yet. R5.2 documents PAT/SSH as "the
universal floor" for exactly this reason. `requires_manual_token=True`
drives the wizard/panel PAT-entry UI instead.

Known limitation: only gitlab.com is supported (self-managed GitLab
instances would need a host-URL field like Gitea/Forgejo's — not built
here; `requires_host_url` stays False for GitLab in this pass).
"""

from __future__ import annotations

from typing import Optional

from freecad_gitpdm.providers.base import (
    BaseProvider,
    ProviderCapabilities,
    RemoteRepoInfo,
    ViewerIdentity,
)

GITLAB_HOST = "gitlab.com"


class GitLabProvider(BaseProvider):
    provider_id = "gitlab"
    display_name = "GitLab"
    capabilities = ProviderCapabilities(
        supports_device_flow=False,
        supports_repo_creation=True,
        supports_lfs_locking=False,  # D1, deferred until a real lfs-mode team user exists
        supports_pull_requests=False,
        requires_manual_token=True,
    )
    default_host = GITLAB_HOST
    credential_username = "oauth2"  # GitLab's PAT-over-HTTPS convention

    def build_api_client(self, token: str, user_agent: str = "GitPDM/1.0"):
        from freecad_gitpdm.providers.gitlab.api_client import GitLabApiClient

        return GitLabApiClient(self.default_host, token, user_agent)

    def create_remote_repo(
        self,
        api_client,
        name: str,
        private: bool,
        description: Optional[str] = None,
    ) -> RemoteRepoInfo:
        from freecad_gitpdm.providers.gitlab.create_repo import (
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
        from freecad_gitpdm.providers.gitlab.identity import fetch_viewer_identity

        result = fetch_viewer_identity(api_client)
        return ViewerIdentity(
            ok=result.ok,
            login=result.login,
            message=result.message,
            error_code=result.error_code,
        )

    def list_repos(self, api_client):
        from freecad_gitpdm.providers.gitlab.repos import list_repos

        return list_repos(api_client)
