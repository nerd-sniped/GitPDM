"""
Tests for Git Hooks (Sprint 2)
"""

import pytest
import tempfile
import zipfile
import subprocess
from pathlib import Path

from freecad.gitpdm.git import hooks
from freecad.gitpdm.git.hooks import HookContext


class TestHookContext:
    """Test HookContext creation and initialization."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository with config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            
            # Initialize git repo
            subprocess.run(['git', 'init'], cwd=repo, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo)
            
            # Create config
            config_dir = repo / "FreeCAD_Automation"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text("""{
                "uncompressed-directory-structure": {
                    "uncompressed-directory-suffix": "_uncompressed",
                    "uncompressed-directory-prefix": "",
                    "subdirectory": {
                        "put-uncompressed-directory-in-subdirectory": false,
                        "subdirectory-name": ""
                    }
                },
                "compress-non-human-readable-FreeCAD-files": {
                    "enabled": false,
                    "files-to-compress": [],
                    "max-compressed-file-size-gigabyte": 2.0,
                    "compression-level": 6,
                    "zip-file-prefix": "binaries_"
                },
                "require-lock-to-modify-FreeCAD-files": false,
                "include-thumbnails": true
            }""")
            
            yield repo
    
    def test_hook_context_creation(self, temp_repo):
        """Test creating hook context from repository."""
        ctx = HookContext.from_repo(temp_repo)
        
        assert ctx.repo_root == temp_repo
        assert ctx.config is not None
        assert ctx.config.uncompressed_suffix == "_uncompressed"
    
    def test_hook_context_without_lock_requirement(self, temp_repo):
        """Test context when locks not required."""
        ctx = HookContext.from_repo(temp_repo)
        
        # Lock manager should not be initialized
        assert ctx.lock_manager is None


class TestGitCommands:
    """Test git command execution helpers."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            subprocess.run(['git', 'init'], cwd=repo, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo)
            
            # Initial commit
            (repo / "README.md").write_text("# Test Repo")
            subprocess.run(['git', 'add', 'README.md'], cwd=repo)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo)
            
            yield repo
    
    def test_run_git_command(self, temp_repo):
        """Test running git commands."""
        result = hooks._run_git_command(['git', 'status'], temp_repo)
        
        assert result.returncode == 0
        assert 'On branch' in result.stdout or 'HEAD' in result.stdout
    
    def test_get_staged_fcstd_files_empty(self, temp_repo):
        """Test getting staged files when none exist."""
        files = hooks._get_staged_fcstd_files(temp_repo)
        
        assert files == []
    
    def test_get_staged_fcstd_files_with_staged(self, temp_repo):
        """Test getting staged FCStd files."""
        # Create and stage an FCStd file
        fcstd = temp_repo / "test.FCStd"
        with zipfile.ZipFile(fcstd, 'w') as zf:
            zf.writestr("Document.xml", "<Document/>")
        
        subprocess.run(['git', 'add', 'test.FCStd'], cwd=temp_repo)
        subprocess.run(['git', 'commit', '-m', 'Add FCStd'], cwd=temp_repo)
        
        # Modify and stage
        with zipfile.ZipFile(fcstd, 'a') as zf:
            zf.writestr("GuiDocument.xml", "<GuiDocument/>")
        
        subprocess.run(['git', 'add', 'test.FCStd'], cwd=temp_repo)
        
        files = hooks._get_staged_fcstd_files(temp_repo)
        
        assert len(files) == 1
        assert files[0].name == "test.FCStd"
    
    def test_is_rebase_in_progress(self, temp_repo):
        """Test rebase detection."""
        # Initially no rebase
        assert not hooks._is_rebase_in_progress(temp_repo)
        
        # Simulate rebase by creating rebase-merge directory
        (temp_repo / '.git' / 'rebase-merge').mkdir()
        
        assert hooks._is_rebase_in_progress(temp_repo)


class TestPreCommitHook:
    """Test pre-commit hook logic."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a test repository with config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            subprocess.run(['git', 'init'], cwd=repo, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo)
            
            # Create config
            config_dir = repo / "FreeCAD_Automation"
            config_dir.mkdir()
            (config_dir / "config.json").write_text("""{
                "uncompressed-directory-structure": {
                    "uncompressed-directory-suffix": "_uncompressed",
                    "uncompressed-directory-prefix": "",
                    "subdirectory": {"put-uncompressed-directory-in-subdirectory": false, "subdirectory-name": ""}
                },
                "compress-non-human-readable-FreeCAD-files": {
                    "enabled": false, "files-to-compress": [], "max-compressed-file-size-gigabyte": 2.0,
                    "compression-level": 6, "zip-file-prefix": "binaries_"
                },
                "require-lock-to-modify-FreeCAD-files": false,
                "include-thumbnails": true
            }""")
            
            # Initial commit
            (repo / "README.md").write_text("# Test")
            subprocess.run(['git', 'add', 'README.md'], cwd=repo)
            subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=repo)
            
            yield repo
    
    def test_pre_commit_with_empty_fcstd(self, temp_repo):
        """Test pre-commit hook accepts empty FCStd files."""
        # Create empty FCStd file
        fcstd = temp_repo / "test.FCStd"
        fcstd.write_bytes(b'')  # Empty file
        
        subprocess.run(['git', 'add', 'test.FCStd'], cwd=temp_repo)
        
        # Should pass
        exit_code = hooks.pre_commit_hook(temp_repo)
        assert exit_code == 0
    
    def test_pre_commit_with_non_empty_fcstd(self, temp_repo):
        """Test pre-commit hook rejects non-empty FCStd files."""
        # Create and commit an empty FCStd file first
        fcstd = temp_repo / "test.FCStd"
        fcstd.write_bytes(b'')
        
        subprocess.run(['git', 'add', 'test.FCStd'], cwd=temp_repo)
        subprocess.run(['git', 'commit', '-m', 'Add empty FCStd'], cwd=temp_repo)
        
        # Now modify it to be non-empty (must be > 1KB)
        with zipfile.ZipFile(fcstd, 'w') as zf:
            # Create a large enough file (> 1KB)
            large_content = "<Document>" + ("x" * 2000) + "</Document>"
            zf.writestr("Document.xml", large_content)
        
        subprocess.run(['git', 'add', 'test.FCStd'], cwd=temp_repo)
        
        # Should fail
        exit_code = hooks.pre_commit_hook(temp_repo)
        assert exit_code == 1
    
    def test_pre_commit_with_no_staged_files(self, temp_repo):
        """Test pre-commit hook with no staged files."""
        exit_code = hooks.pre_commit_hook(temp_repo)
        assert exit_code == 0


class TestPostCheckoutHook:
    """Test post-checkout hook logic."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a test repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            subprocess.run(['git', 'init'], cwd=repo, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo)
            
            # Create config
            config_dir = repo / "FreeCAD_Automation"
            config_dir.mkdir()
            (config_dir / "config.json").write_text("""{
                "uncompressed-directory-structure": {
                    "uncompressed-directory-suffix": "_uncompressed",
                    "uncompressed-directory-prefix": "",
                    "subdirectory": {"put-uncompressed-directory-in-subdirectory": false, "subdirectory-name": ""}
                },
                "compress-non-human-readable-FreeCAD-files": {
                    "enabled": false, "files-to-compress": [], "max-compressed-file-size-gigabyte": 2.0,
                    "compression-level": 6, "zip-file-prefix": "binaries_"
                },
                "require-lock-to-modify-FreeCAD-files": false,
                "include-thumbnails": true
            }""")
            
            # Initial commit
            (repo / "README.md").write_text("# Test")
            subprocess.run(['git', 'add', '.'], cwd=repo)
            subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=repo)
            
            yield repo
    
    def test_post_checkout_file_checkout(self, temp_repo):
        """Test post-checkout with file checkout (not branch)."""
        # Get current HEAD
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=temp_repo,
            capture_output=True,
            text=True
        )
        head = result.stdout.strip()
        
        # File checkout (checkout_type = "0")
        exit_code = hooks.post_checkout_hook(temp_repo, head, head, "0")
        assert exit_code == 0
    
    def test_post_checkout_branch_checkout(self, temp_repo):
        """Test post-checkout with branch checkout."""
        # Get current HEAD
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=temp_repo,
            capture_output=True,
            text=True
        )
        head = result.stdout.strip()
        
        # Branch checkout (checkout_type = "1")
        exit_code = hooks.post_checkout_hook(temp_repo, head, head, "1")
        assert exit_code == 0


class TestPostMergeHook:
    """Test post-merge hook logic."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a test repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            subprocess.run(['git', 'init'], cwd=repo, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo)
            
            # Create config
            config_dir = repo / "FreeCAD_Automation"
            config_dir.mkdir()
            (config_dir / "config.json").write_text("""{
                "uncompressed-directory-structure": {
                    "uncompressed-directory-suffix": "_uncompressed",
                    "uncompressed-directory-prefix": "",
                    "subdirectory": {"put-uncompressed-directory-in-subdirectory": false, "subdirectory-name": ""}
                },
                "compress-non-human-readable-FreeCAD-files": {
                    "enabled": false, "files-to-compress": [], "max-compressed-file-size-gigabyte": 2.0,
                    "compression-level": 6, "zip-file-prefix": "binaries_"
                },
                "require-lock-to-modify-FreeCAD-files": false,
                "include-thumbnails": true
            }""")
            
            # Initial commit
            (repo / "README.md").write_text("# Test")
            subprocess.run(['git', 'add', '.'], cwd=repo)
            subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=repo)
            
            yield repo
    
    def test_post_merge_normal(self, temp_repo):
        """Test post-merge hook with normal merge."""
        # Create ORIG_HEAD to simulate a merge
        head_result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=temp_repo,
            capture_output=True,
            text=True
        )
        (temp_repo / '.git' / 'ORIG_HEAD').write_text(head_result.stdout.strip())
        
        exit_code = hooks.post_merge_hook(temp_repo, "0")
        assert exit_code == 0
    
    def test_post_merge_squash(self, temp_repo):
        """Test post-merge hook with squash merge."""
        # Create ORIG_HEAD to simulate a merge
        head_result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=temp_repo,
            capture_output=True,
            text=True
        )
        (temp_repo / '.git' / 'ORIG_HEAD').write_text(head_result.stdout.strip())
        
        exit_code = hooks.post_merge_hook(temp_repo, "1")
        assert exit_code == 0


class TestIntegration:
    """Integration tests with actual FCStd files."""
    
    @pytest.fixture
    def temp_repo_with_fcstd(self):
        """Create repository with FCStd file and uncompressed directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            subprocess.run(['git', 'init'], cwd=repo, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo)
            
            # Create config
            config_dir = repo / "FreeCAD_Automation"
            config_dir.mkdir()
            (config_dir / "config.json").write_text("""{
                "uncompressed-directory-structure": {
                    "uncompressed-directory-suffix": "_uncompressed",
                    "uncompressed-directory-prefix": "",
                    "subdirectory": {"put-uncompressed-directory-in-subdirectory": false, "subdirectory-name": ""}
                },
                "compress-non-human-readable-FreeCAD-files": {
                    "enabled": false, "files-to-compress": [], "max-compressed-file-size-gigabyte": 2.0,
                    "compression-level": 6, "zip-file-prefix": "binaries_"
                },
                "require-lock-to-modify-FreeCAD-files": false,
                "include-thumbnails": true
            }""")
            
            # Create uncompressed directory with changefile
            uncompressed = repo / "test_uncompressed"
            uncompressed.mkdir()
            (uncompressed / "Document.xml").write_text("<Document/>")
            (uncompressed / ".changefile").write_text(
                "File Last Exported On: 2026-01-03T00:00:00Z\n"
                "FCStd_file_relpath='test.FCStd'\n"
            )
            
            # Create empty FCStd
            fcstd = repo / "test.FCStd"
            fcstd.write_bytes(b'')
            
            # Initial commit
            subprocess.run(['git', 'add', '.'], cwd=repo)
            subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=repo)
            
            yield repo
    
    @pytest.mark.integration
    def test_hook_workflow(self, temp_repo_with_fcstd):
        """Test complete hook workflow."""
        # Pre-commit should pass with empty FCStd
        exit_code = hooks.pre_commit_hook(temp_repo_with_fcstd)
        assert exit_code == 0
