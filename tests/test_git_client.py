# -*- coding: utf-8 -*-
"""
Tests for git.client module - Git client operations
"""

import os

import pytest
from unittest.mock import Mock, patch, MagicMock
from freecad_gitpdm.git.client import (
    GitClient,
    FileStatus,
    CmdResult,
    STATUS_MODIFIED,
    STATUS_ADDED,
    STATUS_UNTRACKED,
    _headless_credential_args,
    _headless_credential_username,
)


class TestHeadlessCredentialUsername:
    """Headless container credential auth must match the active provider's
    username convention, not assume GitHub's unconditionally (found while
    reviewing the manual test checklist for non-GitHub host coverage)."""

    def test_defaults_to_github_convention_when_unset(self, monkeypatch):
        monkeypatch.delenv("GITPDM_PROVIDER", raising=False)
        assert _headless_credential_username() == "x-access-token"

    def test_github_explicit(self, monkeypatch):
        monkeypatch.setenv("GITPDM_PROVIDER", "github")
        assert _headless_credential_username() == "x-access-token"

    def test_gitlab_uses_oauth2(self, monkeypatch):
        monkeypatch.setenv("GITPDM_PROVIDER", "gitlab")
        assert _headless_credential_username() == "oauth2"

    def test_generic_uses_github_convention(self, monkeypatch):
        # Most PAT-in-URL/token hosts ignore the username field entirely,
        # so GenericProvider's default is harmless even though it's named
        # after GitHub's convention.
        monkeypatch.setenv("GITPDM_PROVIDER", "generic")
        assert _headless_credential_username() == "x-access-token"

    def test_unknown_provider_falls_back(self, monkeypatch):
        monkeypatch.setenv("GITPDM_PROVIDER", "bogus-host")
        assert _headless_credential_username() == "x-access-token"

    def test_credential_args_thread_gitlab_username(self, monkeypatch):
        monkeypatch.setenv("GITPDM_TOKEN", "dummy")
        monkeypatch.setenv("GITPDM_PROVIDER", "gitlab")
        args = _headless_credential_args()
        assert any("username=oauth2" in a for a in args)

    def test_credential_args_empty_on_desktop(self, monkeypatch):
        monkeypatch.delenv("GITPDM_TOKEN", raising=False)
        monkeypatch.delenv("GITPDM_TOKEN_FILE", raising=False)
        assert _headless_credential_args() == []


class TestGitClient:
    """Test GitClient basic operations"""

    def test_git_client_initialization(self):
        """Test GitClient can be instantiated"""
        client = GitClient()
        assert client is not None
        assert client._git_available is None

    @patch("subprocess.run")
    def test_is_git_available_success(self, mock_run):
        """Test checking if git is available"""
        mock_run.return_value = MagicMock(returncode=0, stdout="git version 2.40.0")

        client = GitClient()
        result = client.is_git_available()

        assert result is True
        assert client._git_available is True

    @patch("subprocess.run")
    def test_is_git_available_failure(self, mock_run):
        """Test when git is not available"""
        mock_run.side_effect = FileNotFoundError()

        client = GitClient()
        result = client.is_git_available()

        assert result is False
        assert client._git_available is False

    @patch("subprocess.run")
    def test_get_git_version(self, mock_run):
        """Test getting git version"""
        mock_run.return_value = MagicMock(returncode=0, stdout="git version 2.40.1\n")

        client = GitClient()
        version = client.git_version()

        assert version is not None
        assert "2.40" in version

    @patch("subprocess.run")
    def test_is_repo_valid(self, mock_run, temp_repo):
        """Test getting repository root"""
        mock_run.return_value = MagicMock(returncode=0, stdout=str(temp_repo))

        client = GitClient()
        client._git_available = True
        result = client.get_repo_root(str(temp_repo))

        assert result is not None

    @patch("subprocess.run")
    def test_is_repo_invalid(self, mock_run, temp_repo):
        """Test checking invalid git repo"""
        mock_run.return_value = MagicMock(returncode=128, stderr="not a git repository")

        client = GitClient()
        client._git_available = True
        result = client.get_repo_root(str(temp_repo))

        assert result is None

    @patch("subprocess.run")
    def test_get_repo_root(self, mock_run, temp_repo):
        """Test getting repository root path"""
        mock_run.return_value = MagicMock(returncode=0, stdout=str(temp_repo) + "\n")

        client = GitClient()
        client._git_available = True
        result = client.get_repo_root(str(temp_repo))

        assert result is not None
        assert str(temp_repo) in str(result)


class TestFileStatus:
    """Test FileStatus dataclass"""

    def test_create_file_status(self):
        """Test creating FileStatus"""
        status = FileStatus(
            path="test.txt",
            x="M",
            y=" ",
            kind=STATUS_MODIFIED,
            is_staged=True,
            is_untracked=False,
        )
        assert status.path == "test.txt"
        assert status.x == "M"
        assert status.kind == STATUS_MODIFIED
        assert status.is_staged is True
        assert status.is_untracked is False


class TestGitStatus:
    """Test git status parsing"""

    @patch("subprocess.run")
    def test_get_status_clean_repo(self, mock_run, temp_repo):
        """Test status on clean repository"""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        client = GitClient()
        client._git_available = True
        result = client.status_porcelain(str(temp_repo))

        assert isinstance(result, list)
        assert len(result) == 0

    @patch("subprocess.run")
    def test_get_status_modified_files(self, mock_run, temp_repo):
        """Test status with modified files"""
        # Porcelain v1 format with -z
        mock_run.return_value = MagicMock(returncode=0, stdout=" M file.txt\0")

        client = GitClient()
        client._git_available = True
        result = client.status_porcelain(str(temp_repo))

        assert isinstance(result, list)

    @patch("subprocess.run")
    def test_get_status_untracked_files(self, mock_run, temp_repo):
        """Test status with untracked files"""
        mock_run.return_value = MagicMock(returncode=0, stdout="?? new_file.txt\0")

        client = GitClient()
        client._git_available = True
        result = client.status_porcelain(str(temp_repo))

        assert isinstance(result, list)


class TestGitCommit:
    """Test git commit operations"""

    @patch("subprocess.run")
    def test_commit_success(self, mock_run, temp_repo):
        """Test successful commit"""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="[main abc1234] Test commit\n 1 file changed"
        )

        client = GitClient()
        result = client.commit(str(temp_repo), "Test commit")

        assert result.ok is True

    @patch("subprocess.run")
    def test_commit_nothing_to_commit(self, mock_run, temp_repo):
        """Test commit when nothing to commit"""
        mock_run.return_value = MagicMock(
            returncode=1, stderr="nothing to commit, working tree clean"
        )

        client = GitClient()
        client._git_available = True
        result = client.commit(str(temp_repo), "Test commit")

        assert result.ok is False
        assert result.error_code == "NOTHING_TO_COMMIT"

    @patch("subprocess.run")
    def test_commit_missing_identity(self, mock_run, temp_repo):
        """Test commit with missing git identity"""
        mock_run.return_value = MagicMock(
            returncode=1, stderr="Please tell me who you are"
        )

        client = GitClient()
        client._git_available = True
        result = client.commit(str(temp_repo), "Test commit")

        assert result.ok is False
        assert result.error_code == "MISSING_IDENTITY"


class TestCmdResult:
    """Test CmdResult dataclass"""

    def test_create_cmd_result(self):
        """Test creating CmdResult"""
        result = CmdResult(ok=True, stdout="success", stderr="", error_code=None)
        assert result.ok is True
        assert result.stdout == "success"
        assert result.stderr == ""
        assert result.error_code is None

    def test_cmd_result_with_error(self):
        """Test CmdResult with error"""
        result = CmdResult(
            ok=False, stdout="", stderr="error message", error_code="GIT_ERROR"
        )
        assert result.ok is False
        assert result.error_code == "GIT_ERROR"


class TestSubprocessKwargsRegression:
    """Regression tests for the broken `timeout=N ** _get_subprocess_kwargs()`
    splats that made these methods raise TypeError on every call."""

    @patch("subprocess.run")
    def test_list_local_branches_runs(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="main\ndev\n", stderr="")
        client = GitClient()
        branches = client.list_local_branches(str(tmp_path))
        assert branches == ["main", "dev"]

    @patch("subprocess.run")
    def test_list_remote_branches_runs(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="origin/main\n", stderr=""
        )
        client = GitClient()
        branches = client.list_remote_branches(str(tmp_path))
        assert branches == ["origin/main"]

    @patch("subprocess.run")
    def test_pull_ff_only_runs(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Already up to date.", stderr=""
        )
        client = GitClient()
        result = client.pull_ff_only(str(tmp_path))
        assert result["ok"] is True


class TestShallowCloneTolerance:
    """Phase G5 / R2.4: --depth clone, shallow detection, deepen."""

    @patch("subprocess.run")
    def test_clone_repo_without_depth_omits_flag(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        client = GitClient()
        client._git_available = True
        dest = tmp_path / "dest"

        client.clone_repo("https://example.com/repo.git", str(dest))

        args = mock_run.call_args[0][0]
        assert "--depth" not in args

    @patch("subprocess.run")
    def test_clone_repo_with_depth_adds_flag(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        client = GitClient()
        client._git_available = True
        dest = tmp_path / "dest"

        client.clone_repo("https://example.com/repo.git", str(dest), depth=20)

        args = mock_run.call_args[0][0]
        assert "--depth" in args
        assert args[args.index("--depth") + 1] == "20"
        assert args[-2] == "https://example.com/repo.git"
        assert args[-1] == os.path.abspath(str(dest))

    @patch("subprocess.run")
    def test_is_shallow_repo_true(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="true\n", stderr="")
        client = GitClient()
        client._git_available = True

        assert client.is_shallow_repo(str(tmp_path)) is True

    @patch("subprocess.run")
    def test_is_shallow_repo_false(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="false\n", stderr="")
        client = GitClient()
        client._git_available = True

        assert client.is_shallow_repo(str(tmp_path)) is False

    @patch("subprocess.run")
    def test_is_shallow_repo_fails_open_on_error(self, mock_run, tmp_path):
        mock_run.side_effect = OSError("boom")
        client = GitClient()
        client._git_available = True

        assert client.is_shallow_repo(str(tmp_path)) is False

    def test_is_shallow_repo_missing_dir_returns_false(self):
        client = GitClient()
        client._git_available = True

        assert client.is_shallow_repo("/does/not/exist") is False

    @patch("subprocess.run")
    def test_deepen_repo_with_depth_uses_deepen_flag(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        client = GitClient()
        client._git_available = True

        result = client.deepen_repo(str(tmp_path), depth=20)

        args = mock_run.call_args[0][0]
        assert "--deepen" in args
        assert args[args.index("--deepen") + 1] == "20"
        assert result.ok is True

    @patch("subprocess.run")
    def test_deepen_repo_without_depth_unshallows(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        client = GitClient()
        client._git_available = True

        client.deepen_repo(str(tmp_path))

        args = mock_run.call_args[0][0]
        assert "--unshallow" in args

    @patch("subprocess.run")
    def test_deepen_repo_failure_returns_error_code(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="fatal: not shallow"
        )
        client = GitClient()
        client._git_available = True

        result = client.deepen_repo(str(tmp_path))

        assert result.ok is False
        assert result.error_code == "deepen_failed"
