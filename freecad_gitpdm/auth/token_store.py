# -*- coding: utf-8 -*-
"""
GitPDM Token Storage Abstraction
Sprint OAUTH-1: Interface for secure token persistence

This module defines the interface for storing OAuth tokens in OS credential
storage (Windows Credential Manager, macOS Keychain, etc.). It does NOT store
tokens in FreeCAD settings or logs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from freecad_gitpdm.auth.oauth_device_flow import TokenResponse


class TokenStore(ABC):
    """
    Abstract interface for secure token storage.

    Implementations must store tokens in OS credential storage, NOT in
    FreeCAD settings or logs.
    """

    @abstractmethod
    def save(self, host: str, account: str | None, token: TokenResponse) -> None:
        """
        Save a token to secure storage.

        Args:
            host: str - GitHub host (e.g., "github.com")
            account: str | None - GitHub username (optional for multi-account)
            token: TokenResponse - Token to store

        Raises:
            OSError: If credential storage operation fails
        """
        pass

    @abstractmethod
    def load(self, host: str, account: str | None) -> TokenResponse | None:
        """
        Load a token from secure storage.

        Args:
            host: str - GitHub host (e.g., "github.com")
            account: str | None - GitHub username (optional for multi-account)

        Returns:
            TokenResponse if token exists, None if not found

        Raises:
            OSError: If credential storage operation fails
            ValueError: If stored token data is corrupted or invalid
        """
        pass

    @abstractmethod
    def delete(self, host: str, account: str | None) -> None:
        """
        Delete a token from secure storage.

        Args:
            host: str - GitHub host (e.g., "github.com")
            account: str | None - GitHub username (optional for multi-account)

        Raises:
            OSError: If credential storage operation fails
        """
        pass
