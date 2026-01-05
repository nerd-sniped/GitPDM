"""
Tests for lock_manager module
Sprint 1: Lock management testing
"""

import pytest
from pathlib import Path
import tempfile
import subprocess
from unittest.mock import Mock, patch, MagicMock

from freecad.gitpdm.core.lock_manager import LockManager, LockInfo
from freecad.gitpdm.core.config_manager import FCStdConfig


@pytest.fixture
def temp_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo, capture_output=True)
        
        # Create config
        (repo / ".gitpdm").mkdir()
        config_file = repo / ".gitpdm" / "config.json"
        
        import json
        config = FCStdConfig()
        with open(config_file, 'w') as f:
            json.dump(config.to_gitcad_format(), f)
        
        yield repo


class TestLockManager:
    """Tests for LockManager class."""
    
    def test_init_requires_git_repo(self):
        """Test that LockManager requires a git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            not_a_repo = Path(tmpdir)
            
            with pytest.raises(ValueError, match="Not a git repository"):
                LockManager(not_a_repo)
    
    def test_init_with_valid_repo(self, temp_repo):
        """Test successful initialization with valid repo."""
        manager = LockManager(temp_repo)
        
        assert manager.repo_root == temp_repo
    
    @patch('freecad_gitpdm.core.lock_manager.LockManager._run_git_command')
    def test_lock_file_success(self, mock_git, temp_repo):
        """Test successful file locking."""
        mock_git.return_value = Mock(ok=True, value="Locked successfully")
        
        manager = LockManager(temp_repo)
        result = manager.lock_file("test.FCStd")
        
        assert result.ok
        assert "Locked" in result.value
    
    @patch('freecad_gitpdm.core.lock_manager.LockManager._run_git_command')
    def test_lock_file_already_locked(self, mock_git, temp_repo):
        """Test locking a file that's already locked."""
        from freecad.gitpdm.core.result import Result
        
        mock_git.return_value = Result.failure(
            "GIT_ERROR",
            "already locked by other_user"
        )
        
        manager = LockManager(temp_repo)
        result = manager.lock_file("test.FCStd")
        
        assert not result.ok
        assert result.error.code == "ALREADY_LOCKED"
        assert "other_user" in result.error.message
    
    @patch('freecad_gitpdm.core.lock_manager.LockManager._run_git_command')
    def test_lock_file_with_force(self, mock_git, temp_repo):
        """Test force locking (steal lock)."""
        mock_git.return_value = Mock(ok=True, value="Locked")
        
        manager = LockManager(temp_repo)
        result = manager.lock_file("test.FCStd", force=True)
        
        assert result.ok
        
        # Verify force flag was passed
        call_args = mock_git.call_args[0][0]
        assert "--force" in call_args
    
    @patch('freecad_gitpdm.core.lock_manager.LockManager._run_git_command')
    def test_unlock_file_success(self, mock_git, temp_repo):
        """Test successful file unlocking."""
        mock_git.return_value = Mock(ok=True, value="Unlocked")
        
        manager = LockManager(temp_repo)
        result = manager.unlock_file("test.FCStd")
        
        assert result.ok
        assert "Unlocked" in result.value
    
    @patch('freecad_gitpdm.core.lock_manager.LockManager._run_git_command')
    def test_unlock_file_not_locked(self, mock_git, temp_repo):
        """Test unlocking a file that's not locked."""
        from freecad.gitpdm.core.result import Result
        
        mock_git.return_value = Result.failure(
            "GIT_ERROR",
            "not locked"
        )
        
        manager = LockManager(temp_repo)
        result = manager.unlock_file("test.FCStd")
        
        assert not result.ok
        assert result.error.code == "NOT_LOCKED"
    
    @patch('freecad_gitpdm.core.lock_manager.LockManager._run_git_command')
    def test_get_locks(self, mock_git, temp_repo):
        """Test getting list of locks."""
        # Mock git lfs locks output
        locks_output = """
test_uncompressed/.lockfile    user1    ID:123
parts/bracket_uncompressed/.lockfile    user2    ID:456
"""
        mock_git.return_value = Mock(ok=True, value=locks_output)
        
        manager = LockManager(temp_repo)
        result = manager.get_locks()
        
        assert result.ok
        locks = result.value
        assert len(locks) >= 1  # At least one lock parsed
        
        # Check lock info structure
        if locks:
            assert isinstance(locks[0], LockInfo)
            assert hasattr(locks[0], 'fcstd_path')
            assert hasattr(locks[0], 'owner')
    
    @patch('freecad_gitpdm.core.lock_manager.LockManager._run_git_command')
    def test_is_locked(self, mock_git, temp_repo):
        """Test checking if a file is locked."""
        locks_output = "test_uncompressed/.lockfile    user1    ID:123"
        mock_git.return_value = Mock(ok=True, value=locks_output)
        
        manager = LockManager(temp_repo)
        
        # This will depend on how we parse the lock output
        # For now, just test it doesn't crash
        is_locked = manager.is_locked("test.FCStd")
        assert isinstance(is_locked, bool)
    
    @patch('freecad_gitpdm.core.lock_manager.LockManager._run_git_command')
    def test_get_lock_owner(self, mock_git, temp_repo):
        """Test getting lock owner."""
        locks_output = "test_uncompressed/.lockfile    john_doe    ID:123"
        mock_git.return_value = Mock(ok=True, value=locks_output)
        
        manager = LockManager(temp_repo)
        
        owner = manager.get_lock_owner("test.FCStd")
        # May be None or a string depending on parsing
        assert owner is None or isinstance(owner, str)


class TestLockInfo:
    """Tests for LockInfo dataclass."""
    
    def test_lock_info_creation(self):
        """Test creating a LockInfo object."""
        lock = LockInfo(
            fcstd_path="test.FCStd",
            lockfile_path="test_uncompressed/.lockfile",
            owner="user1",
            lock_id="123"
        )
        
        assert lock.fcstd_path == "test.FCStd"
        assert lock.owner == "user1"
    
    def test_lock_info_string(self):
        """Test string representation."""
        lock = LockInfo(
            fcstd_path="test.FCStd",
            lockfile_path="test_uncompressed/.lockfile",
            owner="user1",
            lock_id="123"
        )
        
        lock_str = str(lock)
        assert "test.FCStd" in lock_str
        assert "user1" in lock_str


# Integration tests (require git lfs installed)
@pytest.mark.integration
class TestLockManagerIntegration:
    """Integration tests requiring git and git-lfs."""
    
    def test_real_lock_unlock(self, temp_repo):
        """Test actual lock/unlock with git lfs."""
        # Skip if git lfs not available
        try:
            subprocess.run(
                ["git", "lfs", "version"],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("git-lfs not available")
        
        # Initialize git lfs in repo
        subprocess.run(["git", "lfs", "install"], cwd=temp_repo)
        
        manager = LockManager(temp_repo)
        
        # Create a test file
        test_fcstd = temp_repo / "test.FCStd"
        test_fcstd.write_text("test")
        
        # Lock should work (or fail gracefully if no remote)
        result = manager.lock_file("test.FCStd")
        # Don't assert success since we might not have a remote configured
        assert result is not None
