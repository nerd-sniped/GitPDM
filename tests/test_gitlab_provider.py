# -*- coding: utf-8 -*-
"""Tests for the GitLab provider (PAT auth, REST API v4)."""

from unittest.mock import patch, MagicMock

import pytest

from freecad_gitpdm.providers.gitlab.provider import GitLabProvider
from freecad_gitpdm.providers.gitlab.api_client import GitLabApiClient
from freecad_gitpdm.providers.gitlab.errors import GitLabApiError
from freecad_gitpdm.providers.gitlab.create_repo import (
    CreateRepoRequest,
    create_user_repo,
)
from freecad_gitpdm.providers.gitlab.repos import list_repos, _extract_next_page
from freecad_gitpdm.providers.gitlab.identity import fetch_viewer_identity
from freecad_gitpdm.providers.base import RemoteRepoInfo, ViewerIdentity, RepoInfo


class TestGitLabProvider:
    def test_capabilities(self):
        caps = GitLabProvider.capabilities
        assert caps.supports_device_flow is False
        assert caps.supports_repo_creation is True
        assert caps.requires_manual_token is True
        assert caps.requires_host_url is False

    def test_display_name_and_host(self):
        p = GitLabProvider()
        assert p.display_name == "GitLab"
        assert p.default_host == "gitlab.com"

    def test_credential_username_is_oauth2(self):
        assert GitLabProvider().credential_username == "oauth2"

    def test_build_api_client(self):
        p = GitLabProvider()
        client = p.build_api_client("tok123")
        assert isinstance(client, GitLabApiClient)
        assert client._base_url == "https://gitlab.com/api/v4"

    def test_no_device_flow_config(self):
        p = GitLabProvider()
        assert p.get_client_id() is None
        assert p.device_code_url is None
        assert p.token_url is None
        assert p.default_scopes == []


class TestGitLabApiClient:
    def test_auth_header_is_private_token(self):
        client = GitLabApiClient("gitlab.com", "secrettok")
        assert client._auth_headers() == {"PRIVATE-TOKEN": "secrettok"}

    def test_no_token_no_auth_header(self):
        client = GitLabApiClient("gitlab.com", "")
        assert client._auth_headers() == {}

    def test_provider_id(self):
        assert GitLabApiClient.provider_id == "gitlab"

    def test_error_cls(self):
        assert GitLabApiClient.error_cls is GitLabApiError


class TestGitLabApiError:
    def test_401(self):
        err = GitLabApiError.from_http_error(401)
        assert err.code == "UNAUTHORIZED"

    def test_429_is_rate_limited(self):
        err = GitLabApiError.from_http_error(429)
        assert err.code == "RATE_LIMITED"

    def test_403_with_zero_remaining_is_rate_limited(self):
        err = GitLabApiError.from_http_error(403, {"ratelimit-remaining": "0"})
        assert err.code == "RATE_LIMITED"

    def test_403_without_zero_remaining_is_forbidden(self):
        err = GitLabApiError.from_http_error(403, {"ratelimit-remaining": "10"})
        assert err.code == "FORBIDDEN"

    def test_500(self):
        err = GitLabApiError.from_http_error(500)
        assert err.code == "NETWORK"


class TestCreateRepo:
    def test_empty_name_rejected(self):
        client = MagicMock(spec=GitLabApiClient)
        with pytest.raises(GitLabApiError):
            create_user_repo(client, CreateRepoRequest(name="", private=True))

    def test_invalid_name_rejected(self):
        client = MagicMock(spec=GitLabApiClient)
        with pytest.raises(GitLabApiError):
            create_user_repo(client, CreateRepoRequest(name="bad name!", private=True))

    def test_request_body_shape(self):
        client = MagicMock(spec=GitLabApiClient)
        client.request_json.return_value = (
            201,
            {
                "path_with_namespace": "alice/myproj",
                "web_url": "https://gitlab.com/alice/myproj",
                "http_url_to_repo": "https://gitlab.com/alice/myproj.git",
                "default_branch": "main",
            },
            {},
        )
        req = CreateRepoRequest(name="myproj", private=True, description="desc")
        info = create_user_repo(client, req)

        args, kwargs = client.request_json.call_args
        assert kwargs["url"] == "/projects"
        assert kwargs["body"]["name"] == "myproj"
        assert kwargs["body"]["visibility"] == "private"
        assert kwargs["body"]["initialize_with_readme"] is False
        assert kwargs["body"]["description"] == "desc"
        assert info.full_name == "alice/myproj"
        assert info.clone_url == "https://gitlab.com/alice/myproj.git"

    def test_public_visibility_when_not_private(self):
        client = MagicMock(spec=GitLabApiClient)
        client.request_json.return_value = (
            201,
            {
                "path_with_namespace": "alice/myproj",
                "web_url": "x",
                "http_url_to_repo": "x.git",
                "default_branch": "main",
            },
            {},
        )
        create_user_repo(client, CreateRepoRequest(name="myproj", private=False))
        _, kwargs = client.request_json.call_args
        assert kwargs["body"]["visibility"] == "public"

    def test_incomplete_response_raises(self):
        client = MagicMock(spec=GitLabApiClient)
        client.request_json.return_value = (201, {"path_with_namespace": ""}, {})
        with pytest.raises(GitLabApiError):
            create_user_repo(client, CreateRepoRequest(name="myproj", private=True))


class TestListRepos:
    def test_extract_next_page(self):
        assert _extract_next_page({"X-Next-Page": "2"}) == "2"
        assert _extract_next_page({"X-Next-Page": ""}) is None
        assert _extract_next_page({}) is None

    def test_single_page_no_next(self):
        client = MagicMock(spec=GitLabApiClient)
        client._base_url = "https://gitlab.com/api/v4"
        client.request_json.return_value = (
            200,
            [
                {
                    "path_with_namespace": "alice/proj1",
                    "path": "proj1",
                    "visibility": "private",
                    "default_branch": "main",
                    "http_url_to_repo": "https://gitlab.com/alice/proj1.git",
                    "last_activity_at": "2026-01-01T00:00:00Z",
                }
            ],
            {},
        )
        repos = list_repos(client, use_cache=False)
        assert len(repos) == 1
        assert isinstance(repos[0], RepoInfo)
        assert repos[0].owner == "alice"
        assert repos[0].private is True

    def test_public_visibility_maps_to_not_private(self):
        client = MagicMock(spec=GitLabApiClient)
        client._base_url = "https://gitlab.com/api/v4"
        client.request_json.return_value = (
            200,
            [
                {
                    "path_with_namespace": "alice/pub",
                    "path": "pub",
                    "visibility": "public",
                    "default_branch": "main",
                    "http_url_to_repo": "x.git",
                    "last_activity_at": None,
                }
            ],
            {},
        )
        repos = list_repos(client, use_cache=False)
        assert repos[0].private is False

    def test_pagination_follows_x_next_page(self):
        client = MagicMock(spec=GitLabApiClient)
        client._base_url = "https://gitlab.com/api/v4"
        client.request_json.side_effect = [
            (200, [], {"X-Next-Page": "2"}),
            (200, [], {"X-Next-Page": ""}),
        ]
        list_repos(client, use_cache=False)
        assert client.request_json.call_count == 2
        second_call_url = client.request_json.call_args_list[1][0][1]
        assert "page=2" in second_call_url

    def test_bad_entry_skipped_not_fatal(self):
        client = MagicMock(spec=GitLabApiClient)
        client._base_url = "https://gitlab.com/api/v4"
        client.request_json.return_value = (
            200,
            [None, {"path_with_namespace": "alice/ok", "http_url_to_repo": "x.git"}],
            {},
        )
        repos = list_repos(client, use_cache=False)
        assert len(repos) == 1


class TestFetchIdentity:
    def test_uses_username_field_not_login(self):
        client = MagicMock(spec=GitLabApiClient)
        client.request_json_result = None
        client.request_json.return_value = (
            200,
            {"username": "alice", "id": 42, "avatar_url": "https://x/y.png"},
            {},
        )
        result = fetch_viewer_identity(client)
        assert result.ok is True
        assert result.login == "alice"
        assert result.user_id == 42

    def test_401_maps_to_unauthorized(self):
        client = MagicMock(spec=GitLabApiClient)
        client.request_json_result = None
        client.request_json.side_effect = GitLabApiError.from_http_error(401)
        result = fetch_viewer_identity(client)
        assert result.ok is False
        assert result.error_code == "UNAUTHORIZED"


class TestProviderTranslation:
    """RemoteRepoInfo/ViewerIdentity mapping at the provider boundary."""

    def test_create_remote_repo_maps_to_neutral_shape(self):
        p = GitLabProvider()
        client = MagicMock(spec=GitLabApiClient)
        client.request_json.return_value = (
            201,
            {
                "path_with_namespace": "alice/proj",
                "web_url": "https://gitlab.com/alice/proj",
                "http_url_to_repo": "https://gitlab.com/alice/proj.git",
                "default_branch": "main",
            },
            {},
        )
        result = p.create_remote_repo(client, name="proj", private=True)
        assert isinstance(result, RemoteRepoInfo)
        assert result.full_name == "alice/proj"

    def test_fetch_identity_maps_to_neutral_shape(self):
        p = GitLabProvider()
        client = MagicMock(spec=GitLabApiClient)
        client.request_json_result = None
        client.request_json.return_value = (200, {"username": "alice", "id": 1}, {})
        result = p.fetch_identity(client)
        assert isinstance(result, ViewerIdentity)
        assert result.login == "alice"
