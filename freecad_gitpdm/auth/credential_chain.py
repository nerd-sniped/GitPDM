# -*- coding: utf-8 -*-
"""
GitPDM Credential Resolution Chain
Phase G1: Headless-capable credential resolution (R2.1).

Resolution precedence (non-interactive rungs, tried in order):

    GITPDM_TOKEN_FILE  >  GITPDM_TOKEN  >  keyring

Each rung either *yields* a credential, is *missing* (silent
fall-through), or *errors* (logged warning, fall-through — never a
crash). If every rung misses, resolution returns None and the caller
(UI layer) proceeds to the interactive rungs: device flow, then PAT
prompt.

SECURITY: token values must never appear in log output. Log sources and
paths, never contents.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from freecad_gitpdm.auth.oauth_device_flow import TokenResponse


ENV_TOKEN_FILE = "GITPDM_TOKEN_FILE"
ENV_TOKEN = "GITPDM_TOKEN"
ENV_PROVIDER = "GITPDM_PROVIDER"

SOURCE_ENV_FILE = "env-file"
SOURCE_ENV = "env"
SOURCE_KEYRING = "keyring"


@dataclass
class ResolvedCredential:
    """A credential plus which rung of the chain produced it."""

    token: TokenResponse
    source: str  # SOURCE_ENV_FILE | SOURCE_ENV | SOURCE_KEYRING


def headless_backends_active(environ=None) -> bool:
    """
    True when an environment-variable credential backend is configured.

    Used both by the chain itself and by callers that change policy in
    headless deployments (e.g., git credential bridging; later,
    recovery-branch auto-push per R2.5).
    """
    env = os.environ if environ is None else environ
    return bool(env.get(ENV_TOKEN_FILE, "").strip() or env.get(ENV_TOKEN, "").strip())


def _pat_token(value: str, environ) -> TokenResponse:
    """Wrap a raw PAT string in a TokenResponse. PATs carry no expiry."""
    provider = (environ.get(ENV_PROVIDER) or "github").strip() or "github"
    return TokenResponse(
        access_token=value,
        token_type="bearer",
        scope="",
        provider=provider,
    )


def resolve_env_credential(environ=None) -> Optional[ResolvedCredential]:
    """
    Resolve only the environment rungs (GITPDM_TOKEN_FILE, GITPDM_TOKEN).

    Returns None if both are missing or unusable.
    """
    from freecad_gitpdm.core import log

    env = os.environ if environ is None else environ

    # Rung 1: GITPDM_TOKEN_FILE
    token_file = env.get(ENV_TOKEN_FILE, "").strip()
    if token_file:
        try:
            with open(token_file, "r", encoding="utf-8") as f:
                value = f.read().strip()
        except OSError as e:
            log.warning(
                f"{ENV_TOKEN_FILE} is set but unreadable "
                f"({e.__class__.__name__}); falling through"
            )
            value = ""
        if value:
            log.debug(f"Credential resolved from {ENV_TOKEN_FILE}")
            return ResolvedCredential(_pat_token(value, env), SOURCE_ENV_FILE)
        elif token_file:
            log.warning(f"{ENV_TOKEN_FILE} points to an empty file; falling through")

    # Rung 2: GITPDM_TOKEN
    token_value = env.get(ENV_TOKEN, "").strip()
    if token_value:
        log.debug(f"Credential resolved from {ENV_TOKEN}")
        return ResolvedCredential(_pat_token(token_value, env), SOURCE_ENV)

    return None


def resolve_credential(
    host: str = "github.com",
    account: str | None = None,
    environ=None,
    store_factory=None,
) -> Optional[ResolvedCredential]:
    """
    Resolve a credential through the full non-interactive chain.

    Args:
        host: Git host the credential is for (keyring lookup key).
        account: Optional account name (keyring lookup key).
        environ: Override environment mapping (tests).
        store_factory: Callable returning a TokenStore (tests / services);
                       defaults to the platform factory.

    Returns:
        ResolvedCredential, or None if every rung missed (caller should
        proceed to device flow / PAT prompt).
    """
    from freecad_gitpdm.core import log

    resolved = resolve_env_credential(environ)
    if resolved is not None:
        return resolved

    # Rung 3: keyring (or file store when enabled and keyring absent)
    try:
        if store_factory is None:
            from freecad_gitpdm.auth.token_store_factory import create_token_store

            store_factory = create_token_store
        store = store_factory()
        token = store.load(host, account)
    except Exception as e:
        log.warning(
            f"Token store unavailable ({e.__class__.__name__}); falling through"
        )
        return None

    if token is not None and token.access_token:
        log.debug("Credential resolved from token store")
        return ResolvedCredential(token, SOURCE_KEYRING)

    return None
