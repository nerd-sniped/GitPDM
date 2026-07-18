# -*- coding: utf-8 -*-
"""
Tests for freecad_gitpdm.providers.shared (multi-provider support): the
generic HTTP client, error shape, cache, and rate limiter, plus the
providers/base.py additions and backward-compat shims in providers/github/.
"""

from unittest.mock import MagicMock, patch

from freecad_gitpdm.providers.base import (
    BaseProvider,
    GenericProvider,
    ProviderCapabilities,
    RepoInfo,
)
from freecad_gitpdm.providers.shared.errors import (
    ProviderApiError,
    ProviderApiNetworkError,
)
from freecad_gitpdm.providers.shared.cache import ApiCache, get_api_cache
from freecad_gitpdm.providers.shared.rate_limiter import RateLimiter
from freecad_gitpdm.providers.shared.http_client import BaseApiClient


class TestProviderApiError:
    def test_from_http_error_401(self):
        err = ProviderApiError.from_http_error(401)
        assert err.code == "UNAUTHORIZED"
        assert err.status == 401

    def test_from_http_error_429_with_retry_after(self):
        err = ProviderApiError.from_http_error(429, {"Retry-After": "42"})
        assert err.code == "RATE_LIMITED"
        assert err.retry_after_s == 42

    def test_from_http_error_500(self):
        err = ProviderApiError.from_http_error(500)
        assert err.code == "NETWORK"

    def test_from_http_error_unknown_status(self):
        err = ProviderApiError.from_http_error(418)
        assert err.code == "UNKNOWN"
        assert err.status == 418

    def test_from_network_error_timeout(self):
        err = ProviderApiError.from_network_error("Connection timeout occurred")
        assert err.code == "TIMEOUT"

    def test_str_returns_message(self):
        err = ProviderApiError(code="X", message="human readable")
        assert str(err) == "human readable"

    def test_network_error_subclass(self):
        err = ProviderApiNetworkError("dns failure")
        assert isinstance(err, ProviderApiError)
        assert err.code == "NETWORK"


class TestApiCache:
    def test_set_and_get(self):
        cache = ApiCache(ttl_seconds=60)
        cache.set("gitlab.com", "alice", "repos_list", ["repo1"])
        data, hit = cache.get("gitlab.com", "alice", "repos_list")
        assert hit is True
        assert data == ["repo1"]

    def test_different_hosts_dont_collide(self):
        cache = ApiCache(ttl_seconds=60)
        cache.set("github.com", "alice", "repos_list", ["gh-repo"])
        cache.set("gitlab.com", "alice", "repos_list", ["gl-repo"])
        gh_data, _ = cache.get("github.com", "alice", "repos_list")
        gl_data, _ = cache.get("gitlab.com", "alice", "repos_list")
        assert gh_data == ["gh-repo"]
        assert gl_data == ["gl-repo"]

    def test_bypass(self):
        cache = ApiCache(ttl_seconds=60)
        cache.set("gitlab.com", "alice", "repos_list", ["repo1"])
        cache.set_bypass(True)
        _, hit = cache.get("gitlab.com", "alice", "repos_list")
        assert hit is False

    def test_global_singleton_is_shared(self):
        assert get_api_cache() is get_api_cache()


class TestRateLimiterProviderIsolation:
    def test_different_provider_prefixes_dont_share_buckets(self):
        limiter = RateLimiter.get_instance()
        # Exhaust one provider's user bucket; a differently-prefixed user_id
        # for another provider must be unaffected.
        user_a = "gitlab:test-user-a"
        user_b = "bitbucket:test-user-a"
        for _ in range(RateLimiter.PER_USER_CAPACITY):
            limiter.can_proceed(user_id=user_a)
        # user_a's bucket should now be exhausted (or very low); user_b's
        # independent bucket should still allow a request.
        assert limiter.can_proceed(user_id=user_b) is True


class _FakeError(ProviderApiError):
    pass


class _FakeClient(BaseApiClient):
    provider_id = "fake"
    error_cls = ProviderApiError

    def _auth_headers(self):
        if self._token:
            return {"PRIVATE-TOKEN": self._token}
        return {}


class TestBaseApiClient:
    def test_resolve_url_absolute_path(self):
        client = _FakeClient("https://gitlab.example.com/api/v4", "tok")
        assert (
            client._resolve_url("/projects")
            == "https://gitlab.example.com/api/v4/projects"
        )

    def test_resolve_url_full_url_passthrough(self):
        client = _FakeClient("https://gitlab.example.com/api/v4", "tok")
        assert (
            client._resolve_url("https://other.example.com/x")
            == "https://other.example.com/x"
        )

    def test_auth_header_override(self):
        client = _FakeClient("https://gitlab.example.com/api/v4", "secrettoken")
        assert client._auth_headers() == {"PRIVATE-TOKEN": "secrettoken"}

    def test_user_id_prefixed_with_provider_id(self):
        client = _FakeClient("https://x.example.com", "tok")
        assert client._user_id.startswith("fake:")

    @patch("freecad_gitpdm.providers.shared.http_client.request.urlopen")
    def test_successful_request_returns_parsed_json(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.headers.items.return_value = [("Content-Type", "application/json")]
        mock_resp.read.return_value = b'{"ok": true}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = _FakeClient("https://gitlab.example.com/api/v4", "tok")
        status, js, headers = client.request_json(
            "GET", "/user", headers=None, body=None, timeout_s=5
        )
        assert status == 200
        assert js == {"ok": True}

    @patch("freecad_gitpdm.providers.shared.http_client.request.urlopen")
    def test_401_raises_no_retry(self, mock_urlopen):
        import urllib.error

        http_err = urllib.error.HTTPError(
            url="https://x", code=401, msg="Unauthorized", hdrs=None, fp=None
        )
        http_err.headers = {}
        mock_urlopen.side_effect = http_err

        client = _FakeClient("https://gitlab.example.com/api/v4", "tok")
        try:
            client.request_json("GET", "/user", headers=None, body=None, timeout_s=5)
            assert False, "expected ProviderApiError"
        except ProviderApiError as e:
            assert e.code == "UNAUTHORIZED"
        # Only one urlopen call - 401 is in NO_RETRY_CODES.
        assert mock_urlopen.call_count == 1


class TestProviderBaseAdditions:
    def test_base_provider_list_repos_raises(self):
        provider = BaseProvider()
        try:
            provider.list_repos(api_client=None)
            assert False, "expected NotImplementedError"
        except NotImplementedError:
            pass

    def test_generic_provider_display_name_and_flags(self):
        provider = GenericProvider()
        assert provider.capabilities.requires_manual_token is False
        assert provider.capabilities.requires_host_url is False

    def test_repo_info_fields(self):
        info = RepoInfo(
            owner="alice",
            name="proj",
            full_name="alice/proj",
            private=True,
            default_branch="main",
            clone_url="https://example.com/alice/proj.git",
            updated_at="2026-01-01T00:00:00Z",
        )
        assert info.owner == "alice"

    def test_capabilities_new_flags_default_false(self):
        caps = ProviderCapabilities()
        assert caps.requires_manual_token is False
        assert caps.requires_host_url is False
        assert caps.requires_workspace is False


class TestGitHubBackwardCompatShims:
    def test_github_cache_shim_returns_shared_singleton(self):
        from freecad_gitpdm.providers.github.cache import get_github_api_cache

        assert get_github_api_cache() is get_api_cache()

    def test_github_rate_limiter_shim_is_same_class(self):
        from freecad_gitpdm.providers.github.rate_limiter import (
            RateLimiter as ShimRateLimiter,
        )

        assert ShimRateLimiter is RateLimiter

    def test_github_repos_repoinfo_is_shared_dataclass(self):
        from freecad_gitpdm.providers.github.repos import RepoInfo as GHRepoInfo

        assert GHRepoInfo is RepoInfo

    def test_github_provider_has_display_name_and_list_repos(self):
        from freecad_gitpdm.providers.github.provider import GitHubProvider

        provider = GitHubProvider()
        assert provider.display_name == "GitHub"
        assert hasattr(provider, "list_repos")
