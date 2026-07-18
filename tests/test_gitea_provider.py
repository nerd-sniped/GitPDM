# -*- coding: utf-8 -*-
"""Tests for the Gitea/Forgejo provider (self-hosted, PAT auth)."""

from unittest.mock import MagicMock

import pytest

from freecad_gitpdm.providers.gitea.provider import GiteaProvider
from freecad_gitpdm.providers.gitea.api_client import GiteaApiClient
from freecad_gitpdm.providers.gitea.errors import GiteaApiError
from freecad_gitpdm.providers.gitea.create_repo import (
    CreateRepoRequest,
    create_user_repo,
)
from freecad_gitpdm.providers.gitea.repos import list_repos
from freecad_gitpdm.providers.gitea.identity import fetch_viewer_identity
from freecad_gitpdm.providers.base import RemoteRepoInfo, ViewerIdentity, RepoInfo


class TestGiteaProvider:
    def test_capabilities(self):
        caps = GiteaProvider.capabilities
        assert caps.supports_device_flow is False
        assert caps.supports_repo_creation is True
        assert caps.requires_manual_token is True
        assert caps.requires_host_url is True

    def test_no_default_host(self):
        assert GiteaProvider().default_host == ""

    def test_build_api_client_without_host_returns_none(self):
        p = GiteaProvider()
        assert p.build_api_client("tok") is None

    def test_build_api_client_with_host(self):
        p = GiteaProvider()
        client = p.build_api_client("tok", host="https://git.example.com")
        assert isinstance(client, GiteaApiClient)
        assert client._base_url == "https://git.example.com/api/v1"

    def test_build_api_client_strips_trailing_slash(self):
        p = GiteaProvider()
        client = p.build_api_client("tok", host="https://git.example.com/")
        assert client._base_url == "https://git.example.com/api/v1"


class TestGiteaApiClient:
    def test_auth_header_is_token_scheme(self):
        client = GiteaApiClient("https://git.example.com", "secrettok")
        assert client._auth_headers() == {"Authorization": "token secrettok"}

    def test_no_token_no_auth_header(self):
        client = GiteaApiClient("https://git.example.com", "")
        assert client._auth_headers() == {}


class TestGiteaApiError:
    def test_401(self):
        assert GiteaApiError.from_http_error(401).code == "UNAUTHORIZED"

    def test_404(self):
        err = GiteaApiError.from_http_error(404)
        assert err.code == "BAD_RESPONSE"
        assert "server URL" in err.message

    def test_429(self):
        assert GiteaApiError.from_http_error(429).code == "RATE_LIMITED"


class TestCreateRepo:
    def test_request_body_shape(self):
        client = MagicMock(spec=GiteaApiClient)
        client.request_json.return_value = (
            201,
            {
                "full_name": "alice/myproj",
                "html_url": "https://git.example.com/alice/myproj",
                "clone_url": "https://git.example.com/alice/myproj.git",
                "default_branch": "main",
            },
            {},
        )
        req = CreateRepoRequest(name="myproj", private=True, description="desc")
        info = create_user_repo(client, req)

        _, kwargs = client.request_json.call_args
        assert kwargs["url"] == "/user/repos"
        assert kwargs["body"] == {
            "name": "myproj",
            "private": True,
            "auto_init": False,
            "description": "desc",
        }
        assert info.full_name == "alice/myproj"

    def test_409_conflict_maps_to_friendly_message(self):
        client = MagicMock(spec=GiteaApiClient)
        client.request_json.return_value = (409, {}, {})
        with pytest.raises(GiteaApiError, match="already exists"):
            create_user_repo(client, CreateRepoRequest(name="myproj", private=True))

    def test_invalid_name_rejected(self):
        client = MagicMock(spec=GiteaApiClient)
        with pytest.raises(GiteaApiError):
            create_user_repo(client, CreateRepoRequest(name="bad name!", private=True))


class TestListRepos:
    def test_maps_fields_like_github(self):
        client = MagicMock(spec=GiteaApiClient)
        client._base_url = "https://git.example.com/api/v1"
        client.request_json.return_value = (
            200,
            [
                {
                    "full_name": "alice/proj1",
                    "name": "proj1",
                    "private": True,
                    "default_branch": "main",
                    "clone_url": "https://git.example.com/alice/proj1.git",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ],
            {},
        )
        repos = list_repos(client, use_cache=False)
        assert len(repos) == 1
        assert isinstance(repos[0], RepoInfo)
        assert repos[0].owner == "alice"

    def test_pagination_follows_link_header(self):
        client = MagicMock(spec=GiteaApiClient)
        client._base_url = "https://git.example.com/api/v1"
        client.request_json.side_effect = [
            (
                200,
                [],
                {
                    "Link": '<https://git.example.com/api/v1/user/repos?page=2>; rel="next"'
                },
            ),
            (200, [], {}),
        ]
        list_repos(client, use_cache=False)
        assert client.request_json.call_count == 2


class TestFetchIdentity:
    def test_success(self):
        client = MagicMock(spec=GiteaApiClient)
        client.request_json_result = None
        client.request_json.return_value = (
            200,
            {"login": "alice", "id": 7, "avatar_url": "https://x/y.png"},
            {},
        )
        result = fetch_viewer_identity(client)
        assert result.ok is True
        assert result.login == "alice"


class TestProviderTranslation:
    def test_create_remote_repo_maps_to_neutral_shape(self):
        p = GiteaProvider()
        client = MagicMock(spec=GiteaApiClient)
        client.request_json.return_value = (
            201,
            {
                "full_name": "alice/proj",
                "html_url": "https://git.example.com/alice/proj",
                "clone_url": "https://git.example.com/alice/proj.git",
                "default_branch": "main",
            },
            {},
        )
        result = p.create_remote_repo(client, name="proj", private=True)
        assert isinstance(result, RemoteRepoInfo)

    def test_fetch_identity_maps_to_neutral_shape(self):
        p = GiteaProvider()
        client = MagicMock(spec=GiteaApiClient)
        client.request_json_result = None
        client.request_json.return_value = (200, {"login": "alice", "id": 1}, {})
        result = p.fetch_identity(client)
        assert isinstance(result, ViewerIdentity)
