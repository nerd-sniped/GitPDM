# -*- coding: utf-8 -*-
"""
Tests for git.client module - Git client operations
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from freecad_gitpdm.git.client import (
    GitClient,
    FileStatus,
    CmdResult,
    STATUS_MODIFIED,
    STATUS_ADDED,
    STATUS_UNTRACKED,
)


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
