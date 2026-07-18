# -*- coding: utf-8 -*-
"""
Tests for the SourceHut provider (GraphQL, PAT auth).

Unlike the other three new providers, this one's exact schema (mutation/
query field names) could not be live-verified — see
providers/sourcehut/__init__.py. These tests cover the plumbing (request
construction, error classification, response parsing against the
documented-but-unverified shape) so a schema mismatch would show up as a
clear, well-defined failure rather than silent wrongness; they do not
prove the schema itself is correct.
"""

from unittest.mock import MagicMock, patch

import pytest

from freecad_gitpdm.providers.sourcehut.provider import SourceHutProvider
from freecad_gitpdm.providers.sourcehut.api_client import SourceHutApiClient
from freecad_gitpdm.providers.sourcehut.errors import SourceHutApiError
from freecad_gitpdm.providers.sourcehut.create_repo import (
    CreateRepoRequest,
    create_user_repo,
)
from freecad_gitpdm.providers.sourcehut.repos import list_repos
from freecad_gitpdm.providers.sourcehut.identity import fetch_viewer_identity
from freecad_gitpdm.providers.base import RemoteRepoInfo, ViewerIdentity, RepoInfo


class TestSourceHutProvider:
    def test_capabilities(self):
        caps = SourceHutProvider.capabilities
        assert caps.supports_device_flow is False
        assert caps.supports_repo_creation is True
        assert caps.requires_manual_token is True
        assert caps.requires_host_url is False
        assert caps.requires_workspace is False

    def test_build_api_client(self):
        client = SourceHutProvider().build_api_client("tok")
        assert isinstance(client, SourceHutApiClient)
        assert client._base_url == "https://git.sr.ht/query"


class TestSourceHutApiClient:
    def test_resolve_url_always_returns_single_endpoint(self):
        client = SourceHutApiClient("tok")
        assert client._resolve_url("/anything") == "https://git.sr.ht/query"
        assert client._resolve_url("") == "https://git.sr.ht/query"
        assert client._resolve_url("whatever") == "https://git.sr.ht/query"

    def test_auth_header_is_bearer(self):
        client = SourceHutApiClient("secrettok")
        assert client._auth_headers() == {"Authorization": "Bearer secrettok"}

    def test_no_token_no_auth_header(self):
        assert SourceHutApiClient("")._auth_headers() == {}

    @patch("freecad_gitpdm.providers.shared.http_client.request.urlopen")
    def test_graphql_success_returns_data(self, mock_urlopen):
        import json as jsonlib

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.headers.items.return_value = []
        mock_resp.read.return_value = jsonlib.dumps(
            {"data": {"me": {"canonicalName": "~alice"}}}
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = SourceHutApiClient("tok")
        data = client.graphql("query { me { canonicalName } }")
        assert data == {"me": {"canonicalName": "~alice"}}

    @patch("freecad_gitpdm.providers.shared.http_client.request.urlopen")
    def test_graphql_errors_array_raises_even_on_200(self, mock_urlopen):
        import json as jsonlib

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.headers.items.return_value = []
        mock_resp.read.return_value = jsonlib.dumps(
            {
                "errors": [
                    {
                        "message": "name already taken",
                        "extensions": {"code": "ERR_CONFLICT"},
                    }
                ]
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = SourceHutApiClient("tok")
        with pytest.raises(SourceHutApiError, match="name already taken"):
            client.graphql('mutation { createRepository(name: "x") { id } }')


class TestSourceHutApiError:
    def test_401(self):
        assert SourceHutApiError.from_http_error(401).code == "UNAUTHORIZED"

    def test_graphql_errors_extraction(self):
        err = SourceHutApiError.from_graphql_errors(
            [{"message": "boom", "extensions": {"code": "ERR_X"}}]
        )
        assert err.code == "ERR_X"
        assert err.message == "boom"

    def test_graphql_errors_empty_list_falls_back(self):
        err = SourceHutApiError.from_graphql_errors([])
        assert err.code == "UNKNOWN"


class TestCreateRepo:
    def test_invalid_name_rejected(self):
        client = MagicMock(spec=SourceHutApiClient)
        with pytest.raises(SourceHutApiError):
            create_user_repo(client, CreateRepoRequest(name="bad name!", private=True))

    def test_visibility_mapping(self):
        client = MagicMock(spec=SourceHutApiClient)
        client.graphql.return_value = {
            "createRepository": {
                "name": "myproj",
                "owner": {"canonicalName": "~alice"},
            }
        }
        create_user_repo(client, CreateRepoRequest(name="myproj", private=True))
        variables = client.graphql.call_args[0][1]
        assert variables["visibility"] == "PRIVATE"

        client.graphql.reset_mock()
        create_user_repo(client, CreateRepoRequest(name="myproj", private=False))
        variables = client.graphql.call_args[0][1]
        assert variables["visibility"] == "PUBLIC"

    def test_success_builds_sr_ht_style_urls(self):
        client = MagicMock(spec=SourceHutApiClient)
        client.graphql.return_value = {
            "createRepository": {
                "name": "myproj",
                "owner": {"canonicalName": "~alice"},
            }
        }
        info = create_user_repo(client, CreateRepoRequest(name="myproj", private=False))
        assert info.full_name == "~alice/myproj"
        assert info.clone_url == "https://git.sr.ht/~alice/myproj"
        assert info.html_url == info.clone_url

    def test_incomplete_response_raises(self):
        client = MagicMock(spec=SourceHutApiClient)
        client.graphql.return_value = {"createRepository": {"name": ""}}
        with pytest.raises(SourceHutApiError):
            create_user_repo(client, CreateRepoRequest(name="myproj", private=True))


class TestListRepos:
    def test_single_page(self):
        client = MagicMock(spec=SourceHutApiClient)
        client.graphql.return_value = {
            "me": {
                "repositories": {
                    "cursor": None,
                    "results": [
                        {
                            "name": "proj1",
                            "visibility": "PRIVATE",
                            "updated": "2026-01-01T00:00:00Z",
                            "owner": {"canonicalName": "~alice"},
                        }
                    ],
                }
            }
        }
        repos = list_repos(client, use_cache=False)
        assert len(repos) == 1
        assert isinstance(repos[0], RepoInfo)
        assert repos[0].owner == "~alice"
        assert repos[0].private is True
        assert repos[0].clone_url == "https://git.sr.ht/~alice/proj1"

    def test_pagination_follows_cursor(self):
        client = MagicMock(spec=SourceHutApiClient)
        client.graphql.side_effect = [
            {"me": {"repositories": {"cursor": "abc123", "results": []}}},
            {"me": {"repositories": {"cursor": None, "results": []}}},
        ]
        list_repos(client, use_cache=False)
        assert client.graphql.call_count == 2
        second_variables = client.graphql.call_args_list[1][0][1]
        assert second_variables == {"cursor": "abc123"}

    def test_bad_entry_skipped_not_fatal(self):
        client = MagicMock(spec=SourceHutApiClient)
        client.graphql.return_value = {
            "me": {
                "repositories": {
                    "cursor": None,
                    "results": [
                        None,
                        {
                            "name": "ok",
                            "visibility": "PUBLIC",
                            "owner": {"canonicalName": "~alice"},
                        },
                    ],
                }
            }
        }
        repos = list_repos(client, use_cache=False)
        assert len(repos) == 1


class TestFetchIdentity:
    def test_success_uses_canonical_name(self):
        client = MagicMock(spec=SourceHutApiClient)
        client.graphql.return_value = {"me": {"canonicalName": "~alice"}}
        result = fetch_viewer_identity(client)
        assert result.ok is True
        assert result.login == "~alice"

    def test_no_me_data_is_not_ok(self):
        client = MagicMock(spec=SourceHutApiClient)
        client.graphql.return_value = {"me": None}
        result = fetch_viewer_identity(client)
        assert result.ok is False

    def test_error_propagates(self):
        client = MagicMock(spec=SourceHutApiClient)
        client.graphql.side_effect = SourceHutApiError.from_http_error(401)
        result = fetch_viewer_identity(client)
        assert result.ok is False
        assert result.error_code == "UNAUTHORIZED"


class TestProviderTranslation:
    def test_create_remote_repo_maps_to_neutral_shape(self):
        p = SourceHutProvider()
        client = MagicMock(spec=SourceHutApiClient)
        client.graphql.return_value = {
            "createRepository": {"name": "proj", "owner": {"canonicalName": "~alice"}}
        }
        result = p.create_remote_repo(client, name="proj", private=True)
        assert isinstance(result, RemoteRepoInfo)

    def test_fetch_identity_maps_to_neutral_shape(self):
        p = SourceHutProvider()
        client = MagicMock(spec=SourceHutApiClient)
        client.graphql.return_value = {"me": {"canonicalName": "~alice"}}
        result = p.fetch_identity(client)
        assert isinstance(result, ViewerIdentity)
