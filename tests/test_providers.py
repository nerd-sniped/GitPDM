# -*- coding: utf-8 -*-
"""
Tests for the provider abstraction (Phase G4, R5.1-R5.3).
"""

import pytest

from freecad_gitpdm.providers import (
    DEFAULT_PROVIDER_ID,
    get_provider,
    get_provider_class,
    list_provider_ids,
)
from freecad_gitpdm.providers.base import GenericProvider, ProviderCapabilities
from freecad_gitpdm.providers.github.provider import GitHubProvider
from freecad_gitpdm.providers.gitlab.provider import GitLabProvider


class TestRegistry:
    def test_known_ids_resolve(self):
        assert get_provider_class("github") is GitHubProvider
        assert get_provider_class("generic") is GenericProvider
        assert get_provider_class("gitlab") is GitLabProvider

    def test_unknown_id_falls_back_to_generic(self):
        assert get_provider_class("bitbucket") is GenericProvider
        assert get_provider_class("") is GenericProvider

    def test_case_and_whitespace_insensitive(self):
        assert get_provider_class(" GitHub ") is GitHubProvider

    def test_list_provider_ids(self):
        assert list_provider_ids() == sorted(["github", "generic", "gitlab"])

    def test_default_provider_id_is_github(self):
        # Existing repos predate the provider field entirely; the default
        # must keep desktop behavior unchanged (see core/provider_config.py).
        assert DEFAULT_PROVIDER_ID == "github"

    def test_get_provider_instantiates(self):
        provider = get_provider("generic")
        assert isinstance(provider, GenericProvider)


class TestGenericProviderZeroApi:
    """R5.1's forcing requirement: GenericProvider makes zero host API calls."""

    def test_capabilities_all_false(self):
        caps = GenericProvider.capabilities
        assert caps == ProviderCapabilities(
            supports_device_flow=False,
            supports_repo_creation=False,
            supports_lfs_locking=False,
            supports_pull_requests=False,
        )

    def test_build_api_client_returns_none(self):
        provider = GenericProvider()
        assert provider.build_api_client("some-token") is None

    def test_create_remote_repo_raises_with_instructions(self):
        provider = GenericProvider()
        with pytest.raises(NotImplementedError, match="paste its clone URL"):
            provider.create_remote_repo(None, name="foo", private=True)

    def test_fetch_identity_raises(self):
        provider = GenericProvider()
        with pytest.raises(NotImplementedError):
            provider.fetch_identity(None)

    def test_no_device_flow_config(self):
        provider = GenericProvider()
        assert provider.get_client_id() is None
        assert provider.device_code_url is None
        assert provider.token_url is None
        assert provider.default_scopes == []


class TestGitHubProviderCapabilities:
    def test_capabilities(self):
        caps = GitHubProvider.capabilities
        assert caps.supports_device_flow is True
        assert caps.supports_repo_creation is True
        assert caps.supports_lfs_locking is False
        assert caps.supports_pull_requests is False

    def test_owns_auth_endpoints(self):
        provider = GitHubProvider()
        assert provider.device_code_url == "https://github.com/login/device/code"
        assert provider.token_url == "https://github.com/login/oauth/access_token"
        assert "repo" in provider.default_scopes

    def test_build_api_client(self):
        from freecad_gitpdm.providers.github.api_client import GitHubApiClient

        provider = GitHubProvider()
        client = provider.build_api_client("tok123")
        assert isinstance(client, GitHubApiClient)


class TestGitLabProviderCapabilities:
    """GitLab is a full PAT-auth provider now (see tests/test_gitlab_provider.py
    for the detailed API-client/create-repo/list-repos/identity coverage).
    This class only checks the registry-level capability contract."""

    def test_capabilities(self):
        caps = GitLabProvider.capabilities
        assert caps.supports_device_flow is False
        assert caps.supports_repo_creation is True
        assert caps.supports_lfs_locking is False
        assert caps.supports_pull_requests is False
        assert caps.requires_manual_token is True

    def test_no_device_flow_config(self):
        # supports_device_flow=False -> base class defaults apply, matching
        # GenericProvider's shape rather than raising NotImplementedError.
        provider = GitLabProvider()
        assert provider.get_client_id() is None
        assert provider.device_code_url is None
        assert provider.token_url is None
        assert provider.default_scopes == []


class TestAuthConfigBackwardCompat:
    """auth/config.py must keep working unchanged after G4 (existing UI callers)."""

    def test_reexports_match_provider(self):
        from freecad_gitpdm.auth import config as auth_config

        provider = GitHubProvider()
        assert auth_config.DEVICE_CODE_URL == provider.device_code_url
        assert auth_config.TOKEN_URL == provider.token_url
        assert auth_config.DEFAULT_SCOPES == provider.default_scopes
        assert auth_config.get_client_id() == provider.get_client_id()
