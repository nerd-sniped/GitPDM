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
    def load_github_host(self) -> str: ...

    def load_github_login(self) -> str | None: ...


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

        from freecad_gitpdm.auth.token_store_wincred import WindowsCredentialStore

        return WindowsCredentialStore()

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

    def github_api_client(self):
        """Create a GitHubApiClient from stored token, or return None."""

        host = (self.settings.load_github_host() or "").strip()
        if not host:
            return None

        account = self.settings.load_github_login()

        store = self.token_store()
        token_resp = store.load(host, account)
        if not token_resp:
            return None

        from freecad_gitpdm.github.api_client import GitHubApiClient

        ua = "GitPDM/1.0"
        return GitHubApiClient("api.github.com", token_resp.access_token, ua)


_singleton: ServiceContainer | None = None


def get_services() -> ServiceContainer:
    """Default app-wide service container."""

    global _singleton
    if _singleton is None:
        from freecad_gitpdm.core import settings as settings_module

        _singleton = ServiceContainer(settings=settings_module)
    return _singleton
