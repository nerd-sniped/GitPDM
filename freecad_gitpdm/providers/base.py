# -*- coding: utf-8 -*-
"""
GitPDM Provider Abstraction
Phase G4: stop GitHub leakage into the rest of the codebase (R5.1, R5.2, R5.3).

A "provider" is a git host (GitHub, GitLab, or none at all). `GenericProvider`
is the base case, not a fallback: plain git plus a PAT or ambient SSH agent
is enough to make GitPDM fully functional with zero host API calls. Hosted
providers (GitHub, GitLab) add device-flow auth and repo-creation-via-API on
top of that.

UI code must read `capabilities` and hide actions the active provider can't
perform — it must never offer an action that will fail.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ProviderCapabilities:
    """What a provider can do. UI gates on these flags, never on provider_id."""

    supports_device_flow: bool = False
    supports_repo_creation: bool = False
    supports_lfs_locking: bool = False
    supports_pull_requests: bool = False

    # Multi-provider support (PAT-paste hosts: GitLab, Bitbucket, Gitea/
    # Forgejo, SourceHut). Independent of supports_device_flow, which stays
    # about the *interactive* no-terminal auth UX and isn't the same thing
    # as "can this provider create/list repos" — a host can support repo
    # creation via a pasted PAT with no device flow at all, which is every
    # new provider added here.
    requires_manual_token: bool = False
    # True only for self-hostable providers (Gitea/Forgejo) where GitPDM
    # can't assume a fixed default_host and the UI must ask for the
    # instance's base URL.
    requires_host_url: bool = False
    # True only for providers whose repos live under a workspace/org the
    # user must specify (Bitbucket) rather than just "your account".
    requires_workspace: bool = False


@dataclass
class RemoteRepoInfo:
    """Provider-neutral result of creating (or pointing at) a remote repo."""

    full_name: str
    html_url: str
    clone_url: str
    default_branch: Optional[str] = None


@dataclass
class ViewerIdentity:
    """Provider-neutral authenticated-user result."""

    ok: bool
    login: Optional[str]
    message: str = ""
    error_code: Optional[str] = None


@dataclass
class RepoInfo:
    """Provider-neutral listed-repo result (repo picker table rows)."""

    owner: str
    name: str
    full_name: str
    private: bool
    default_branch: Optional[str]
    clone_url: str
    updated_at: Optional[str]


class BaseProvider:
    """
    Contract every git host (or lack thereof) must implement.

    Instantiate via `freecad_gitpdm.providers.get_provider_class()`, not
    directly, so callers stay decoupled from concrete provider classes.
    """

    provider_id: str = "base"
    capabilities: ProviderCapabilities = ProviderCapabilities()
    default_host: str = ""
    # Human-readable name for UI copy that shouldn't hardcode "GitHub"
    # (e.g. repo picker's "Sign in to {display_name} to list repositories").
    display_name: str = ""

    # Username to send alongside a PAT/token over HTTPS git auth (the
    # `username=` line in a git credential helper response). Hosts differ:
    # GitHub accepts any non-empty value, "x-access-token" is its own
    # convention; GitLab requires "oauth2" specifically. Consulted by
    # git/client.py's headless credential bridge (G1) so a container
    # deployment authenticates correctly against whichever host the repo
    # is configured for, not just GitHub.
    credential_username: str = "x-access-token"

    # ---- Auth endpoint ownership (R5.1: providers own their auth config,
    # so the G1 credential chain and refresh path can consult them instead
    # of a hardcoded GitHub URL). ----

    def get_client_id(self) -> Optional[str]:
        """OAuth client id for device flow, or None if unsupported/unconfigured."""
        return None

    @property
    def device_code_url(self) -> Optional[str]:
        return None

    @property
    def token_url(self) -> Optional[str]:
        return None

    @property
    def default_scopes(self) -> List[str]:
        return []

    # ---- Repo / identity operations. Base implementations refuse cleanly;
    # GenericProvider makes zero host API calls by construction. ----

    def create_remote_repo(
        self,
        api_client,
        name: str,
        private: bool,
        description: Optional[str] = None,
    ) -> RemoteRepoInfo:
        """Create a repo on the host. Raises if capabilities.supports_repo_creation is False."""
        raise NotImplementedError(
            f"{self.provider_id} does not support repository creation via API. "
            "Create the repository in your browser (or another tool), then "
            "paste its clone URL into GitPDM."
        )

    def fetch_identity(self, api_client) -> ViewerIdentity:
        """Verify the current credential against the host. Raises if no host API exists."""
        raise NotImplementedError(
            f"{self.provider_id} has no host API to verify identity against."
        )

    def list_repos(self, api_client) -> List[RepoInfo]:
        """List repos the credential can access. Raises if no host API exists."""
        raise NotImplementedError(
            f"{self.provider_id} has no host API to list repositories from."
        )

    def build_api_client(self, token: str, user_agent: str = "GitPDM/1.0"):
        """Construct a host API client for this provider, or None if it has no API."""
        return None


class GenericProvider(BaseProvider):
    """
    The base case: plain git + a PAT in the remote URL or an ambient SSH
    agent. Zero host API calls. This class alone must make GitPDM fully
    functional — configure, clone, save, commit, push all work through
    `git/client.py`, which is already host-agnostic.
    """

    provider_id = "generic"
    capabilities = ProviderCapabilities(
        supports_device_flow=False,
        supports_repo_creation=False,
        supports_lfs_locking=False,
        supports_pull_requests=False,
    )
    default_host = ""
