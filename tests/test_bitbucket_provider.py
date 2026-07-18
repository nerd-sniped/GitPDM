# -*- coding: utf-8 -*-
"""Tests for the Bitbucket Cloud provider (PAT/API-token auth, workspace-scoped)."""

from unittest.mock import MagicMock

import pytest

from freecad_gitpdm.providers.bitbucket.provider import BitbucketProvider
from freecad_gitpdm.providers.bitbucket.api_client import BitbucketApiClient
from freecad_gitpdm.providers.bitbucket.errors import BitbucketApiError
from freecad_gitpdm.providers.bitbucket.create_repo import (
    CreateRepoRequest,
    create_user_repo,
    _slugify,
    _extract_https_clone_url,
)
from freecad_gitpdm.providers.bitbucket.repos import list_repos
from freecad_gitpdm.providers.bitbucket.identity import fetch_viewer_identity
from freecad_gitpdm.providers.base import RemoteRepoInfo, ViewerIdentity, RepoInfo


class TestBitbucketProvider:
    def test_capabilities(self):
        caps = BitbucketProvider.capabilities
        assert caps.supports_device_flow is False
        assert caps.supports_repo_creation is True
        assert caps.requires_manual_token is True
        assert caps.requires_workspace is True
        assert caps.requires_host_url is False

    def test_credential_username(self):
        assert BitbucketProvider().credential_username == "x-token-auth"

    def test_build_api_client(self):
        client = BitbucketProvider().build_api_client("tok")
        assert isinstance(client, BitbucketApiClient)
        assert client._base_url == "https://api.bitbucket.org/2.0"


class TestBitbucketApiClient:
    def test_auth_header_is_bearer(self):
        client = BitbucketApiClient("secrettok")
        assert client._auth_headers() == {"Authorization": "Bearer secrettok"}

    def test_no_token_no_auth_header(self):
        assert BitbucketApiClient("")._auth_headers() == {}


class TestBitbucketApiError:
    def test_401(self):
        assert BitbucketApiError.from_http_error(401).code == "UNAUTHORIZED"

    def test_404(self):
        err = BitbucketApiError.from_http_error(404)
        assert "workspace" in err.message

    def test_429(self):
        assert BitbucketApiError.from_http_error(429).code == "RATE_LIMITED"


class TestSlugify:
    def test_lowercase_and_spaces(self):
        assert _slugify("My Cool Project") == "my-cool-project"

    def test_invalid_chars_replaced(self):
        assert _slugify("proj!@#name") == "proj-name"

    def test_empty_falls_back(self):
        assert _slugify("   ") == "repo"


class TestExtractHttpsCloneUrl:
    def test_finds_https_entry(self):
        links = [
            {"name": "ssh", "href": "git@bitbucket.org:x/y.git"},
            {"name": "https", "href": "https://bitbucket.org/x/y.git"},
        ]
        assert _extract_https_clone_url(links) == "https://bitbucket.org/x/y.git"

    def test_missing_returns_empty(self):
        assert _extract_https_clone_url(None) == ""
        assert _extract_https_clone_url([]) == ""


class TestCreateRepo:
    def test_requires_workspace(self):
        client = MagicMock(spec=BitbucketApiClient)
        with pytest.raises(BitbucketApiError, match="workspace"):
            create_user_repo(
                client, CreateRepoRequest(name="proj", private=True, workspace="")
            )

    def test_request_uses_workspace_slug_url(self):
        client = MagicMock(spec=BitbucketApiClient)
        client.request_json.return_value = (
            201,
            {
                "full_name": "myteam/my-cool-project",
                "links": {
                    "html": {"href": "https://bitbucket.org/myteam/my-cool-project"},
                    "clone": [
                        {
                            "name": "https",
                            "href": "https://bitbucket.org/myteam/my-cool-project.git",
                        },
                        {
                            "name": "ssh",
                            "href": "git@bitbucket.org:myteam/my-cool-project.git",
                        },
                    ],
                },
                "mainbranch": {"name": "main"},
            },
            {},
        )
        req = CreateRepoRequest(
            name="My Cool Project", private=True, workspace="myteam", description="d"
        )
        info = create_user_repo(client, req)

        _, kwargs = client.request_json.call_args
        assert kwargs["url"] == "/repositories/myteam/my-cool-project"
        assert kwargs["body"]["scm"] == "git"
        assert kwargs["body"]["is_private"] is True
        assert info.full_name == "myteam/my-cool-project"
        assert info.clone_url == "https://bitbucket.org/myteam/my-cool-project.git"
        assert info.default_branch == "main"


class TestListRepos:
    def test_requires_workspace(self):
        client = MagicMock(spec=BitbucketApiClient)
        with pytest.raises(BitbucketApiError):
            list_repos(client, workspace="", use_cache=False)

    def test_parses_values_envelope(self):
        client = MagicMock(spec=BitbucketApiClient)
        client.request_json.return_value = (
            200,
            {
                "values": [
                    {
                        "full_name": "myteam/proj1",
                        "slug": "proj1",
                        "is_private": False,
                        "mainbranch": {"name": "main"},
                        "links": {
                            "clone": [
                                {
                                    "name": "https",
                                    "href": "https://bitbucket.org/myteam/proj1.git",
                                }
                            ]
                        },
                        "updated_on": "2026-01-01T00:00:00Z",
                    }
                ],
                "next": None,
            },
            {},
        )
        repos = list_repos(client, workspace="myteam", use_cache=False)
        assert len(repos) == 1
        assert isinstance(repos[0], RepoInfo)
        assert repos[0].owner == "myteam"
        assert repos[0].clone_url == "https://bitbucket.org/myteam/proj1.git"

    def test_pagination_follows_next_url(self):
        client = MagicMock(spec=BitbucketApiClient)
        client.request_json.side_effect = [
            (
                200,
                {
                    "values": [],
                    "next": "https://api.bitbucket.org/2.0/repositories/myteam?page=2",
                },
                {},
            ),
            (200, {"values": [], "next": None}, {}),
        ]
        list_repos(client, workspace="myteam", use_cache=False)
        assert client.request_json.call_count == 2
        second_call_url = client.request_json.call_args_list[1][0][1]
        assert (
            second_call_url
            == "https://api.bitbucket.org/2.0/repositories/myteam?page=2"
        )


class TestFetchIdentity:
    def test_success_uses_username(self):
        client = MagicMock(spec=BitbucketApiClient)
        client.request_json_result = None
        client.request_json.return_value = (
            200,
            {"username": "alice", "display_name": "Alice", "links": {}},
            {},
        )
        result = fetch_viewer_identity(client)
        assert result.ok is True
        assert result.login == "alice"
        assert result.user_id is None  # Bitbucket has no simple int id


class TestProviderTranslation:
    def test_create_remote_repo_passes_workspace_through(self):
        p = BitbucketProvider()
        client = MagicMock(spec=BitbucketApiClient)
        client.request_json.return_value = (
            201,
            {
                "full_name": "myteam/proj",
                "links": {
                    "html": {"href": "x"},
                    "clone": [{"name": "https", "href": "https://x/proj.git"}],
                },
                "mainbranch": {"name": "main"},
            },
            {},
        )
        result = p.create_remote_repo(
            client, name="proj", private=True, workspace="myteam"
        )
        assert isinstance(result, RemoteRepoInfo)
        _, kwargs = client.request_json.call_args
        assert "myteam" in kwargs["url"]

    def test_list_repos_passes_workspace_through(self):
        p = BitbucketProvider()
        client = MagicMock(spec=BitbucketApiClient)
        client.request_json.return_value = (200, {"values": [], "next": None}, {})
        p.list_repos(client, workspace="myteam")
        args, kwargs = client.request_json.call_args
        assert "myteam" in args[1]
