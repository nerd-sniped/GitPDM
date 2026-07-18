# -*- coding: utf-8 -*-
"""
Tests for core.settings.py's multi-provider connection settings
(save_provider_*/load_provider_*) and the GitHub backward-compat wrappers
that must keep using the exact same parameter-store keys as before.
"""

from freecad_gitpdm.core import settings


class TestProviderKeyPrefix:
    def test_known_providers_use_explicit_prefixes(self):
        assert settings._provider_key_prefix("github") == "GitHub"
        assert settings._provider_key_prefix("gitlab") == "GitLab"
        assert settings._provider_key_prefix("gitea") == "Gitea"
        assert settings._provider_key_prefix("bitbucket") == "Bitbucket"
        assert settings._provider_key_prefix("sourcehut") == "SourceHut"

    def test_unknown_provider_falls_back_to_capitalized(self):
        assert settings._provider_key_prefix("newhost") == "Newhost"


class TestProviderConnected:
    def test_save_writes_namespaced_key(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        settings.save_provider_connected("gitlab", True)
        param_group.SetBool.assert_called_once_with("GitLabConnected", True)

    def test_load_reads_namespaced_key(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        param_group.GetBool.return_value = True
        assert settings.load_provider_connected("gitlab") is True
        param_group.GetBool.assert_called_with("GitLabConnected", False)

    def test_different_providers_use_different_keys(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        settings.save_provider_connected("github", True)
        settings.save_provider_connected("gitlab", True)
        keys_used = [c.args[0] for c in param_group.SetBool.call_args_list]
        assert "GitHubConnected" in keys_used
        assert "GitLabConnected" in keys_used
        assert keys_used[0] != keys_used[1]


class TestProviderLogin:
    def test_save_and_load(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        settings.save_provider_login("bitbucket", "alice")
        param_group.SetString.assert_called_with("BitbucketLogin", "alice")

        param_group.GetString.return_value = "alice"
        assert settings.load_provider_login("bitbucket") == "alice"

    def test_empty_login_returns_none(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        param_group.GetString.return_value = ""
        assert settings.load_provider_login("bitbucket") is None


class TestProviderHost:
    def test_save_and_load_with_default(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        settings.save_provider_host("gitea", None, default_host="")
        param_group.SetString.assert_called_with("GiteaHost", "")

        param_group.GetString.return_value = "https://gitea.example.com"
        assert (
            settings.load_provider_host("gitea", default_host="")
            == "https://gitea.example.com"
        )


class TestProviderUserId:
    def test_save_int_and_load(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        settings.save_provider_user_id("gitlab", 42)
        param_group.SetString.assert_called_with("GitLabUserId", "42")

        param_group.GetString.return_value = "42"
        assert settings.load_provider_user_id("gitlab") == 42

    def test_save_none_clears(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        settings.save_provider_user_id("gitlab", None)
        param_group.SetString.assert_called_with("GitLabUserId", "")

    def test_load_unset_returns_none(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        param_group.GetString.return_value = ""
        assert settings.load_provider_user_id("gitlab") is None


class TestProviderLastApiError:
    def test_save_and_load(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        settings.save_provider_last_api_error("sourcehut", "UNAUTHORIZED", "expired")

        param_group.GetString.side_effect = lambda key, default="": {
            "SourceHutLastApiErrorCode": "UNAUTHORIZED",
            "SourceHutLastApiErrorMessage": "expired",
        }.get(key, default)

        assert settings.load_provider_last_api_error("sourcehut") == (
            "UNAUTHORIZED",
            "expired",
        )


class TestGitHubBackwardCompat:
    """GitHub's existing functions must use the exact same storage keys as
    before this refactor - no migration, zero behavior change."""

    def test_save_github_connected_uses_original_key(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        settings.save_github_connected(True)
        param_group.SetBool.assert_called_once_with("GitHubConnected", True)

    def test_save_github_login_uses_original_key(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        settings.save_github_login("alice")
        param_group.SetString.assert_called_with("GitHubLogin", "alice")

    def test_save_github_host_uses_original_key_and_default(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        settings.save_github_host(None)
        param_group.SetString.assert_called_with("GitHubHost", "github.com")

    def test_load_github_host_default(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        param_group.GetString.return_value = "github.com"
        assert settings.load_github_host() == "github.com"
        param_group.GetString.assert_called_with("GitHubHost", "github.com")

    def test_save_github_user_id_uses_original_key(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        settings.save_github_user_id(99)
        param_group.SetString.assert_called_with("GitHubUserId", "99")

    def test_save_last_verified_at_uses_original_key(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        settings.save_last_verified_at("2026-01-01T00:00:00Z")
        param_group.SetString.assert_called_with(
            "GitHubLastVerifiedAt", "2026-01-01T00:00:00Z"
        )

    def test_save_last_api_error_uses_original_keys(self, mock_freecad):
        param_group = mock_freecad.ParamGet.return_value
        settings.save_last_api_error("RATE_LIMITED", "slow down")
        param_group.SetString.assert_any_call("GitHubLastApiErrorCode", "RATE_LIMITED")
        param_group.SetString.assert_any_call("GitHubLastApiErrorMessage", "slow down")
