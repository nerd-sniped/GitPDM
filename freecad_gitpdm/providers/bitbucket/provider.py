# -*- coding: utf-8 -*-
"""
Bitbucket Cloud provider: PAT-paste auth (API tokens) + repo creation/
listing via REST API 2.0. `requires_workspace=True` is the one real UI
asymmetry among the providers here — unlike GitHub/GitLab/Gitea, a
Bitbucket repo lives under a workspace the user must specify, not just
"your account".

No device flow: Bitbucket Cloud has no OAuth device-flow support at all
(R5.2). PAT/SSH is "the universal floor" here too.

credential_username for git-over-HTTPS is "x-token-auth" — Bitbucket's
documented literal-username convention for Repository/Project/Workspace
Access Tokens used as the password. Not live-verified (would need a real
clone attempt with a real token); flagged for the real-token acceptance
pass per GITPDM_DEV_PLAN.md.
"""

from __future__ import annotations

from typing import Optional

from freecad_gitpdm.providers.base import (
    BaseProvider,
    ProviderCapabilities,
    RemoteRepoInfo,
    ViewerIdentity,
)

BITBUCKET_HOST = "bitbucket.org"


class BitbucketProvider(BaseProvider):
    provider_id = "bitbucket"
    display_name = "Bitbucket"
    capabilities = ProviderCapabilities(
        supports_device_flow=False,
        supports_repo_creation=True,
        supports_lfs_locking=False,
        supports_pull_requests=False,
        requires_manual_token=True,
        requires_workspace=True,
    )
    default_host = BITBUCKET_HOST
    credential_username = "x-token-auth"

    def build_api_client(
        self, token: str, user_agent: str = "GitPDM/1.0", host: Optional[str] = None
    ):
        from freecad_gitpdm.providers.bitbucket.api_client import BitbucketApiClient

        return BitbucketApiClient(token, user_agent)

    def create_remote_repo(
        self,
        api_client,
        name: str,
        private: bool,
        description: Optional[str] = None,
        workspace: Optional[str] = None,
    ) -> RemoteRepoInfo:
        from freecad_gitpdm.providers.bitbucket.create_repo import (
            CreateRepoRequest,
            create_user_repo,
        )

        req = CreateRepoRequest(
            name=name,
            private=private,
            description=description,
            workspace=workspace or "",
        )
        info = create_user_repo(api_client, req)
        return RemoteRepoInfo(
            full_name=info.full_name,
            html_url=info.html_url,
            clone_url=info.clone_url,
            default_branch=info.default_branch,
        )

    def fetch_identity(self, api_client) -> ViewerIdentity:
        from freecad_gitpdm.providers.bitbucket.identity import fetch_viewer_identity

        result = fetch_viewer_identity(api_client)
        return ViewerIdentity(
            ok=result.ok,
            login=result.login,
            message=result.message,
            error_code=result.error_code,
        )

    def list_repos(self, api_client, workspace: Optional[str] = None):
        from freecad_gitpdm.providers.bitbucket.repos import list_repos

        return list_repos(api_client, workspace=workspace or "")
