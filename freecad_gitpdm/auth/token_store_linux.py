# -*- coding: utf-8 -*-
"""
GitPDM Linux Secret Service Token Store
Sprint OAUTH-1: Secure token storage using Secret Service API (D-Bus)

This module implements TokenStore for Linux using the Secret Service API
(libsecret/gnome-keyring) via the secretstorage library.
"""

from __future__ import annotations

import json
from freecad_gitpdm.auth.token_store import TokenStore
from freecad_gitpdm.auth.oauth_device_flow import TokenResponse
from freecad_gitpdm.auth.keys import credential_target_name


class LinuxSecretServiceStore(TokenStore):
    """
    Secure token storage using Linux Secret Service API (D-Bus).

    This works with GNOME Keyring, KWallet (via Secret Service), and other
    freedesktop.org Secret Service implementations.

    Requires: secretstorage library and a running D-Bus session with a
    secret service provider.
    """

    def __init__(self):
        """Initialize Secret Service connection."""
        self._available = False
        self._connection = None
        self._collection = None

        try:
            import secretstorage

            # Connect to D-Bus session bus
            self._connection = secretstorage.dbus_init()
            # Get default collection (usually "login")
            self._collection = secretstorage.get_default_collection(self._connection)
            self._available = True
        except Exception as e:
            from freecad_gitpdm.core import log

            log.warning(f"Secret Service not available: {e}")
            self._available = False

    def __del__(self):
        """Clean up D-Bus connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass

    def save(self, host: str, account: str | None, token: TokenResponse) -> None:
        """
        Save token to Secret Service.

        Args:
            host: GitHub host
            account: GitHub username (optional)
            token: TokenResponse to store

        Raises:
            OSError: If secret storage operation fails
        """
        if not self._available:
            from freecad_gitpdm.core import log

            log.error("Secret Service not available")
            raise OSError("Secret Service not available on this system")

        import secretstorage
        from freecad_gitpdm.core import log

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

        # Attributes for searching (similar to Windows target name)
        attributes = {
            "application": "freecad-gitpdm",
            "target": target_name,
            "host": host,
        }
        if account:
            attributes["account"] = account

        # Label for display in keyring managers
        label = f"GitPDM GitHub Token ({target_name})"

        log.debug(f"Storing token for {target_name} in Secret Service")

        # Delete any existing item first
        self._delete_internal(target_name, host, account)

        # Create new secret
        try:
            self._collection.create_item(
                label, attributes, token_json.encode("utf-8"), replace=True
            )
            log.debug(f"Token stored successfully for {target_name}")
        except Exception as e:
            log.error(f"Failed to store token: {e}")
            raise OSError(f"Failed to store token in Secret Service: {e}")

    def load(self, host: str, account: str | None) -> TokenResponse | None:
        """
        Load token from Secret Service.

        Args:
            host: GitHub host
            account: GitHub username (optional)

        Returns:
            TokenResponse or None if not found

        Raises:
            OSError: If secret lookup fails
            ValueError: If stored data is invalid
        """
        if not self._available:
            from freecad_gitpdm.core import log

            log.debug("Secret Service not available")
            return None

        from freecad_gitpdm.core import log

        target_name = credential_target_name(host, account)

        # Search for matching items
        search_attrs = {"application": "freecad-gitpdm", "target": target_name}

        log.debug(f"Loading token for {target_name} from Secret Service")

        try:
            items = list(self._collection.search_items(search_attrs))

            if not items:
                log.debug(f"Token not found for {target_name}")
                # Fallback: try without target, just host
                if account:
                    fallback_target = credential_target_name(host, None)
                    if fallback_target != target_name:
                        search_attrs = {
                            "application": "freecad-gitpdm",
                            "target": fallback_target,
                        }
                        items = list(self._collection.search_items(search_attrs))
                        if not items:
                            return None
                    else:
                        return None
                else:
                    return None

            # Get the secret from the first matching item
            item = items[0]
            token_bytes = item.get_secret()
            token_json = token_bytes.decode("utf-8")
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

        except Exception as e:
            log.error(f"Failed to load token: {e}")
            raise OSError(f"Failed to load token from Secret Service: {e}")

    def delete(self, host: str, account: str | None) -> None:
        """
        Delete token from Secret Service.

        Args:
            host: GitHub host
            account: GitHub username (optional)

        Raises:
            OSError: If secret deletion fails
        """
        if not self._available:
            from freecad_gitpdm.core import log

            log.error("Secret Service not available")
            raise OSError("Secret Service not available on this system")

        from freecad_gitpdm.core import log

        target_name = credential_target_name(host, account)
        self._delete_internal(target_name, host, account)

        # Also try to delete fallback (host-only) key if account was provided
        if account:
            fallback_target = credential_target_name(host, None)
            if fallback_target != target_name:
                try:
                    self._delete_internal(fallback_target, host, None)
                except Exception:
                    pass  # Fallback key might not exist

    def _delete_internal(self, target_name: str, host: str, account: str | None):
        """Internal helper to delete a specific target."""
        from freecad_gitpdm.core import log

        search_attrs = {"application": "freecad-gitpdm", "target": target_name}

        log.debug(f"Deleting token for {target_name} from Secret Service")

        try:
            items = list(self._collection.search_items(search_attrs))

            if not items:
                log.debug(f"Token not found for {target_name}")
                return

            # Delete all matching items
            for item in items:
                item.delete()

            log.debug(f"Token deleted successfully for {target_name}")

        except Exception as e:
            log.error(f"Failed to delete token: {e}")
            raise OSError(f"Failed to delete token from Secret Service: {e}")
