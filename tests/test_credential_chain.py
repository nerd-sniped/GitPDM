# -*- coding: utf-8 -*-
"""
Tests for auth.credential_chain — Phase G1 credential resolution.

Covers: rung precedence, yield/miss/error semantics per rung, the
no-token-values-in-logs invariant, and headless backend detection.
"""

import pytest
from unittest.mock import MagicMock

from freecad_gitpdm.auth import credential_chain
from freecad_gitpdm.auth.credential_chain import (
    resolve_credential,
    resolve_env_credential,
    headless_backends_active,
    SOURCE_ENV_FILE,
    SOURCE_ENV,
    SOURCE_KEYRING,
)
from freecad_gitpdm.auth.oauth_device_flow import TokenResponse


SECRET_FILE_TOKEN = "ghp_file_secret_token_AAA111"
SECRET_ENV_TOKEN = "ghp_env_secret_token_BBB222"
SECRET_KEYRING_TOKEN = "ghp_keyring_secret_token_CCC333"


@pytest.fixture
def captured_logs(monkeypatch):
    """Capture all core.log output produced via the chain module."""
    messages = []
    from freecad_gitpdm.core import log

    for name in ("debug", "info", "warning", "error"):
        monkeypatch.setattr(log, name, lambda msg, _n=name: messages.append(str(msg)))
    return messages


def _keyring_store_with(token):
    store = MagicMock()
    store.load.return_value = token
    return store


def _keyring_token():
    return TokenResponse(
        access_token=SECRET_KEYRING_TOKEN,
        token_type="bearer",
        scope="repo",
    )


class TestPrecedence:
    def test_token_file_wins_over_env_and_keyring(self, tmp_path, captured_logs):
        token_file = tmp_path / "token.txt"
        token_file.write_text(SECRET_FILE_TOKEN + "\n", encoding="utf-8")
        environ = {
            "GITPDM_TOKEN_FILE": str(token_file),
            "GITPDM_TOKEN": SECRET_ENV_TOKEN,
        }
        store = _keyring_store_with(_keyring_token())

        resolved = resolve_credential(environ=environ, store_factory=lambda: store)

        assert resolved is not None
        assert resolved.source == SOURCE_ENV_FILE
        assert resolved.token.access_token == SECRET_FILE_TOKEN
        store.load.assert_not_called()

    def test_env_token_wins_over_keyring(self, captured_logs):
        environ = {"GITPDM_TOKEN": SECRET_ENV_TOKEN}
        store = _keyring_store_with(_keyring_token())

        resolved = resolve_credential(environ=environ, store_factory=lambda: store)

        assert resolved is not None
        assert resolved.source == SOURCE_ENV
        assert resolved.token.access_token == SECRET_ENV_TOKEN
        store.load.assert_not_called()

    def test_keyring_used_when_no_env(self, captured_logs):
        store = _keyring_store_with(_keyring_token())

        resolved = resolve_credential(
            host="github.com",
            account="octocat",
            environ={},
            store_factory=lambda: store,
        )

        assert resolved is not None
        assert resolved.source == SOURCE_KEYRING
        assert resolved.token.access_token == SECRET_KEYRING_TOKEN
        store.load.assert_called_once_with("github.com", "octocat")

    def test_all_rungs_miss_returns_none(self, captured_logs):
        store = _keyring_store_with(None)
        resolved = resolve_credential(environ={}, store_factory=lambda: store)
        assert resolved is None


class TestRungErrorSemantics:
    def test_unreadable_token_file_falls_through_to_env(self, tmp_path, captured_logs):
        environ = {
            "GITPDM_TOKEN_FILE": str(tmp_path / "does-not-exist.txt"),
            "GITPDM_TOKEN": SECRET_ENV_TOKEN,
        }

        resolved = resolve_credential(environ=environ, store_factory=MagicMock)

        assert resolved is not None
        assert resolved.source == SOURCE_ENV
        assert any("GITPDM_TOKEN_FILE" in m for m in captured_logs)

    def test_empty_token_file_falls_through(self, tmp_path, captured_logs):
        token_file = tmp_path / "empty.txt"
        token_file.write_text("", encoding="utf-8")
        environ = {
            "GITPDM_TOKEN_FILE": str(token_file),
            "GITPDM_TOKEN": SECRET_ENV_TOKEN,
        }

        resolved = resolve_credential(environ=environ, store_factory=MagicMock)

        assert resolved is not None
        assert resolved.source == SOURCE_ENV

    def test_keyring_error_falls_through_to_none(self, captured_logs):
        def broken_factory():
            raise OSError("no secret service daemon")

        resolved = resolve_credential(environ={}, store_factory=broken_factory)

        assert resolved is None
        assert any("falling through" in m for m in captured_logs)

    def test_keyring_load_error_falls_through_to_none(self, captured_logs):
        store = MagicMock()
        store.load.side_effect = OSError("dbus not available")

        resolved = resolve_credential(environ={}, store_factory=lambda: store)

        assert resolved is None


class TestInteractiveResolver:
    """Audit fix P1.3: resolve_credential() itself becomes the single
    entry point for the interactive rungs (device flow / PAT prompt),
    via an injected callable, when the first three rungs all miss."""

    def test_interactive_resolver_invoked_when_all_rungs_miss(self, captured_logs):
        store = _keyring_store_with(None)
        sentinel = credential_chain.ResolvedCredential(
            token=TokenResponse(
                access_token="ghp_from_device_flow", token_type="bearer", scope=""
            ),
            source=credential_chain.SOURCE_INTERACTIVE,
        )
        interactive = MagicMock(return_value=sentinel)

        resolved = resolve_credential(
            environ={},
            store_factory=lambda: store,
            interactive_resolver=interactive,
        )

        interactive.assert_called_once()
        assert resolved is sentinel

    def test_interactive_resolver_not_invoked_when_env_yields(self, captured_logs):
        interactive = MagicMock()

        resolved = resolve_credential(
            environ={"GITPDM_TOKEN": SECRET_ENV_TOKEN},
            store_factory=MagicMock,
            interactive_resolver=interactive,
        )

        interactive.assert_not_called()
        assert resolved.source == SOURCE_ENV

    def test_interactive_resolver_invoked_after_keyring_error(self, captured_logs):
        def broken_factory():
            raise OSError("no secret service daemon")

        interactive = MagicMock(return_value=None)

        resolved = resolve_credential(
            environ={},
            store_factory=broken_factory,
            interactive_resolver=interactive,
        )

        interactive.assert_called_once()
        assert resolved is None

    def test_omitting_interactive_resolver_preserves_prior_behavior(
        self, captured_logs
    ):
        """Headless callers (auth/check.py) that don't pass
        interactive_resolver must see exactly the old three-rung-only
        result: None on a full miss."""
        store = _keyring_store_with(None)
        resolved = resolve_credential(environ={}, store_factory=lambda: store)
        assert resolved is None


class TestNoTokensInLogs:
    """SECURITY invariant: no rung may log a token value."""

    def test_no_token_values_logged_on_any_path(self, tmp_path, captured_logs):
        token_file = tmp_path / "token.txt"
        token_file.write_text(SECRET_FILE_TOKEN, encoding="utf-8")

        # Exercise every yielding rung
        resolve_credential(
            environ={"GITPDM_TOKEN_FILE": str(token_file)},
            store_factory=MagicMock,
        )
        resolve_credential(
            environ={"GITPDM_TOKEN": SECRET_ENV_TOKEN}, store_factory=MagicMock
        )
        resolve_credential(
            environ={},
            store_factory=lambda: _keyring_store_with(_keyring_token()),
        )
        # And the error paths
        resolve_credential(
            environ={
                "GITPDM_TOKEN_FILE": str(tmp_path / "missing.txt"),
                "GITPDM_TOKEN": SECRET_ENV_TOKEN,
            },
            store_factory=MagicMock,
        )

        joined = "\n".join(captured_logs)
        for secret in (SECRET_FILE_TOKEN, SECRET_ENV_TOKEN, SECRET_KEYRING_TOKEN):
            assert secret not in joined


class TestHeadlessDetection:
    def test_inactive_with_empty_environ(self):
        assert headless_backends_active(environ={}) is False

    def test_active_with_token(self):
        assert headless_backends_active(environ={"GITPDM_TOKEN": "x"}) is True

    def test_active_with_token_file(self):
        assert headless_backends_active(environ={"GITPDM_TOKEN_FILE": "/x"}) is True

    def test_whitespace_only_is_inactive(self):
        assert headless_backends_active(environ={"GITPDM_TOKEN": "  "}) is False


class TestEnvCredentialProvider:
    def test_provider_defaults_to_github(self):
        resolved = resolve_env_credential(environ={"GITPDM_TOKEN": "tok"})
        assert resolved is not None
        assert resolved.token.provider == "github"

    def test_provider_from_env(self):
        resolved = resolve_env_credential(
            environ={"GITPDM_TOKEN": "tok", "GITPDM_PROVIDER": "gitlab"}
        )
        assert resolved is not None
        assert resolved.token.provider == "gitlab"

    def test_env_token_has_no_expiry(self):
        resolved = resolve_env_credential(environ={"GITPDM_TOKEN": "tok"})
        assert resolved is not None
        assert resolved.token.refresh_token is None
        assert resolved.token.expires_in is None

    def test_module_reference(self):
        # Guard against accidental removal of the public names other
        # modules import (git client, services).
        assert callable(credential_chain.headless_backends_active)
        assert callable(credential_chain.resolve_env_credential)
