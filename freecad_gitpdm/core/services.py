# -*- coding: utf-8 -*-
"""GitPDM Services / Composition Root

Sprint 3: Minimal dependency container to centralize object creation.

Design goals:
- No UI/Qt imports at module import time.
- Provide a single place to construct shared services (git client, token
  store, GitHub API client factory).
- Support injection of a settings provider for tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable


@runtime_checkable
class _SettingsLike(Protocol):
    def load_provider_host(self, provider_id: str, default_host: str = "") -> str: ...

    def load_provider_login(self, provider_id: str) -> str | None: ...


@runtime_checkable
class _TokenLike(Protocol):
    access_token: str


@runtime_checkable
class _TokenStoreLike(Protocol):
    def load(self, host: str, account: str | None) -> _TokenLike | None: ...


@dataclass
class ServiceContainer:
    """Small container for shared service construction.

    This is intentionally minimal and mostly a composition root.
    """

    settings: _SettingsLike
    token_store_factory: Callable[[], _TokenStoreLike] | None = None
    git_client_factory: Callable[[], object] | None = None

    def token_store(self):
        if self.token_store_factory is not None:
            return self.token_store_factory()

        from freecad_gitpdm.auth.token_store_factory import create_token_store

        return create_token_store()

    def git_client(self):
        if self.git_client_factory is not None:
            return self.git_client_factory()

        from freecad_gitpdm.git.client import GitClient

        return GitClient()

    def job_runner(self):
        """Return the shared Qt job runner.

        NOTE: Imports Qt only when called (i.e., inside FreeCAD).
        """

        from freecad_gitpdm.core import jobs

        return jobs.get_job_runner()

    def provider_for_repo(self, repo_root: str):
        """Resolve the active BaseProvider for a repo (Phase G4).

        Reads `.freecad-pdm/config.json`'s `provider` field (see
        `core/provider_config.py`); defaults to GitHub for repos that
        predate this field, so existing desktop behavior is unchanged.
        """

        from freecad_gitpdm.core.provider_config import get_provider_id
        from freecad_gitpdm.providers import get_provider

        return get_provider(get_provider_id(repo_root))

    def api_client_for(self, provider):
        """Build `provider`'s host API client from the credential chain, or None.

        Providers with no host API (GenericProvider) return None here via
        `BaseProvider.build_api_client`. Environment credentials
        (GITPDM_TOKEN_FILE / GITPDM_TOKEN, Phase G1) take precedence and
        require no configured host or stored token.

        Host/account resolution is keyed by `provider.provider_id` (via
        `settings.load_provider_host()`/`load_provider_login()`) rather than
        the old hardcoded GitHub-only settings lookup, so this correctly
        resolves credentials for GitLab/Bitbucket/Gitea/SourceHut too, not
        just GitHub — each provider's connection state lives in its own
        namespaced settings keys (core/settings.py) and doesn't collide
        with another provider's.
        """

        from freecad_gitpdm.auth.credential_chain import resolve_env_credential

        ua = "GitPDM/1.0"

        env_cred = resolve_env_credential()
        if env_cred is not None:
            return provider.build_api_client(env_cred.token.access_token, ua)

        host = (
            self.settings.load_provider_host(
                provider.provider_id, default_host=provider.default_host
            )
            or ""
        ).strip()
        if not host:
            return None

        account = self.settings.load_provider_login(provider.provider_id)

        store = self.token_store()
        token_resp = store.load(host, account)
        if not token_resp:
            return None

        return provider.build_api_client(token_resp.access_token, ua, host=host)

    def github_api_client(self):
        """Create a GitHubApiClient from the credential chain, or None.

        Kept for backward compatibility with existing callers that only
        ever spoke to GitHub; behavior is unchanged from before Phase G4.
        New provider-aware code should use `provider_for_repo()` +
        `api_client_for()` instead.
        """

        from freecad_gitpdm.providers.github.provider import GitHubProvider

        return self.api_client_for(GitHubProvider())


_singleton: ServiceContainer | None = None


def get_services() -> ServiceContainer:
    """Default app-wide service container."""

    global _singleton
    if _singleton is None:
        from freecad_gitpdm.core import settings as settings_module

        _singleton = ServiceContainer(settings=settings_module)
    return _singleton
