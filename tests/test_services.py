# -*- coding: utf-8 -*-
"""
Tests for core.services.ServiceContainer, focused on the multi-provider
credential-resolution fix: api_client_for(provider) must resolve host/
account per-provider (via settings.load_provider_host/login), not from a
single hardcoded GitHub settings slot regardless of which provider was
passed in - the bug found while wiring up the repo picker/wizard for
GitLab/Bitbucket/Gitea/SourceHut.
"""

from unittest.mock import MagicMock

from freecad_gitpdm.core.services import ServiceContainer
from freecad_gitpdm.providers.github.provider import GitHubProvider
from freecad_gitpdm.providers.gitlab.provider import GitLabProvider
from freecad_gitpdm.providers.gitea.provider import GiteaProvider
from freecad_gitpdm.providers.base import GenericProvider


class _FakeToken:
    def __init__(self, access_token):
        self.access_token = access_token


class _FakeSettings:
    """Mimics core/settings.py's provider-namespaced functions with an
    in-memory dict, so tests don't need the mock_freecad fixture."""

    def __init__(self):
        self.hosts = {}
        self.logins = {}

    def load_provider_host(self, provider_id, default_host=""):
        return self.hosts.get(provider_id, default_host)

    def load_provider_login(self, provider_id):
        return self.logins.get(provider_id)


def _container(settings, token_store, git_client_factory=None):
    return ServiceContainer(
        settings=settings,
        token_store_factory=lambda: token_store,
        git_client_factory=git_client_factory,
    )


class TestApiClientForMultiProvider:
    def test_resolves_host_and_account_per_provider(self, monkeypatch):
        monkeypatch.setattr(
            "freecad_gitpdm.auth.credential_chain.resolve_env_credential",
            lambda: None,
        )

        fake_settings = _FakeSettings()
        fake_settings.hosts["github"] = "github.com"
        fake_settings.logins["github"] = "alice-gh"
        fake_settings.hosts["gitlab"] = "gitlab.com"
        fake_settings.logins["gitlab"] = "alice-gl"

        calls = []

        class _RecordingStore:
            def load(self, host, account):
                calls.append((host, account))
                return _FakeToken(f"token-for-{host}")

        container = _container(fake_settings, _RecordingStore())

        gh_client = container.api_client_for(GitHubProvider())
        gl_client = container.api_client_for(GitLabProvider())

        assert calls == [
            ("github.com", "alice-gh"),
            ("gitlab.com", "alice-gl"),
        ]
        # Different providers must not silently share one client/token.
        assert gh_client is not None
        assert gl_client is not None
        assert gh_client._token != gl_client._token

    def test_falls_back_to_provider_default_host_when_unset(self, monkeypatch):
        monkeypatch.setattr(
            "freecad_gitpdm.auth.credential_chain.resolve_env_credential",
            lambda: None,
        )
        fake_settings = _FakeSettings()  # nothing recorded yet

        calls = []

        class _RecordingStore:
            def load(self, host, account):
                calls.append((host, account))
                return _FakeToken("tok")

        container = _container(fake_settings, _RecordingStore())
        container.api_client_for(GitLabProvider())

        assert calls == [("gitlab.com", None)]

    def test_gitea_host_flows_through_to_build_api_client(self, monkeypatch):
        monkeypatch.setattr(
            "freecad_gitpdm.auth.credential_chain.resolve_env_credential",
            lambda: None,
        )
        fake_settings = _FakeSettings()
        fake_settings.hosts["gitea"] = "https://gitea.example.com"
        fake_settings.logins["gitea"] = "alice"

        class _Store:
            def load(self, host, account):
                return _FakeToken("tok")

        container = _container(fake_settings, _Store())
        client = container.api_client_for(GiteaProvider())

        assert client is not None
        assert client._base_url == "https://gitea.example.com/api/v1"

    def test_no_host_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            "freecad_gitpdm.auth.credential_chain.resolve_env_credential",
            lambda: None,
        )
        fake_settings = _FakeSettings()  # generic has no default_host either

        container = _container(fake_settings, MagicMock())
        assert container.api_client_for(GenericProvider()) is None

    def test_no_stored_token_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            "freecad_gitpdm.auth.credential_chain.resolve_env_credential",
            lambda: None,
        )
        fake_settings = _FakeSettings()
        fake_settings.hosts["github"] = "github.com"

        class _EmptyStore:
            def load(self, host, account):
                return None

        container = _container(fake_settings, _EmptyStore())
        assert container.api_client_for(GitHubProvider()) is None

    def test_env_credential_takes_precedence_over_stored_token(self, monkeypatch):
        env_cred = MagicMock()
        env_cred.token.access_token = "env-token"
        monkeypatch.setattr(
            "freecad_gitpdm.auth.credential_chain.resolve_env_credential",
            lambda: env_cred,
        )

        fake_settings = _FakeSettings()
        store_called = []

        class _Store:
            def load(self, host, account):
                store_called.append(True)
                return _FakeToken("should-not-be-used")

        container = _container(fake_settings, _Store())
        client = container.api_client_for(GitHubProvider())

        assert client is not None
        assert client._token == "env-token"
        assert not store_called  # env credential short-circuits the store lookup
