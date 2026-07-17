# -*- coding: utf-8 -*-
"""
GitPDM Token Store Factory
Platform-aware factory for creating the appropriate token store implementation.
"""

from __future__ import annotations

import sys
from freecad_gitpdm.auth.token_store import TokenStore


def _store_usable(store: TokenStore) -> bool:
    """
    Cheap availability probe for a platform store.

    Only consulted when the file backend is explicitly enabled
    (GITPDM_ALLOW_FILE_TOKENS=1), i.e., in headless environments where
    the OS credential service may be absent at runtime even though the
    store class constructs fine (e.g., Linux without a Secret Service
    daemon).
    """
    if getattr(store, "_available", True) is False:
        return False
    try:
        store.load("gitpdm.availability-probe.invalid", None)
    except Exception:
        return False
    return True


def create_token_store() -> TokenStore:
    """
    Create the appropriate token store for the current platform.

    When GITPDM_ALLOW_FILE_TOKENS=1 is set and the platform's OS
    credential store is unavailable, falls back to the file-based store
    (headless/container environments, R2.1). Without that flag the file
    backend is unreachable and behavior is unchanged from previous
    releases.

    Returns:
        TokenStore: Platform-specific token store implementation

    Raises:
        OSError: If no token store is available for the current platform
    """
    from freecad_gitpdm.auth.token_store_file import (
        FileTokenStore,
        file_tokens_allowed,
    )

    try:
        store = _create_platform_store()
    except OSError:
        if file_tokens_allowed():
            return FileTokenStore()
        raise

    if file_tokens_allowed() and not _store_usable(store):
        from freecad_gitpdm.core import log

        log.warning(
            "OS credential store unavailable; using file token store "
            "(GITPDM_ALLOW_FILE_TOKENS=1)"
        )
        return FileTokenStore()

    return store


def _create_platform_store() -> TokenStore:
    """Create the OS-keyring store for the current platform."""
    if sys.platform == "win32":
        # Windows: Use Windows Credential Manager
        from freecad_gitpdm.auth.token_store_wincred import WindowsCredentialStore

        return WindowsCredentialStore()
    elif sys.platform == "darwin":
        # macOS: Use Keychain
        from freecad_gitpdm.auth.token_store_macos import MacOSKeychainStore

        return MacOSKeychainStore()
    elif sys.platform.startswith("linux"):
        # Linux: Use Secret Service API (GNOME Keyring, KWallet, etc.)
        from freecad_gitpdm.auth.token_store_linux import LinuxSecretServiceStore

        return LinuxSecretServiceStore()
    else:
        # Unknown platform
        from freecad_gitpdm.core import log

        log.error(f"Unsupported platform: {sys.platform}")
        raise OSError(f"No secure token storage available for platform: {sys.platform}")
