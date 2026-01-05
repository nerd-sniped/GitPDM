"""
GitPDM Token Store Factory
Platform-aware factory for creating the appropriate token store implementation.
"""

from __future__ import annotations

import sys
from freecad.gitpdm.auth.token_store import TokenStore


def create_token_store() -> TokenStore:
    """
    Create the appropriate token store for the current platform.

    Returns:
        TokenStore: Platform-specific token store implementation

    Raises:
        OSError: If no token store is available for the current platform
    """
    if sys.platform == "win32":
        # Windows: Use Windows Credential Manager
        from freecad.gitpdm.auth.token_store_wincred import WindowsCredentialStore

        return WindowsCredentialStore()
    elif sys.platform == "darwin":
        # macOS: Use Keychain
        from freecad.gitpdm.auth.token_store_macos import MacOSKeychainStore

        return MacOSKeychainStore()
    elif sys.platform.startswith("linux"):
        # Linux: Use Secret Service API (GNOME Keyring, KWallet, etc.)
        from freecad.gitpdm.auth.token_store_linux import LinuxSecretServiceStore

        return LinuxSecretServiceStore()
    else:
        # Unknown platform
        from freecad.gitpdm.core import log

        log.error(f"Unsupported platform: {sys.platform}")
        raise OSError(f"No secure token storage available for platform: {sys.platform}")
