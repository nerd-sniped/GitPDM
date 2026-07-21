# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
GitPDM File-Based Token Store (headless environments)
Phase G1: Credential persistence without an OS keyring.

Stores tokens as JSON in ~/.config/GitPDM/credentials.json with mode 0600.
Intended for containers and other headless environments where no OS
credential service exists (see Dev_Docs/GITPDM_REQUIREMENTS.md R2.1).

SECURITY: This backend is gated behind the GITPDM_ALLOW_FILE_TOKENS=1
environment variable. Without the flag, constructing the store raises —
it must be unreachable so it can never silently downgrade a desktop
user's security. This invariant is asserted by tests.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from freecad_gitpdm.auth.token_store import TokenStore
from freecad_gitpdm.auth.oauth_device_flow import TokenResponse
from freecad_gitpdm.auth.keys import credential_target_name


ALLOW_FILE_TOKENS_ENV = "GITPDM_ALLOW_FILE_TOKENS"


def file_tokens_allowed(environ=None) -> bool:
    """Return True if the file token backend is explicitly enabled."""
    env = os.environ if environ is None else environ
    return env.get(ALLOW_FILE_TOKENS_ENV, "") == "1"


def default_credentials_path() -> Path:
    """Default credentials file location (all platforms)."""
    return Path.home() / ".config" / "GitPDM" / "credentials.json"


class FileTokenStore(TokenStore):
    """
    Token storage in a JSON file, for keyring-less environments.

    The file maps credential target names (see auth/keys.py) to the same
    per-field JSON dict the OS-keyring stores use, so tokens are portable
    between backends.
    """

    def __init__(self, path: str | os.PathLike | None = None, environ=None):
        """
        Args:
            path: Override the credentials file location (mainly for tests).
            environ: Override environment mapping (mainly for tests).

        Raises:
            OSError: If GITPDM_ALLOW_FILE_TOKENS=1 is not set.
        """
        if not file_tokens_allowed(environ):
            raise OSError(
                "File token storage is disabled. Set "
                f"{ALLOW_FILE_TOKENS_ENV}=1 to enable it (headless "
                "environments only)."
            )
        self._path = Path(path) if path is not None else default_credentials_path()

    def _read_all(self) -> dict:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            raise ValueError(f"Credentials file is corrupted: {e}")
        if not isinstance(data, dict):
            raise ValueError("Credentials file has unexpected structure")
        return data

    def _write_all(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self._path.parent, 0o700)
        except OSError:
            pass  # best effort on platforms without POSIX modes
        tmp_path = self._path.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        try:
            os.chmod(tmp_path, 0o600)
        except OSError:
            pass
        os.replace(tmp_path, self._path)
        try:
            os.chmod(self._path, 0o600)
        except OSError:
            pass

    def save(self, host: str, account: str | None, token: TokenResponse) -> None:
        from freecad_gitpdm.core import log

        target_name = credential_target_name(host, account)
        data = self._read_all()
        data[target_name] = token.to_dict()
        self._write_all(data)
        log.debug(f"Token stored for {target_name} in credentials file")

    def load(self, host: str, account: str | None) -> TokenResponse | None:
        from freecad_gitpdm.core import log

        data = self._read_all()

        # Primary lookup, then host-only fallback (same migration
        # behaviour as the OS-keyring stores).
        targets = [credential_target_name(host, account)]
        if account:
            fallback = credential_target_name(host, None)
            if fallback not in targets:
                targets.append(fallback)

        for target_name in targets:
            token_data = data.get(target_name)
            if token_data is None:
                continue
            log.debug(f"Token loaded for {target_name} from credentials file")
            return TokenResponse.from_dict(token_data)
        return None

    def delete(self, host: str, account: str | None) -> None:
        from freecad_gitpdm.core import log

        data = self._read_all()
        targets = [credential_target_name(host, account)]
        if account:
            targets.append(credential_target_name(host, None))

        removed = False
        for target_name in targets:
            if target_name in data:
                del data[target_name]
                removed = True
                log.debug(f"Token deleted for {target_name} from credentials file")
        if removed:
            self._write_all(data)
