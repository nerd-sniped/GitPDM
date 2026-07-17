# -*- coding: utf-8 -*-
"""
Tests for auth.token_store_file and the factory gating — Phase G1.

The critical invariant: the file backend is UNREACHABLE unless
GITPDM_ALLOW_FILE_TOKENS=1 is set (desktop-security invariant).
"""

import json
import os
import sys

import pytest

from freecad_gitpdm.auth import token_store_factory
from freecad_gitpdm.auth.oauth_device_flow import TokenResponse
from freecad_gitpdm.auth.token_store_file import (
    FileTokenStore,
    file_tokens_allowed,
    ALLOW_FILE_TOKENS_ENV,
)


def _token(access="ghp_file_store_test_token", provider="github"):
    return TokenResponse(
        access_token=access,
        token_type="bearer",
        scope="repo read:user",
        refresh_token="refresh_abc",
        expires_in=28800,
        obtained_at_utc="2026-07-16T12:00:00+00:00",
        provider=provider,
    )


ALLOWED = {ALLOW_FILE_TOKENS_ENV: "1"}


class TestGatingInvariant:
    def test_constructor_raises_without_flag(self, tmp_path):
        with pytest.raises(OSError):
            FileTokenStore(path=tmp_path / "credentials.json", environ={})

    def test_constructor_raises_with_wrong_flag_value(self, tmp_path):
        with pytest.raises(OSError):
            FileTokenStore(
                path=tmp_path / "credentials.json",
                environ={ALLOW_FILE_TOKENS_ENV: "true"},
            )

    def test_file_tokens_allowed_only_when_exactly_1(self):
        assert file_tokens_allowed({}) is False
        assert file_tokens_allowed({ALLOW_FILE_TOKENS_ENV: "0"}) is False
        assert file_tokens_allowed({ALLOW_FILE_TOKENS_ENV: "yes"}) is False
        assert file_tokens_allowed({ALLOW_FILE_TOKENS_ENV: "1"}) is True

    def test_factory_never_returns_file_store_without_flag(self, monkeypatch):
        """Even with the platform store broken, no flag means no file store."""
        monkeypatch.delenv(ALLOW_FILE_TOKENS_ENV, raising=False)

        def broken_platform_store():
            raise OSError("no platform store")

        monkeypatch.setattr(
            token_store_factory, "_create_platform_store", broken_platform_store
        )
        with pytest.raises(OSError):
            token_store_factory.create_token_store()

    def test_factory_falls_back_to_file_store_with_flag(self, monkeypatch):
        monkeypatch.setenv(ALLOW_FILE_TOKENS_ENV, "1")

        def broken_platform_store():
            raise OSError("no platform store")

        monkeypatch.setattr(
            token_store_factory, "_create_platform_store", broken_platform_store
        )
        store = token_store_factory.create_token_store()
        assert isinstance(store, FileTokenStore)

    def test_factory_prefers_working_platform_store_even_with_flag(self, monkeypatch):
        """The flag alone must not downgrade a user with a working keyring."""
        monkeypatch.setenv(ALLOW_FILE_TOKENS_ENV, "1")

        class WorkingStore:
            def load(self, host, account):
                return None

        working = WorkingStore()
        monkeypatch.setattr(
            token_store_factory, "_create_platform_store", lambda: working
        )
        store = token_store_factory.create_token_store()
        assert store is working

    def test_factory_falls_back_when_platform_store_unusable(self, monkeypatch):
        monkeypatch.setenv(ALLOW_FILE_TOKENS_ENV, "1")

        class DeadStore:
            def load(self, host, account):
                raise OSError("secret service daemon not running")

        monkeypatch.setattr(
            token_store_factory, "_create_platform_store", lambda: DeadStore()
        )
        store = token_store_factory.create_token_store()
        assert isinstance(store, FileTokenStore)


class TestRoundTrip:
    def test_save_load_round_trip(self, tmp_path):
        store = FileTokenStore(path=tmp_path / "credentials.json", environ=ALLOWED)
        token = _token()
        store.save("github.com", "octocat", token)

        loaded = store.load("github.com", "octocat")
        assert loaded is not None
        assert loaded.access_token == token.access_token
        assert loaded.refresh_token == token.refresh_token
        assert loaded.expires_in == token.expires_in
        assert loaded.obtained_at_utc == token.obtained_at_utc
        assert loaded.provider == "github"

    def test_provider_round_trip(self, tmp_path):
        store = FileTokenStore(path=tmp_path / "credentials.json", environ=ALLOWED)
        store.save("gitlab.com", None, _token(provider="gitlab"))
        loaded = store.load("gitlab.com", None)
        assert loaded is not None
        assert loaded.provider == "gitlab"

    def test_load_missing_returns_none(self, tmp_path):
        store = FileTokenStore(path=tmp_path / "credentials.json", environ=ALLOWED)
        assert store.load("github.com", "nobody") is None

    def test_host_only_fallback(self, tmp_path):
        """Token saved before the username was known is still found."""
        store = FileTokenStore(path=tmp_path / "credentials.json", environ=ALLOWED)
        store.save("github.com", None, _token())
        loaded = store.load("github.com", "octocat")
        assert loaded is not None

    def test_delete(self, tmp_path):
        store = FileTokenStore(path=tmp_path / "credentials.json", environ=ALLOWED)
        store.save("github.com", "octocat", _token())
        store.delete("github.com", "octocat")
        assert store.load("github.com", "octocat") is None

    def test_corrupt_file_raises_value_error(self, tmp_path):
        path = tmp_path / "credentials.json"
        path.write_text("{not json", encoding="utf-8")
        store = FileTokenStore(path=path, environ=ALLOWED)
        with pytest.raises(ValueError):
            store.load("github.com", None)

    def test_multiple_hosts_coexist(self, tmp_path):
        store = FileTokenStore(path=tmp_path / "credentials.json", environ=ALLOWED)
        store.save("github.com", None, _token(access="tok_gh"))
        store.save("gitlab.com", None, _token(access="tok_gl", provider="gitlab"))
        gh = store.load("github.com", None)
        gl = store.load("gitlab.com", None)
        assert gh is not None and gh.access_token == "tok_gh"
        assert gl is not None and gl.access_token == "tok_gl"

    def test_file_is_valid_json_on_disk(self, tmp_path):
        path = tmp_path / "credentials.json"
        store = FileTokenStore(path=path, environ=ALLOWED)
        store.save("github.com", None, _token())
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "GitPDM:github.com:oauth" in data

    @pytest.mark.skipif(
        sys.platform == "win32", reason="POSIX file modes not applicable"
    )
    def test_file_mode_0600(self, tmp_path):
        path = tmp_path / "credentials.json"
        store = FileTokenStore(path=path, environ=ALLOWED)
        store.save("github.com", None, _token())
        mode = os.stat(path).st_mode & 0o777
        assert mode == 0o600
