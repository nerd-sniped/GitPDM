# -*- coding: utf-8 -*-
"""
GitPDM Credential Check CLI
Phase G1: Container smoke test for the credential resolution chain.

Usage (no FreeCAD required):

    python -m freecad_gitpdm.auth.check

Resolves the credential chain (GITPDM_TOKEN_FILE > GITPDM_TOKEN >
keyring) and verifies the token against the host API by fetching the
authenticated login. Exit code 0 on success, 1 on failure.

Environment:
    GITPDM_HOST              Git host (default: github.com)
    GITPDM_TOKEN_FILE        Path to a file containing a token
    GITPDM_TOKEN             Token value
    GITPDM_ALLOW_FILE_TOKENS Enable the file persistence backend
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


USER_AGENT = "GitPDM/1.0"


def _api_user_url(host: str) -> str:
    """API endpoint returning the authenticated user for a host."""
    if host in ("github.com", "www.github.com", "api.github.com"):
        return "https://api.github.com/user"
    # GitHub Enterprise convention; other providers come with G4.
    return f"https://{host}/api/v3/user"


def fetch_login(host: str, access_token: str, timeout_s: int = 10) -> str:
    """
    Fetch the authenticated login for a token.

    Raises:
        RuntimeError: with a user-facing message on any failure.
        (Never includes the token value.)
    """
    request = urllib.request.Request(
        _api_user_url(host),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"API request failed (HTTP {e.code})")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}")
    except json.JSONDecodeError:
        raise RuntimeError("Invalid response from host API")

    login = payload.get("login")
    if not login:
        raise RuntimeError("Host API response has no login field")
    return str(login)


def main(argv=None) -> int:
    from freecad_gitpdm.auth.credential_chain import resolve_credential

    host = os.environ.get("GITPDM_HOST", "").strip() or "github.com"

    resolved = resolve_credential(host=host)
    if resolved is None:
        print(
            "GitPDM auth check: FAILED — no credential resolved "
            "(GITPDM_TOKEN_FILE, GITPDM_TOKEN, and keyring all missed)"
        )
        return 1

    try:
        login = fetch_login(host, resolved.token.access_token)
    except RuntimeError as e:
        print(
            f"GitPDM auth check: FAILED — credential from '{resolved.source}' "
            f"did not authenticate: {e}"
        )
        return 1

    print(
        f"GitPDM auth check: OK — source={resolved.source} "
        f"provider={resolved.token.provider} host={host} login={login}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
