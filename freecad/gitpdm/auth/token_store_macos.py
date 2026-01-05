"""
GitPDM macOS Keychain Token Store
Sprint OAUTH-1: Secure token storage using macOS Keychain

This module implements TokenStore for macOS using the keyring library,
which provides a Pythonic interface to the macOS Keychain.
"""

from __future__ import annotations

import json
from freecad.gitpdm.auth.token_store import TokenStore
from freecad.gitpdm.auth.oauth_device_flow import TokenResponse
from freecad.gitpdm.auth.keys import credential_target_name


class MacOSKeychainStore(TokenStore):
    """
    Secure token storage using macOS Keychain.

    Uses the keyring library which provides cross-platform access to
    system credential storage. On macOS, this uses the Keychain API.

    Requires: keyring library (usually pre-installed with Python on macOS)
    """

    def __init__(self):
        """Initialize Keychain access via keyring library."""
        self._available = False
        self._service_name = "freecad-gitpdm"

        try:
            import keyring

            # Test that keyring is functional
            backend = keyring.get_keyring()
            backend_name = backend.__class__.__name__

            # Verify we have a real keychain backend (not the fail keyring)
            if "fail" in backend_name.lower() or "null" in backend_name.lower():
                from freecad.gitpdm.core import log

                log.warning(
                    f"Keyring backend is not functional: {backend_name}. "
                    "Keychain access not available."
                )
                self._available = False
            else:
                self._keyring = keyring
                self._available = True
        except Exception as e:
            from freecad.gitpdm.core import log

            log.warning(f"macOS Keychain not available: {e}")
            self._available = False

    def save(self, host: str, account: str | None, token: TokenResponse) -> None:
        """
        Save token to macOS Keychain.

        Args:
            host: GitHub host
            account: GitHub username (optional)
            token: TokenResponse to store

        Raises:
            OSError: If keychain storage operation fails
        """
        if not self._available:
            from freecad.gitpdm.core import log

            log.error("macOS Keychain not available")
            raise OSError("macOS Keychain not available on this system")

        from freecad.gitpdm.core import log

        target_name = credential_target_name(host, account)

        # Serialize token to JSON
        token_data = {
            "access_token": token.access_token,
            "token_type": token.token_type,
            "scope": token.scope,
            "refresh_token": token.refresh_token,
            "expires_in": token.expires_in,
            "refresh_token_expires_in": token.refresh_token_expires_in,
            "obtained_at_utc": token.obtained_at_utc,
        }
        token_json = json.dumps(token_data)

        log.debug(f"Storing token for {target_name} in macOS Keychain")

        try:
            # Store in keychain using target_name as the username
            # and our service name as the service
            self._keyring.set_password(self._service_name, target_name, token_json)
            log.debug(f"Token stored successfully for {target_name}")
        except Exception as e:
            log.error(f"Failed to store token in Keychain: {e}")
            raise OSError(f"Failed to store token in macOS Keychain: {e}")

    def load(self, host: str, account: str | None) -> TokenResponse | None:
        """
        Load token from macOS Keychain.

        Args:
            host: GitHub host
            account: GitHub username (optional)

        Returns:
            TokenResponse or None if not found

        Raises:
            OSError: If keychain lookup fails
            ValueError: If stored data is invalid
        """
        if not self._available:
            from freecad.gitpdm.core import log

            log.debug("macOS Keychain not available")
            return None

        from freecad.gitpdm.core import log

        target_name = credential_target_name(host, account)

        log.debug(f"Loading token for {target_name} from macOS Keychain")

        try:
            # Try to load the token
            token_json = self._keyring.get_password(self._service_name, target_name)

            if token_json is None:
                log.debug(f"Token not found for {target_name}")

                # Fallback: try host-only key if account was provided
                if account:
                    fallback_target = credential_target_name(host, None)
                    if fallback_target != target_name:
                        token_json = self._keyring.get_password(
                            self._service_name, fallback_target
                        )
                        if token_json is None:
                            return None
                    else:
                        return None
                else:
                    return None

            # Parse the token JSON
            token_data = json.loads(token_json)

            log.debug(f"Token loaded successfully for {target_name}")

            return TokenResponse(
                access_token=token_data.get("access_token", ""),
                token_type=token_data.get("token_type", "bearer"),
                scope=token_data.get("scope", ""),
                refresh_token=token_data.get("refresh_token"),
                expires_in=token_data.get("expires_in"),
                refresh_token_expires_in=token_data.get("refresh_token_expires_in"),
                obtained_at_utc=token_data.get("obtained_at_utc", ""),
            )

        except json.JSONDecodeError as e:
            log.error(f"Failed to parse stored token: {e}")
            raise ValueError(f"Stored token data is invalid: {e}")
        except Exception as e:
            log.error(f"Failed to load token from Keychain: {e}")
            raise OSError(f"Failed to load token from macOS Keychain: {e}")

    def delete(self, host: str, account: str | None) -> None:
        """
        Delete token from macOS Keychain.

        Args:
            host: GitHub host
            account: GitHub username (optional)

        Raises:
            OSError: If keychain deletion fails
        """
        if not self._available:
            from freecad.gitpdm.core import log

            log.error("macOS Keychain not available")
            raise OSError("macOS Keychain not available on this system")

        from freecad.gitpdm.core import log

        target_name = credential_target_name(host, account)

        log.debug(f"Deleting token for {target_name} from macOS Keychain")

        try:
            # Try to delete the primary token
            self._keyring.delete_password(self._service_name, target_name)
            log.debug(f"Token deleted successfully for {target_name}")
        except self._keyring.errors.PasswordDeleteError:
            # Token not found - this is not an error
            log.debug(f"Token not found for {target_name}")
        except Exception as e:
            log.error(f"Failed to delete token from Keychain: {e}")
            raise OSError(f"Failed to delete token from macOS Keychain: {e}")

        # Also try to delete fallback (host-only) key if account was provided
        if account:
            fallback_target = credential_target_name(host, None)
            if fallback_target != target_name:
                try:
                    self._keyring.delete_password(self._service_name, fallback_target)
                    log.debug(f"Fallback token deleted for {fallback_target}")
                except Exception:
                    # Fallback key might not exist - ignore
                    pass
