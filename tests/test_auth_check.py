# -*- coding: utf-8 -*-
"""
Tests for auth.check — Phase G1 CLI credential smoke test.

Also asserts the refresh path works end-to-end with a fake expiring
token (G1 acceptance criterion).
"""

import io
import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from freecad_gitpdm.auth import check
from freecad_gitpdm.auth import token_refresh
from freecad_gitpdm.auth.oauth_device_flow import TokenResponse


def _fake_urlopen_json(payload):
    """Build a urlopen replacement returning the given JSON payload."""
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    opener = MagicMock()
    opener.return_value.__enter__.return_value = response
    return opener


class TestCheckCli:
    def test_ok_with_env_token(self, monkeypatch, capsys):
        monkeypatch.setenv("GITPDM_TOKEN", "ghp_check_token_xyz")
        monkeypatch.delenv("GITPDM_TOKEN_FILE", raising=False)
        monkeypatch.delenv("GITPDM_HOST", raising=False)

        with patch.object(
            check.urllib.request,
            "urlopen",
            _fake_urlopen_json({"login": "octocat"}),
        ):
            rc = check.main()

        out = capsys.readouterr().out
        assert rc == 0
        assert "OK" in out
        assert "login=octocat" in out
        assert "source=env" in out
        # SECURITY: token value never printed
        assert "ghp_check_token_xyz" not in out

    def test_fails_with_no_credential(self, monkeypatch, capsys):
        monkeypatch.delenv("GITPDM_TOKEN", raising=False)
        monkeypatch.delenv("GITPDM_TOKEN_FILE", raising=False)

        # Force the chain to miss so the test never touches the real
        # OS keyring on the machine running the suite.
        from freecad_gitpdm.auth import credential_chain

        monkeypatch.setattr(
            credential_chain,
            "resolve_credential",
            lambda **kwargs: None,
        )

        rc = check.main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "FAILED" in out

    def test_fails_on_http_error(self, monkeypatch, capsys):
        monkeypatch.setenv("GITPDM_TOKEN", "ghp_bad_token")

        import urllib.error

        def raise_http(*args, **kwargs):
            raise urllib.error.HTTPError(
                "https://api.github.com/user", 401, "Unauthorized", {}, io.BytesIO()
            )

        with patch.object(check.urllib.request, "urlopen", raise_http):
            rc = check.main()

        out = capsys.readouterr().out
        assert rc == 1
        assert "FAILED" in out
        assert "401" in out
        assert "ghp_bad_token" not in out

    def test_enterprise_host_url(self):
        assert (
            check._api_user_url("github.example.com")
            == "https://github.example.com/api/v3/user"
        )
        assert check._api_user_url("github.com") == "https://api.github.com/user"


class TestRefreshPathWithFakeExpiringToken:
    """G1 acceptance: refresh path exercised with a fake expiring token."""

    def _expiring_token(self):
        obtained = datetime.now(timezone.utc) - timedelta(hours=8)
        return TokenResponse(
            access_token="ghp_expired_token",
            token_type="bearer",
            scope="repo",
            refresh_token="ghr_refresh_token",
            expires_in=28800,  # 8 hours, i.e., expired just now
            obtained_at_utc=obtained.isoformat(),
        )

    def test_expiring_token_is_detected(self):
        assert token_refresh.is_token_expired(self._expiring_token()) is True

    def test_env_pat_never_expires(self):
        pat = TokenResponse(access_token="ghp_pat", token_type="bearer", scope="")
        assert token_refresh.is_token_expired(pat) is False

    def test_past_expires_at_triggers_refresh(self):
        """Audit fix P0.1 acceptance: a credential with a past `expires_at`
        (the field itself, not the legacy obtained_at_utc+expires_in path)
        is detected as expired."""
        token = TokenResponse(
            access_token="ghp_expired",
            token_type="bearer",
            scope="repo",
            refresh_token="ghr_refresh",
            expires_at=time.time() - 60,
        )
        assert token_refresh.is_token_expired(token) is True

    def test_future_expires_at_outside_window_skips_refresh(self):
        """Audit fix P0.1 acceptance: a future `expires_at` well outside the
        5-minute refresh buffer is treated as still valid."""
        token = TokenResponse(
            access_token="ghp_fresh",
            token_type="bearer",
            scope="repo",
            expires_at=time.time() + 3600,
        )
        assert token_refresh.is_token_expired(token) is False

    def test_ensure_fresh_token_skips_refresh_for_future_expires_at(self):
        token = TokenResponse(
            access_token="ghp_fresh",
            token_type="bearer",
            scope="repo",
            refresh_token="ghr_refresh",
            expires_at=time.time() + 3600,
        )
        with patch.object(token_refresh.urllib.request, "urlopen") as mock_urlopen:
            ok, returned, msg = token_refresh.ensure_fresh_token(
                token, client_id="client123"
            )

        mock_urlopen.assert_not_called()
        assert ok is True
        assert returned is token

    def test_ensure_fresh_token_refreshes(self):
        refreshed_payload = {
            "access_token": "ghp_new_token",
            "token_type": "bearer",
            "scope": "repo",
            "refresh_token": "ghr_new_refresh",
            "expires_in": 28800,
        }
        with patch.object(
            token_refresh.urllib.request,
            "urlopen",
            _fake_urlopen_json(refreshed_payload),
        ):
            ok, new_token, msg = token_refresh.ensure_fresh_token(
                self._expiring_token(), client_id="client123"
            )

        assert ok is True
        assert new_token is not None
        assert new_token.access_token == "ghp_new_token"

    def test_failed_refresh_degrades_to_reauth_message(self):
        import urllib.error

        def raise_url_error(*args, **kwargs):
            raise urllib.error.URLError("network down")

        with patch.object(token_refresh.urllib.request, "urlopen", raise_url_error):
            ok, token, msg = token_refresh.ensure_fresh_token(
                self._expiring_token(), client_id="client123"
            )

        assert ok is False
        assert "sign in again" in msg.lower()
