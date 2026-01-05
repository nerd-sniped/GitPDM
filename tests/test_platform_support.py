"""Tests for platform-aware token store factory."""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestTokenStoreFactory:
    """Test token store factory platform detection."""

    def test_factory_returns_windows_store_on_windows(self):
        """Factory should return WindowsCredentialStore on Windows."""
        with patch("sys.platform", "win32"):
            from freecad.gitpdm.auth.token_store_factory import create_token_store

            store = create_token_store()
            assert store.__class__.__name__ == "WindowsCredentialStore"

    def test_factory_returns_linux_store_on_linux(self):
        """Factory should return LinuxSecretServiceStore on Linux."""
        with patch("sys.platform", "linux"):
            from freecad.gitpdm.auth.token_store_factory import create_token_store

            store = create_token_store()
            assert store.__class__.__name__ == "LinuxSecretServiceStore"

    def test_factory_returns_linux_store_on_linux2(self):
        """Factory should return LinuxSecretServiceStore on linux2 (old Python)."""
        with patch("sys.platform", "linux2"):
            from freecad.gitpdm.auth.token_store_factory import create_token_store

            store = create_token_store()
            assert store.__class__.__name__ == "LinuxSecretServiceStore"

    def test_factory_warns_on_macos(self):
        """Factory should return MacOSKeychainStore on macOS."""
        with patch("sys.platform", "darwin"):
            from freecad.gitpdm.auth.token_store_factory import create_token_store

            store = create_token_store()
            assert store.__class__.__name__ == "MacOSKeychainStore"

    def test_factory_raises_on_unknown_platform(self):
        """Factory should raise OSError on unsupported platform."""
        with patch("sys.platform", "unknown"):
            from freecad.gitpdm.auth.token_store_factory import create_token_store

            with pytest.raises(OSError, match="No secure token storage available"):
                create_token_store()


class TestLinuxSecretServiceStore:
    """Test Linux Secret Service token store."""

    @pytest.fixture
    def mock_secretstorage(self):
        """Mock secretstorage module."""
        with patch.dict("sys.modules", {"secretstorage": Mock()}):
            yield

    def test_linux_store_gracefully_handles_missing_secretstorage(self):
        """Linux store should handle missing secretstorage gracefully."""
        # Temporarily remove secretstorage from sys.modules if present
        original_module = sys.modules.get("secretstorage")
        if "secretstorage" in sys.modules:
            del sys.modules["secretstorage"]

        try:
            with patch.dict("sys.modules", {"secretstorage": None}):
                from freecad.gitpdm.auth.token_store_linux import (
                    LinuxSecretServiceStore,
                )

                store = LinuxSecretServiceStore()
                assert not store._available
        finally:
            # Restore original state
            if original_module is not None:
                sys.modules["secretstorage"] = original_module

    def test_linux_store_unavailable_raises_on_save(self, mock_secretstorage):
        """Linux store should raise OSError when unavailable."""
        from freecad.gitpdm.auth.token_store_linux import LinuxSecretServiceStore
        from freecad.gitpdm.auth.oauth_device_flow import TokenResponse

        store = LinuxSecretServiceStore()
        store._available = False

        token = TokenResponse(
            access_token="test_token",
            token_type="bearer",
            scope="repo",
            obtained_at_utc="2024-01-01T00:00:00Z",
        )

        with pytest.raises(OSError, match="Secret Service not available"):
            store.save("github.com", "testuser", token)

    def test_linux_store_unavailable_returns_none_on_load(self, mock_secretstorage):
        """Linux store should return None when unavailable."""
        from freecad.gitpdm.auth.token_store_linux import LinuxSecretServiceStore

        store = LinuxSecretServiceStore()
        store._available = False

        result = store.load("github.com", "testuser")
        assert result is None


class TestGitClientLinuxPaths:
    """Test git client finds git on Linux."""

    def test_finds_git_in_usr_bin(self):
        """Should find git in /usr/bin."""
        with patch("sys.platform", "linux"):
            with patch("os.path.isfile") as mock_isfile:
                # First path check succeeds
                mock_isfile.return_value = True

                from freecad.gitpdm.git.client import _find_git_executable

                result = _find_git_executable()
                assert result == "/usr/bin/git"

    def test_finds_git_on_path_linux(self):
        """Should fall back to PATH on Linux."""
        with patch("sys.platform", "linux"):
            with patch("os.path.isfile", return_value=False):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = Mock(returncode=0)

                    from freecad.gitpdm.git.client import _find_git_executable

                    result = _find_git_executable()
                    assert result == "git"
                    mock_run.assert_called_once()

    def test_returns_none_when_git_not_found_linux(self):
        """Should return None when git not found on Linux."""
        with patch("sys.platform", "linux"):
            with patch("os.path.isfile", return_value=False):
                with patch(
                    "subprocess.run", side_effect=FileNotFoundError("git not found")
                ):
                    from freecad.gitpdm.git.client import _find_git_executable

                    result = _find_git_executable()
                    assert result is None


class TestMacOSKeychainStore:
    """Test macOS Keychain token store."""

    @pytest.fixture
    def mock_keyring(self):
        """Mock keyring module."""
        mock_kr = Mock()
        mock_backend = Mock()
        mock_backend.__class__.__name__ = "KeychainKeyring"
        mock_kr.get_keyring.return_value = mock_backend
        mock_kr.errors = Mock()
        mock_kr.errors.PasswordDeleteError = Exception
        return mock_kr

    def test_macos_store_initialization_success(self, mock_keyring):
        """macOS store should initialize successfully with keyring available."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            from freecad.gitpdm.auth.token_store_macos import MacOSKeychainStore

            store = MacOSKeychainStore()
            assert store._available

    def test_macos_store_initialization_fail_backend(self):
        """macOS store should handle fail keyring backend gracefully."""
        mock_kr = Mock()
        mock_backend = Mock()
        mock_backend.__class__.__name__ = "FailKeyring"
        mock_kr.get_keyring.return_value = mock_backend

        with patch.dict("sys.modules", {"keyring": mock_kr}):
            from freecad.gitpdm.auth.token_store_macos import MacOSKeychainStore

            store = MacOSKeychainStore()
            assert not store._available

    def test_macos_store_unavailable_raises_on_save(self, mock_keyring):
        """macOS store should raise OSError when unavailable."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            from freecad.gitpdm.auth.token_store_macos import MacOSKeychainStore
            from freecad.gitpdm.auth.oauth_device_flow import TokenResponse

            store = MacOSKeychainStore()
            store._available = False

            token = TokenResponse(
                access_token="test_token",
                token_type="bearer",
                scope="repo",
                obtained_at_utc="2024-01-01T00:00:00Z",
            )

            with pytest.raises(OSError, match="macOS Keychain not available"):
                store.save("github.com", "testuser", token)

    def test_macos_store_unavailable_returns_none_on_load(self, mock_keyring):
        """macOS store should return None when unavailable."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            from freecad.gitpdm.auth.token_store_macos import MacOSKeychainStore

            store = MacOSKeychainStore()
            store._available = False

            result = store.load("github.com", "testuser")
            assert result is None

    def test_macos_store_save_and_load(self, mock_keyring):
        """macOS store should save and load tokens correctly."""
        stored_data = {}

        def mock_set_password(service, username, password):
            stored_data[f"{service}:{username}"] = password

        def mock_get_password(service, username):
            return stored_data.get(f"{service}:{username}")

        mock_keyring.set_password.side_effect = mock_set_password
        mock_keyring.get_password.side_effect = mock_get_password

        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            from freecad.gitpdm.auth.token_store_macos import MacOSKeychainStore
            from freecad.gitpdm.auth.oauth_device_flow import TokenResponse

            store = MacOSKeychainStore()

            # Save a token
            token = TokenResponse(
                access_token="test_token_123",
                token_type="bearer",
                scope="repo",
                refresh_token="refresh_123",
                expires_in=3600,
                refresh_token_expires_in=7200,
                obtained_at_utc="2024-01-01T00:00:00Z",
            )

            store.save("github.com", "testuser", token)

            # Load it back
            loaded = store.load("github.com", "testuser")

            assert loaded is not None
            assert loaded.access_token == "test_token_123"
            assert loaded.token_type == "bearer"
            assert loaded.scope == "repo"
            assert loaded.refresh_token == "refresh_123"
            assert loaded.expires_in == 3600

    def test_macos_store_delete(self, mock_keyring):
        """macOS store should delete tokens correctly."""
        deleted = []

        def mock_delete_password(service, username):
            deleted.append(f"{service}:{username}")

        mock_keyring.delete_password.side_effect = mock_delete_password

        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            from freecad.gitpdm.auth.token_store_macos import MacOSKeychainStore

            store = MacOSKeychainStore()
            store.delete("github.com", "testuser")

            # Should have deleted the primary key
            assert any("testuser" in d for d in deleted)

    def test_macos_store_handles_missing_keyring(self):
        """macOS store should handle missing keyring module gracefully."""
        original_module = sys.modules.get("keyring")
        if "keyring" in sys.modules:
            del sys.modules["keyring"]

        try:
            with patch.dict("sys.modules", {"keyring": None}):
                from freecad.gitpdm.auth.token_store_macos import MacOSKeychainStore

                store = MacOSKeychainStore()
                assert not store._available
        finally:
            if original_module is not None:
                sys.modules["keyring"] = original_module


class TestGitClientMacOSPaths:
    """Test git client finds git on macOS."""

    def test_finds_git_in_usr_local_bin(self):
        """Should find git in /usr/local/bin on macOS."""
        with patch("sys.platform", "darwin"):
            with patch("os.path.isfile") as mock_isfile:
                # First path fails, second succeeds
                mock_isfile.side_effect = [False, True]

                from freecad.gitpdm.git.client import _find_git_executable

                result = _find_git_executable()
                assert result == "/usr/local/bin/git"

    def test_finds_git_in_homebrew_path(self):
        """Should find git in Homebrew path on macOS."""
        with patch("sys.platform", "darwin"):
            with patch("os.path.isfile") as mock_isfile:
                # First three paths fail, fourth succeeds (Homebrew)
                mock_isfile.side_effect = [False, False, False, True]

                from freecad.gitpdm.git.client import _find_git_executable

                result = _find_git_executable()
                assert result == "/opt/homebrew/bin/git"

    def test_finds_git_on_path_macos(self):
        """Should fall back to PATH on macOS."""
        with patch("sys.platform", "darwin"):
            with patch("os.path.isfile", return_value=False):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = Mock(returncode=0)

                    from freecad.gitpdm.git.client import _find_git_executable

                    result = _find_git_executable()
                    assert result == "git"
                    mock_run.assert_called_once()
