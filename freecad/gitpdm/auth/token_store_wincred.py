"""
GitPDM Windows Credential Manager Token Store
Sprint OAUTH-1: Secure token storage using Windows Credential Manager

This module implements TokenStore for Windows using ctypes to access
CredWriteW, CredReadW, CredDeleteW, and CredFree from Windows API.
"""

from __future__ import annotations

import json
import ctypes
from ctypes import wintypes
from freecad.gitpdm.auth.token_store import TokenStore
from freecad.gitpdm.auth.oauth_device_flow import TokenResponse
from freecad.gitpdm.auth.keys import credential_target_name


# Windows Credential Manager constants
CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
CRED_PRESERVE_CREDENTIAL_BLOB = 0x04000000


# ctypes definitions for Windows credential manager
class CREDENTIAL(ctypes.Structure):
    """Windows CREDENTIAL structure"""

    pass


# Define the structure fields
CREDENTIAL._fields_ = [
    ("Flags", wintypes.DWORD),
    ("Type", wintypes.DWORD),
    ("TargetName", wintypes.LPWSTR),
    ("Comment", wintypes.LPWSTR),
    ("LastWritten", wintypes.FILETIME),
    ("CredentialBlobSize", wintypes.DWORD),
    ("CredentialBlob", wintypes.LPBYTE),
    ("Persist", wintypes.DWORD),
    ("AttributeCount", wintypes.DWORD),
    ("Attributes", wintypes.LPVOID),
    ("TargetAlias", wintypes.LPWSTR),
    ("UserName", wintypes.LPWSTR),
]


def _get_cred_functions():
    """
    Get Windows credential manager functions from advapi32.dll

    Returns:
        tuple: (CredWriteW, CredReadW, CredDeleteW, CredFree)
    """
    advapi32 = ctypes.windll.advapi32

    # CredWriteW: BOOL CredWriteW(PCREDENTIALW Credential, DWORD Flags);
    CredWriteW = advapi32.CredWriteW
    CredWriteW.argtypes = [ctypes.POINTER(CREDENTIAL), wintypes.DWORD]
    CredWriteW.restype = wintypes.BOOL

    # CredReadW: BOOL CredReadW(LPCWSTR TargetName, DWORD Type,
    #                           DWORD Flags, PCREDENTIALW *Credential);
    CredReadW = advapi32.CredReadW
    CredReadW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.POINTER(CREDENTIAL)),
    ]
    CredReadW.restype = wintypes.BOOL

    # CredDeleteW: BOOL CredDeleteW(LPCWSTR TargetName, DWORD Type,
    #                               DWORD Flags);
    CredDeleteW = advapi32.CredDeleteW
    CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    CredDeleteW.restype = wintypes.BOOL

    # CredFree: VOID CredFree(PVOID Buffer);
    CredFree = advapi32.CredFree
    CredFree.argtypes = [wintypes.LPVOID]
    CredFree.restype = None

    return CredWriteW, CredReadW, CredDeleteW, CredFree


class WindowsCredentialStore(TokenStore):
    """
    Secure token storage using Windows Credential Manager.

    Stores token as JSON in the credential blob. Uses the target name
    from auth/keys.py to organize credentials.
    """

    def __init__(self):
        """Initialize Windows Credential Manager functions."""
        try:
            (self._cred_write, self._cred_read, self._cred_delete, self._cred_free) = (
                _get_cred_functions()
            )
            self._available = True
        except (AttributeError, OSError) as e:
            # Windows API not available (e.g., on non-Windows)
            from freecad.gitpdm.core import log

            log.warning(f"Windows Credential Manager not available: {e}")
            self._available = False

    def save(self, host: str, account: str | None, token: TokenResponse) -> None:
        """
        Save token to Windows Credential Manager.

        Args:
            host: GitHub host
            account: GitHub username (optional)
            token: TokenResponse to store

        Raises:
            OSError: If credential storage fails
        """
        if not self._available:
            from freecad.gitpdm.core import log

            log.error("Windows Credential Manager not available")
            raise OSError("Windows Credential Manager not available")

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
        token_bytes = token_json.encode("utf-8")

        # Create CREDENTIAL structure
        cred = CREDENTIAL()
        cred.Type = CRED_TYPE_GENERIC
        cred.TargetName = ctypes.c_wchar_p(target_name)
        cred.Comment = ctypes.c_wchar_p("")
        cred.CredentialBlobSize = len(token_bytes)
        cred.CredentialBlob = ctypes.cast(
            ctypes.c_char_p(token_bytes), ctypes.POINTER(wintypes.BYTE)
        )
        cred.Persist = CRED_PERSIST_LOCAL_MACHINE
        cred.AttributeCount = 0
        cred.Attributes = None
        cred.UserName = ctypes.c_wchar_p("GitPDM")

        # Write credential
        log.debug(f"Storing token for {target_name} in Windows Credential Manager")

        # Clear any previous error state
        ctypes.set_last_error(0)

        result = self._cred_write(ctypes.byref(cred), 0)

        if not result:
            error_code = ctypes.get_last_error()
            log.error(f"CredWriteW failed: {error_code}")
            raise OSError(f"CredWriteW failed: {error_code}")

        log.debug(f"Token stored successfully for {target_name}")

    def load(self, host: str, account: str | None) -> TokenResponse | None:
        """
        Load token from Windows Credential Manager.

        Args:
            host: GitHub host
            account: GitHub username (optional)

        Returns:
            TokenResponse or None if not found

        Raises:
            OSError: If credential lookup fails
            ValueError: If stored data is invalid
        """
        if not self._available:
            from freecad.gitpdm.core import log

            log.debug("Windows Credential Manager not available")
            return None

        from freecad.gitpdm.core import log

        def _read_target(target_name: str) -> TokenResponse | None:
            """Read a token from a specific Windows Credential Manager target."""
            pCred = ctypes.POINTER(CREDENTIAL)()
            log.debug(
                f"Loading token for {target_name} from Windows Credential Manager"
            )

            # Clear any previous error state
            ctypes.set_last_error(0)

            result = self._cred_read(
                ctypes.c_wchar_p(target_name),
                CRED_TYPE_GENERIC,
                0,
                ctypes.byref(pCred),
            )

            if not result:
                error_code = ctypes.get_last_error()
                # ERROR_NOT_FOUND = 1168, but also treat 0 as "not found"
                # (Windows sometimes returns 0 instead of 1168)
                if error_code == 1168 or error_code == 0:
                    log.debug(
                        f"Token not found for {target_name} (error code: {error_code})"
                    )
                    return None
                log.error(f"CredReadW failed: {error_code}")
                raise OSError(f"CredReadW failed: {error_code}")

            try:
                # Extract credential blob
                cred = pCred.contents
                token_bytes = bytes(
                    cred.CredentialBlob[i] for i in range(cred.CredentialBlobSize)
                )
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
            finally:
                # Free credential
                if pCred:
                    self._cred_free(ctypes.cast(pCred, wintypes.LPVOID))

        # Primary lookup: account-specific key (if account provided)
        primary_target = credential_target_name(host, account)
        token = _read_target(primary_target)
        if token is not None:
            return token

        # Back-compat / migration path: if the token was saved before the
        # username was known, it is stored under the host-only key.
        if account:
            fallback_target = credential_target_name(host, None)
            if fallback_target != primary_target:
                return _read_target(fallback_target)

        return None

    def delete(self, host: str, account: str | None) -> None:
        """
        Delete token from Windows Credential Manager.

        Args:
            host: GitHub host
            account: GitHub username (optional)

        Raises:
            OSError: If credential deletion fails
        """
        if not self._available:
            from freecad.gitpdm.core import log

            log.error("Windows Credential Manager not available")
            raise OSError("Windows Credential Manager not available")

        from freecad.gitpdm.core import log

        targets = [credential_target_name(host, account)]
        if account:
            targets.append(credential_target_name(host, None))

        # De-dup while preserving order
        seen = set()
        targets = [t for t in targets if not (t in seen or seen.add(t))]

        for target_name in targets:
            log.debug(
                f"Deleting token for {target_name} from Windows Credential Manager"
            )

            # Clear any previous error state
            ctypes.set_last_error(0)

            result = self._cred_delete(
                ctypes.c_wchar_p(target_name),
                CRED_TYPE_GENERIC,
                0,
            )

            if not result:
                error_code = ctypes.get_last_error()
                # ERROR_NOT_FOUND = 1168, but also treat 0 as "not found"
                if error_code == 1168 or error_code == 0:
                    log.debug(
                        f"Token not found for {target_name} (error code: {error_code})"
                    )
                    continue
                log.error(f"CredDeleteW failed: {error_code}")
                raise OSError(f"CredDeleteW failed: {error_code}")

            log.debug(f"Token deleted successfully for {target_name}")
