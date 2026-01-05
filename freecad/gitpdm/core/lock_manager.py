"""
Lock Manager - Core Module
Sprint 1: Native Python implementation of file locking

This module provides file locking functionality using Git LFS,
replacing GitCAD's bash-based locking scripts.

Files are locked by locking a .lockfile in their uncompressed directory,
not the .FCStd file directly (which appears empty to git due to clean filter).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from .result import Result
from . import log


@dataclass
class LockInfo:
    """Information about a locked file."""
    fcstd_path: str  # Relative path to .FCStd file
    lockfile_path: str  # Relative path to .lockfile
    owner: str  # Username who owns the lock
    lock_id: str  # LFS lock ID
    locked_at: Optional[datetime] = None  # When locked (if available)
    
    def __str__(self) -> str:
        """String representation of lock."""
        return f"{self.fcstd_path} (locked by {self.owner})"


class LockManager:
    """
    Manages file locking using Git LFS.
    
    This class provides a Python interface to Git LFS locking,
    eliminating the need for bash scripts and subprocess wrappers.
    
    Example:
        >>> manager = LockManager(Path("/path/to/repo"))
        >>> result = manager.lock_file("part.FCStd")
        >>> if result.ok:
        ...     print("File locked successfully")
    """
    
    def __init__(self, repo_root: Path):
        """
        Initialize lock manager for a repository.
        
        Args:
            repo_root: Path to git repository root
        """
        self.repo_root = Path(repo_root).resolve()
        
        if not (self.repo_root / ".git").exists():
            raise ValueError(f"Not a git repository: {repo_root}")
    
    def lock_file(self, fcstd_path: str, force: bool = False) -> Result:
        """
        Lock a .FCStd file by locking its .lockfile.
        
        Args:
            fcstd_path: Relative path to .FCStd file (from repo root)
            force: If True, steal lock from other user
            
        Returns:
            Result with success message or error
            
        Example:
            >>> result = manager.lock_file("parts/bracket.FCStd")
            >>> if not result.ok:
            ...     print(f"Lock failed: {result.error.message}")
        """
        try:
            # Calculate lockfile path
            lockfile = self._get_lockfile_path(fcstd_path)
            
            if not lockfile:
                return Result.failure(
                    "CONFIG_ERROR",
                    f"Could not determine lockfile path for {fcstd_path}"
                )
            
            # Ensure lockfile exists (create if needed)
            lockfile_abs = self.repo_root / lockfile
            if not lockfile_abs.exists():
                lockfile_abs.parent.mkdir(parents=True, exist_ok=True)
                lockfile_abs.write_text("")
                
                # Stage the new lockfile
                self._run_git_command(["add", str(lockfile)])
            
            log.info(f"Locking {fcstd_path} via {lockfile}")
            
            # If force, first unlock (steal the lock)
            if force:
                log.info(f"Force lock requested, unlocking first...")
                unlock_result = self._run_git_command(["lfs", "unlock", "--force", str(lockfile)])
                if not unlock_result.ok:
                    log.warning(f"Force unlock failed (may not be locked): {unlock_result.error.message}")
            
            # Lock via git lfs (no --force flag for lock command)
            args = ["lfs", "lock", str(lockfile)]
            result = self._run_git_command(args)
            
            if result.ok:
                return Result.success(f"Locked: {fcstd_path}")
            else:
                # Parse error message for better feedback
                error_msg = result.error.message
                if "already locked" in error_msg.lower():
                    owner = self._extract_lock_owner(error_msg)
                    return Result.failure(
                        "ALREADY_LOCKED",
                        f"{fcstd_path} is already locked by {owner}"
                    )
                return result
                
        except Exception as e:
            log.error(f"Lock failed: {e}", exc_info=True)
            return Result.failure("LOCK_ERROR", str(e))
    
    def unlock_file(self, fcstd_path: str, force: bool = False) -> Result:
        """
        Unlock a .FCStd file by unlocking its .lockfile.
        
        Args:
            fcstd_path: Relative path to .FCStd file (from repo root)
            force: If True, break lock from other user (requires permissions)
            
        Returns:
            Result with success message or error
        """
        try:
            lockfile = self._get_lockfile_path(fcstd_path)
            
            if not lockfile:
                return Result.failure(
                    "CONFIG_ERROR",
                    f"Could not determine lockfile path for {fcstd_path}"
                )
            
            log.info(f"Unlocking {fcstd_path} via {lockfile}")
            
            # Build unlock command
            args = ["lfs", "unlock", str(lockfile)]
            if force:
                args.append("--force")
            
            result = self._run_git_command(args)
            
            if result.ok:
                return Result.success(f"Unlocked: {fcstd_path}")
            else:
                error_msg = result.error.message
                if "not locked" in error_msg.lower():
                    return Result.failure(
                        "NOT_LOCKED",
                        f"{fcstd_path} is not locked"
                    )
                return result
                
        except Exception as e:
            log.error(f"Unlock failed: {e}", exc_info=True)
            return Result.failure("UNLOCK_ERROR", str(e))
    
    def get_locks(self) -> Result:
        """
        Get list of all locked files in the repository.
        
        Returns:
            Result with list of LockInfo objects
            
        Example:
            >>> result = manager.get_locks()
            >>> if result.ok:
            ...     for lock in result.value:
            ...         print(f"{lock.fcstd_path} locked by {lock.owner}")
        """
        try:
            log.info("Querying git lfs locks...")
            result = self._run_git_command(["lfs", "locks"])
            
            if not result.ok:
                log.error(f"git lfs locks failed: {result.error.message}")
                return result
            
            # Parse lock output
            locks = self._parse_locks_output(result.value)
            log.info(f"Found {len(locks)} locked files")
            
            return Result.success(locks)
            
        except Exception as e:
            log.error(f"Failed to get locks: {e}", exc_info=True)
            return Result.failure("LOCK_QUERY_ERROR", str(e))
    
    def is_locked(self, fcstd_path: str) -> bool:
        """
        Check if a file is currently locked.
        
        Args:
            fcstd_path: Relative path to .FCStd file
            
        Returns:
            True if locked, False otherwise
        """
        result = self.get_locks()
        if not result.ok:
            return False
        
        for lock in result.value:
            if lock.fcstd_path == fcstd_path:
                return True
        return False
    
    def get_lock_owner(self, fcstd_path: str) -> Optional[str]:
        """
        Get the owner of a locked file.
        
        Args:
            fcstd_path: Relative path to .FCStd file
            
        Returns:
            Owner username if locked, None otherwise
        """
        result = self.get_locks()
        if not result.ok:
            return None
        
        for lock in result.value:
            if lock.fcstd_path == fcstd_path:
                return lock.owner
        return None
    
    def _get_lockfile_path(self, fcstd_path: str) -> Optional[Path]:
        """
        Calculate the .lockfile path for a .FCStd file.
        
        Args:
            fcstd_path: Relative path to .FCStd file
            
        Returns:
            Relative path to .lockfile, or None if config missing
        """
        try:
            from .config_manager import load_config, get_uncompressed_dir
            
            config = load_config(self.repo_root)
            uncompressed_dir = get_uncompressed_dir(
                self.repo_root,
                fcstd_path,
                config
            )
            
            lockfile = uncompressed_dir / ".lockfile"
            return lockfile.relative_to(self.repo_root)
            
        except Exception as e:
            log.error(f"Failed to get lockfile path: {e}")
            return None
    
    def _run_git_command(self, args: List[str]) -> Result:
        """
        Run a git command in the repository.
        
        Args:
            args: Git command arguments (e.g., ["lfs", "lock", "file"])
            
        Returns:
            Result with stdout on success, error on failure
        """
        try:
            import sys
            
            cmd = ["git"] + args
            
            # Windows-specific: suppress console window
            kwargs = {
                "cwd": self.repo_root,
                "capture_output": True,
                "text": True,
                "timeout": 30
            }
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run(cmd, **kwargs)
            
            if result.returncode == 0:
                return Result.success(result.stdout)
            else:
                return Result.failure(
                    "GIT_ERROR",
                    result.stderr or result.stdout or "Git command failed"
                )
                
        except subprocess.TimeoutExpired:
            return Result.failure("TIMEOUT", "Git command timed out")
        except FileNotFoundError:
            return Result.failure("GIT_NOT_FOUND", "Git not found in PATH")
        except Exception as e:
            return Result.failure("COMMAND_ERROR", str(e))
    
    def _parse_locks_output(self, output: str) -> List[LockInfo]:
        """
        Parse output from 'git lfs locks' command.
        
        Args:
            output: Raw output from git lfs locks
            
        Returns:
            List of LockInfo objects
        """
        locks = []
        
        log.info(f"Parsing git lfs locks output:\n{output}")
        
        for line in output.strip().split('\n'):
            if not line or line.startswith('--'):
                continue
            
            # Parse lock line - git lfs locks uses TAB separation
            # Example: "path/to/.lockfile\tuser\tID:123"
            # Fallback to whitespace split for different git-lfs versions
            if '\t' in line:
                parts = line.split('\t')
            else:
                parts = line.split()
            
            if len(parts) >= 2:
                lockfile_path = parts[0].strip()
                owner = parts[1].strip()
                lock_id = parts[2].strip() if len(parts) > 2 else ""
                
                log.info(f"Raw lock entry: lockfile='{lockfile_path}', owner='{owner}', id='{lock_id}'")
                
                # Convert .lockfile path back to .FCStd path using config
                fcstd_path = self._lockfile_to_fcstd(lockfile_path)
                
                locks.append(LockInfo(
                    fcstd_path=fcstd_path,
                    lockfile_path=lockfile_path,
                    owner=owner,
                    lock_id=lock_id
                ))
        
        return locks
    
    def _lockfile_to_fcstd(self, lockfile_path: str) -> str:
        """
        Convert a .lockfile path back to its corresponding .FCStd path.
        
        Args:
            lockfile_path: Path to lockfile (e.g., "part_uncompressed/.lockfile")
            
        Returns:
            Relative path to .FCStd file (e.g., "part.FCStd")
        """
        try:
            from .config_manager import load_config
            
            config = load_config(self.repo_root)
            lockfile = Path(lockfile_path)
            
            log.debug(f"Converting lockfile '{lockfile_path}' with config: suffix='{config.uncompressed_suffix}', prefix='{config.uncompressed_prefix}', subdir_mode={config.subdirectory_mode}")
            
            # Lockfile should end with .lockfile
            if lockfile.name != ".lockfile":
                log.warning(f"Lockfile path doesn't end with .lockfile: {lockfile_path}")
                # Fallback: just remove _uncompressed suffix
                result = lockfile_path.replace("_uncompressed/.lockfile", ".FCStd")
                log.debug(f"Fallback conversion: '{lockfile_path}' -> '{result}'")
                return result
            
            # Get the uncompressed directory name
            uncomp_dir = lockfile.parent
            
            # Handle subdirectory mode
            if config.subdirectory_mode:
                # Check if parent is the subdirectory
                if uncomp_dir.parent.name == config.subdirectory_name:
                    # Path like: "parts/.freecad_data/bracket_uncompressed/.lockfile"
                    actual_parent = uncomp_dir.parent.parent
                    uncomp_dir_name = uncomp_dir.name
                else:
                    actual_parent = uncomp_dir.parent
                    uncomp_dir_name = uncomp_dir.name
            else:
                # Path like: "parts/bracket_uncompressed/.lockfile" or "bracket_uncompressed/.lockfile"
                actual_parent = uncomp_dir.parent
                uncomp_dir_name = uncomp_dir.name
            
            log.debug(f"Uncompressed dir: '{uncomp_dir}', dir_name: '{uncomp_dir_name}', parent: '{actual_parent}'")
            
            # Remove prefix and suffix to get base name
            base_name = uncomp_dir_name
            if config.uncompressed_prefix and base_name.startswith(config.uncompressed_prefix):
                base_name = base_name[len(config.uncompressed_prefix):]
                log.debug(f"After removing prefix: '{base_name}'")
            if config.uncompressed_suffix and base_name.endswith(config.uncompressed_suffix):
                base_name = base_name[:-len(config.uncompressed_suffix)]
                log.debug(f"After removing suffix: '{base_name}'")
            
            # Reconstruct FCStd path
            if actual_parent == Path('.'):
                fcstd_path = f"{base_name}.FCStd"
            else:
                fcstd_path = str(actual_parent / f"{base_name}.FCStd")
            
            # Normalize path separators to forward slashes (git standard)
            fcstd_path = fcstd_path.replace('\\', '/')
            
            log.debug(f"Converted lockfile '{lockfile_path}' -> FCStd '{fcstd_path}'")
            return fcstd_path
            
        except Exception as e:
            log.error(f"Failed to convert lockfile to FCStd path: {e}")
            # Fallback to simple replace
            result = lockfile_path.replace("_uncompressed/.lockfile", ".FCStd")
            log.debug(f"Exception fallback: '{lockfile_path}' -> '{result}'")
            return result
    
    def _extract_lock_owner(self, error_message: str) -> str:
        """
        Extract lock owner from git lfs error message.
        
        Args:
            error_message: Error message from git lfs lock
            
        Returns:
            Owner username, or "another user"
        """
        # Try to parse owner from error message
        # Example: "Already locked by username"
        if "by" in error_message:
            parts = error_message.split("by")
            if len(parts) > 1:
                return parts[1].strip().split()[0]
        
        return "another user"
