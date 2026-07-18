# -*- coding: utf-8 -*-
"""
GitLab provider stub (Phase G4).

Proves the provider abstraction has a second hosted-provider shape without
committing to a full implementation. Capability flags are set per R5.2
(GitLab >= 17.9 supports OAuth device flow); every operation raises
NotImplementedError pointing at the tracking issue. Full implementation is
deferred until a real GitLab user exists (see GITPDM_DEV_PLAN.md
"Deferred" section).

Tracking issue: https://github.com/nerd-sniped/GitPDM/issues (file under
"GitLab provider" when picked up).
"""

from __future__ import annotations

from typing import List, Optional

from freecad_gitpdm.providers.base import (
    BaseProvider,
    ProviderCapabilities,
    RemoteRepoInfo,
    ViewerIdentity,
)

_NOT_IMPLEMENTED = (
    "GitLab support is a stub (Phase G4) — not implemented yet. "
    "Track progress at the GitLab-provider tracking issue."
)


class GitLabProvider(BaseProvider):
    provider_id = "gitlab"
    capabilities = ProviderCapabilities(
        supports_device_flow=True,  # GitLab >= 17.9 (R5.2); flow itself unimplemented
        supports_repo_creation=False,
        supports_lfs_locking=False,
        supports_pull_requests=False,
    )
    default_host = "gitlab.com"

    # GitLab's documented convention for PAT-over-HTTPS git auth: username
    # must be "oauth2" specifically (unlike GitHub, which ignores the
    # username field). Safe to set even in this stub -- it's a static fact
    # about GitLab's git transport, not an API call.
    credential_username = "oauth2"

    def get_client_id(self) -> Optional[str]:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    @property
    def device_code_url(self) -> Optional[str]:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    @property
    def token_url(self) -> Optional[str]:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    @property
    def default_scopes(self) -> List[str]:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def create_remote_repo(
        self,
        api_client,
        name: str,
        private: bool,
        description: Optional[str] = None,
    ) -> RemoteRepoInfo:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def fetch_identity(self, api_client) -> ViewerIdentity:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def build_api_client(self, token: str, user_agent: str = "GitPDM/1.0"):
        raise NotImplementedError(_NOT_IMPLEMENTED)
