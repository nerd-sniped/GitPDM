# -*- coding: utf-8 -*-
"""
SourceHut provider: PAT-paste auth (Bearer token) + repo creation/listing
via the git.sr.ht GraphQL API. Additive beyond Dev_Docs/GITPDM_REQUIREMENTS.md's
documented four hosts (GitHub/GitLab/Bitbucket/Gitea) — added per explicit
user request. The riskiest provider here: its GraphQL schema could not be
live-verified (see providers/sourcehut/__init__.py) since the endpoint
requires auth even for introspection. Needs a real-token acceptance pass
before being trusted in production.

No device flow: SourceHut has no OAuth device-flow support. PAT/SSH is
"the universal floor" here too (R5.2's framing, though SourceHut itself
isn't in R5.2's table).
"""

from __future__ import annotations

from typing import Optional

from freecad_gitpdm.providers.base import (
    BaseProvider,
    ProviderCapabilities,
    RemoteRepoInfo,
    ViewerIdentity,
)

SOURCEHUT_HOST = "git.sr.ht"


class SourceHutProvider(BaseProvider):
    provider_id = "sourcehut"
    display_name = "SourceHut"
    capabilities = ProviderCapabilities(
        supports_device_flow=False,
        supports_repo_creation=True,
        supports_lfs_locking=False,
        supports_pull_requests=False,
        requires_manual_token=True,
    )
    default_host = SOURCEHUT_HOST
    # Any non-empty value works over git.sr.ht's HTTPS git auth (like
    # GitHub); "x-access-token" (the BaseProvider default) is fine.

    def build_api_client(
        self, token: str, user_agent: str = "GitPDM/1.0", host: Optional[str] = None
    ):
        from freecad_gitpdm.providers.sourcehut.api_client import SourceHutApiClient

        return SourceHutApiClient(token, user_agent)

    def create_remote_repo(
        self,
        api_client,
        name: str,
        private: bool,
        description: Optional[str] = None,
        workspace: Optional[str] = None,
    ) -> RemoteRepoInfo:
        from freecad_gitpdm.providers.sourcehut.create_repo import (
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
        from freecad_gitpdm.providers.sourcehut.identity import fetch_viewer_identity

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
        from freecad_gitpdm.providers.sourcehut.repos import list_repos

        return list_repos(
            api_client, use_cache=use_cache, cache_key_user=cache_key_user
        )
