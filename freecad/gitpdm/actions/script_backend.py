"""
PowerShell Script Backend for GitPDM Actions

This backend executes PowerShell scripts instead of using Python subprocess.
Implements the GitBackend protocol so it can be swapped with GitClientBackend.

Phase 3: Bash Script Backend
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Any
from freecad.gitpdm.core import log


class ScriptBackend:
    """
    Git backend that uses PowerShell scripts for operations.
    
    Implements GitBackend protocol - can be used as drop-in replacement
    for GitClientBackend.
    """
    
    def __init__(self, scripts_dir: Optional[str] = None):
        """
        Initialize script backend.
        
        Args:
            scripts_dir: Directory containing git scripts (default: freecad/gitpdm/scripts/)
        """
        if scripts_dir is None:
            # Default to scripts/ directory next to this file
            this_dir = Path(__file__).parent
            scripts_dir = this_dir / "scripts"
        
        self.scripts_dir = Path(scripts_dir)
        
        if not self.scripts_dir.exists():
            log.warning(f"Scripts directory not found: {self.scripts_dir}")
    
    def _run_script(self, script_name: str, *args) -> tuple[int, str, str]:
        """
        Run a PowerShell script with arguments.
        
        Args:
            script_name: Name of script file (e.g., "git_status.ps1")
            *args: Arguments to pass to script
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        script_path = self.scripts_dir / script_name
        
        if not script_path.exists():
            error_msg = f"Script not found: {script_path}"
            log.error(error_msg)
            return (1, "", error_msg)
        
        # Build PowerShell command
        cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
        cmd.extend(str(arg) for arg in args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return (result.returncode, result.stdout.strip(), result.stderr.strip())
        except subprocess.TimeoutExpired:
            error_msg = f"Script timed out: {script_name}"
            log.error(error_msg)
            return (1, "", error_msg)
        except Exception as e:
            error_msg = f"Script execution failed: {e}"
            log.error(error_msg)
            return (1, "", error_msg)
    
    # ========== GitBackend Protocol Implementation ==========
    
    def is_git_available(self) -> bool:
        """Check if git is available."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_repo_root(self, path: str) -> Optional[str]:
        """
        Get repository root from path.
        
        Args:
            path: Directory path to check
        
        Returns:
            Repository root path if valid repo, None otherwise
        """
        code, stdout, stderr = self._run_script("git_validate_repo.ps1", path)
        
        if code == 0 and stdout:
            return stdout
        return None
    
    def init_repo(self, path: str) -> Any:
        """
        Initialize a new repository.
        
        Args:
            path: Directory path to initialize
        
        Returns:
            Result object (for compatibility)
        """
        code, stdout, stderr = self._run_script("git_init_repo.ps1", path)
        
        if code == 0:
            return type('Result', (), {'returncode': 0, 'stdout': stdout, 'stderr': stderr})()
        else:
            raise RuntimeError(stderr or "Init failed")
    
    def get_status_porcelain(self, repo_root: str) -> Any:
        """
        Get git status in porcelain format.
        
        Args:
            repo_root: Repository root path
        
        Returns:
            Result object with status output
        """
        code, stdout, stderr = self._run_script("git_status.ps1", repo_root)
        
        return type('Result', (), {
            'returncode': code,
            'stdout': stdout,
            'stderr': stderr
        })()
    
    def current_branch(self, repo_root: str) -> str:
        """
        Get current branch name.
        
        Args:
            repo_root: Repository root path
        
        Returns:
            Branch name or empty string
        """
        code, stdout, stderr = self._run_script("git_current_branch.ps1", repo_root)
        
        if code == 0:
            return stdout
        return ""
    
    def commit(self, repo_root: str, message: str, stage_all: bool = False) -> tuple[int, str, str]:
        """
        Commit changes.
        
        Args:
            repo_root: Repository root path
            message: Commit message
            stage_all: Whether to stage all changes first
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        args = [repo_root, message]
        if stage_all:
            args.append("-StageAll")
        
        return self._run_script("git_commit.ps1", *args)
    
    def push(self, repo_root: str, remote: str, branch: str = "") -> tuple[int, str, str]:
        """
        Push commits to remote.
        
        Args:
            repo_root: Repository root path
            remote: Remote name
            branch: Branch name (optional)
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        args = [repo_root, remote]
        if branch:
            args.append(branch)
        
        return self._run_script("git_push.ps1", *args)
    
    def fetch(self, repo_root: str, remote: str) -> tuple[int, str, str]:
        """
        Fetch from remote.
        
        Args:
            repo_root: Repository root path
            remote: Remote name
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        return self._run_script("git_fetch.ps1", repo_root, remote)
    
    def pull(self, repo_root: str, remote: str, branch: str = "") -> tuple[int, str, str]:
        """
        Pull from remote.
        
        Args:
            repo_root: Repository root path
            remote: Remote name
            branch: Branch name (optional)
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        args = [repo_root, remote]
        if branch:
            args.append(branch)
        
        return self._run_script("git_pull.ps1", *args)
    
    def add_remote(self, repo_root: str, name: str, url: str) -> tuple[int, str, str]:
        """
        Add a remote repository.
        
        Args:
            repo_root: Repository root path
            name: Remote name
            url: Remote URL
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        return self._run_script("git_add_remote.ps1", repo_root, name, url)


# Convenience function to create script backend
def create_script_backend() -> ScriptBackend:
    """Create a script backend with default settings."""
    return ScriptBackend()
