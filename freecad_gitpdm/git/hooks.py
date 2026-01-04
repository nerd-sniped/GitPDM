# -*- coding: utf-8 -*-
"""
Git Hooks Module - Sprint 2: Native Python Implementation

This module provides Python-based git hooks to replace the bash scripts,
integrating with the Sprint 1 core modules for FCStd file management.

Hook Overview:
- pre-commit: Validate FCStd files are empty, check locks
- post-checkout: Import FCStd files after branch switch
- post-merge: Import FCStd files after merge
- post-rewrite: Import FCStd files after rebase
- pre-push: Validate user has locks for modified files
"""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

from freecad_gitpdm.core import log
from freecad_gitpdm.core.result import Result
from freecad_gitpdm.core.config_manager import load_config, FCStdConfig
from freecad_gitpdm.core.fcstd_tool import import_fcstd, export_fcstd
from freecad_gitpdm.core.lock_manager import LockManager


@dataclass
class HookContext:
    """Context information for git hook execution."""
    repo_root: Path
    config: FCStdConfig
    lock_manager: Optional[LockManager] = None
    
    @classmethod
    def from_repo(cls, repo_root: Path) -> 'HookContext':
        """Create hook context from repository root."""
        config = load_config(repo_root)
        
        lock_manager = None
        if config.require_lock:
            try:
                lock_manager = LockManager(repo_root)
            except Exception as e:
                log.warning(f"Could not initialize lock manager: {e}")
        
        return cls(
            repo_root=repo_root,
            config=config,
            lock_manager=lock_manager
        )


def _run_git_command(cmd: List[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    """
    Run a git command and return the result.
    
    Args:
        cmd: Command list (e.g., ['git', 'diff-index', ...])
        cwd: Working directory
        check: Whether to raise exception on non-zero exit
        
    Returns:
        CompletedProcess with stdout, stderr, returncode
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        log.error(f"Git command failed: {' '.join(cmd)}")
        log.error(f"Exit code: {e.returncode}")
        log.error(f"Stderr: {e.stderr}")
        raise


def _get_staged_fcstd_files(repo_root: Path) -> List[Path]:
    """
    Get list of staged .FCStd files (modified, not newly added).
    
    Args:
        repo_root: Repository root path
        
    Returns:
        List of Path objects for staged FCStd files
    """
    # Refresh git index
    _run_git_command(['git', 'update-index', '--refresh', '-q'], repo_root, check=False)
    
    # Get staged files (excluding Added files)
    # Filter: C=copied, D=deleted, M=modified, R=renamed, T=type-changed, U=unmerged, X=unknown, B=broken
    result = _run_git_command(
        ['git', 'diff-index', '--cached', '--name-only', '--diff-filter=CDMRTUXB', 'HEAD'],
        repo_root,
        check=False
    )
    
    # Filter for .FCStd files
    fcstd_files = []
    for line in result.stdout.strip().split('\n'):
        if line and line.lower().endswith('.fcstd'):
            fcstd_files.append(repo_root / line)
    
    return fcstd_files


def _get_changed_files_between_refs(repo_root: Path, old_ref: str, new_ref: str) -> List[Path]:
    """
    Get list of files changed between two git refs.
    
    Args:
        repo_root: Repository root path
        old_ref: Old reference (e.g., 'ORIG_HEAD', commit SHA)
        new_ref: New reference (e.g., 'HEAD', commit SHA)
        
    Returns:
        List of changed file paths
    """
    result = _run_git_command(
        ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', old_ref, new_ref],
        repo_root
    )
    
    changed_files = []
    for line in result.stdout.strip().split('\n'):
        if line:
            changed_files.append(repo_root / line)
    
    return changed_files


def _is_rebase_in_progress(repo_root: Path) -> bool:
    """
    Check if a git rebase is currently in progress.
    
    Args:
        repo_root: Repository root path
        
    Returns:
        True if rebase is active
    """
    git_dir = repo_root / '.git'
    return (git_dir / 'rebase-merge').exists() or (git_dir / 'rebase-apply').exists()


def pre_commit_hook(repo_root: Path) -> int:
    """
    Pre-commit hook: Validate FCStd files are empty and user has required locks.
    
    This hook ensures that:
    1. Staged .FCStd files are empty (actual data in uncompressed directories)
    2. User has locks for files they're modifying (if locking enabled)
    
    Args:
        repo_root: Repository root path
        
    Returns:
        0 for success, 1 for failure
    """
    try:
        ctx = HookContext.from_repo(repo_root)
        
        # Check staged FCStd files are empty
        staged_fcstd = _get_staged_fcstd_files(repo_root)
        
        for fcstd_path in staged_fcstd:
            if not fcstd_path.exists():
                continue
            
            # Check if file is empty (or nearly empty - allow small metadata)
            file_size = fcstd_path.stat().st_size
            if file_size > 1024:  # More than 1KB = not empty
                print(f"Error: {fcstd_path.name} is not empty ({file_size} bytes)", file=sys.stderr)
                print(f"Export it using `git fadd` or clear it using `git fcmod`", file=sys.stderr)
                return 1
        
        # Check locks if required
        if ctx.config.require_lock and ctx.lock_manager:
            # Get current user
            user_result = _run_git_command(
                ['git', 'config', '--get', 'user.name'],
                repo_root
            )
            current_user = user_result.stdout.strip()
            
            if not current_user:
                print("Error: git config user.name not set!", file=sys.stderr)
                return 1
            
            # Get user's locks
            locks_result = ctx.lock_manager.get_locks()
            if not locks_result.ok:
                print(f"Error: Failed to get lock info: {locks_result.error}", file=sys.stderr)
                return 1
            
            user_locked_files = [
                lock.path for lock in locks_result.value
                if lock.owner == current_user
            ]
            
            # Get staged .changefile files (indicators of FCStd modifications)
            result = _run_git_command(
                ['git', 'diff-index', '--cached', '--name-only', '--diff-filter=CDMRTUXB', 'HEAD'],
                repo_root,
                check=False
            )
            
            staged_changefiles = [
                line for line in result.stdout.strip().split('\n')
                if line and line.lower().endswith('.changefile')
            ]
            
            # Verify user has locks for modified files
            for changefile in staged_changefiles:
                # Extract FCStd path from changefile path
                # .changefile is in uncompressed directory, corresponding .FCStd is the file to lock
                changefile_path = repo_root / changefile
                
                # Read changefile to get FCStd path
                if changefile_path.exists():
                    content = changefile_path.read_text()
                    for line in content.split('\n'):
                        if 'FCStd_file_relpath=' in line:
                            # Extract path from FCStd_file_relpath='path/to/file.FCStd'
                            fcstd_rel = line.split('=', 1)[1].strip().strip("'\"")
                            fcstd_path = repo_root / fcstd_rel
                            
                            if str(fcstd_path) not in user_locked_files:
                                print(f"Error: You don't have a lock on {fcstd_path.name}", file=sys.stderr)
                                print(f"Use `git lock {fcstd_path}` to acquire lock", file=sys.stderr)
                                return 1
        
        return 0
        
    except Exception as e:
        log.error(f"Pre-commit hook failed: {e}")
        print(f"Error: Pre-commit hook failed: {e}", file=sys.stderr)
        return 1


def post_checkout_hook(repo_root: Path, old_ref: str, new_ref: str, checkout_type: str) -> int:
    """
    Post-checkout hook: Import FCStd files after branch switch.
    
    This hook:
    1. Runs git-lfs post-checkout
    2. Pulls LFS files
    3. Imports (recompresses) FCStd files from uncompressed directories
    
    Args:
        repo_root: Repository root path
        old_ref: Previous HEAD reference
        new_ref: New HEAD reference
        checkout_type: "1" for branch checkout, "0" for file checkout
        
    Returns:
        0 for success, 2 for fatal error
    """
    try:
        ctx = HookContext.from_repo(repo_root)
        
        # Run git-lfs post-checkout
        try:
            subprocess.run(
                ['git', 'lfs', 'post-checkout', old_ref, new_ref, checkout_type],
                cwd=str(repo_root),
                check=True
            )
        except subprocess.CalledProcessError:
            print("Warning: git-lfs post-checkout failed", file=sys.stderr)
        
        # Pull LFS files
        try:
            _run_git_command(['git', 'lfs', 'pull'], repo_root)
        except Exception as e:
            log.warning(f"LFS pull failed: {e}")
        
        # Skip if rebase in progress (handled by post-rewrite)
        if _is_rebase_in_progress(repo_root):
            return 0
        
        # Only process branch checkouts
        if checkout_type != "1":
            return 0
        
        # Get changed files
        changed_files = _get_changed_files_between_refs(repo_root, old_ref, new_ref)
        
        # Find changed .changefile files
        changefiles = [f for f in changed_files if f.name.lower().endswith('.changefile')]
        
        # Import each changed FCStd file
        for changefile in changefiles:
            if not changefile.exists():
                continue
            
            # Parse changefile to get FCStd path
            try:
                content = changefile.read_text()
                fcstd_relpath = None
                for line in content.split('\n'):
                    if 'FCStd_file_relpath=' in line:
                        fcstd_relpath = line.split('=', 1)[1].strip().strip("'\"")
                        break
                
                if not fcstd_relpath:
                    continue
                
                # Calculate paths
                fcstd_path = repo_root / fcstd_relpath
                uncompressed_dir = changefile.parent
                
                # Import the file
                print(f"Importing: {fcstd_path.name}...", end='', file=sys.stderr)
                result = import_fcstd(uncompressed_dir, fcstd_path, ctx.config)
                
                if result.ok:
                    print(" Done", file=sys.stderr)
                else:
                    print(f" Failed: {result.error}", file=sys.stderr)
                    
            except Exception as e:
                log.error(f"Failed to import from {changefile}: {e}")
                continue
        
        return 0
        
    except Exception as e:
        log.error(f"Post-checkout hook failed: {e}")
        return 2


def post_merge_hook(repo_root: Path, is_squash: str) -> int:
    """
    Post-merge hook: Import FCStd files after merge.
    
    Similar to post-checkout but for merge operations.
    
    Args:
        repo_root: Repository root path
        is_squash: "1" if squash merge, "0" otherwise
        
    Returns:
        0 for success, 2 for fatal error
    """
    try:
        ctx = HookContext.from_repo(repo_root)
        
        # Run git-lfs post-merge
        try:
            subprocess.run(
                ['git', 'lfs', 'post-merge', is_squash],
                cwd=str(repo_root),
                check=True
            )
        except subprocess.CalledProcessError:
            print("Warning: git-lfs post-merge failed", file=sys.stderr)
        
        # Pull LFS files
        try:
            _run_git_command(['git', 'lfs', 'pull'], repo_root)
        except Exception as e:
            log.warning(f"LFS pull failed: {e}")
        
        # Get changed files between ORIG_HEAD and HEAD
        # ORIG_HEAD might not exist (e.g., initial commit or first merge)
        try:
            changed_files = _get_changed_files_between_refs(repo_root, 'ORIG_HEAD', 'HEAD')
        except Exception:
            # If ORIG_HEAD doesn't exist, no files to import
            return 0
        
        # Find changed .changefile files
        changefiles = [f for f in changed_files if f.name.lower().endswith('.changefile')]
        
        # Import each changed FCStd file
        for changefile in changefiles:
            if not changefile.exists():
                continue
            
            try:
                content = changefile.read_text()
                fcstd_relpath = None
                for line in content.split('\n'):
                    if 'FCStd_file_relpath=' in line:
                        fcstd_relpath = line.split('=', 1)[1].strip().strip("'\"")
                        break
                
                if not fcstd_relpath:
                    continue
                
                fcstd_path = repo_root / fcstd_relpath
                uncompressed_dir = changefile.parent
                
                print(f"Importing: {fcstd_path.name}...", end='', file=sys.stderr)
                result = import_fcstd(uncompressed_dir, fcstd_path, ctx.config)
                
                if result.ok:
                    print(" Done", file=sys.stderr)
                else:
                    print(f" Failed: {result.error}", file=sys.stderr)
                    
            except Exception as e:
                log.error(f"Failed to import from {changefile}: {e}")
                continue
        
        return 0
        
    except Exception as e:
        log.error(f"Post-merge hook failed: {e}")
        return 2


def post_rewrite_hook(repo_root: Path, rewrite_type: str) -> int:
    """
    Post-rewrite hook: Import FCStd files after rebase/amend.
    
    Args:
        repo_root: Repository root path
        rewrite_type: "rebase" or "amend"
        
    Returns:
        0 for success, 2 for fatal error
    """
    try:
        ctx = HookContext.from_repo(repo_root)
        
        # Run git-lfs post-rewrite
        try:
            # Git LFS expects rewritten refs on stdin
            subprocess.run(
                ['git', 'lfs', 'post-rewrite', rewrite_type],
                cwd=str(repo_root),
                stdin=sys.stdin,
                check=True
            )
        except subprocess.CalledProcessError:
            print("Warning: git-lfs post-rewrite failed", file=sys.stderr)
        
        # For rebase, import all FCStd files that have changefiles
        if rewrite_type == "rebase":
            # Find all .changefile files in repo
            changefiles = list(repo_root.rglob('*.changefile'))
            
            for changefile in changefiles:
                if not changefile.exists():
                    continue
                
                try:
                    content = changefile.read_text()
                    fcstd_relpath = None
                    for line in content.split('\n'):
                        if 'FCStd_file_relpath=' in line:
                            fcstd_relpath = line.split('=', 1)[1].strip().strip("'\"")
                            break
                    
                    if not fcstd_relpath:
                        continue
                    
                    fcstd_path = repo_root / fcstd_relpath
                    uncompressed_dir = changefile.parent
                    
                    print(f"Importing: {fcstd_path.name}...", end='', file=sys.stderr)
                    result = import_fcstd(uncompressed_dir, fcstd_path, ctx.config)
                    
                    if result.ok:
                        print(" Done", file=sys.stderr)
                    else:
                        print(f" Failed: {result.error}", file=sys.stderr)
                        
                except Exception as e:
                    log.error(f"Failed to import from {changefile}: {e}")
                    continue
        
        return 0
        
    except Exception as e:
        log.error(f"Post-rewrite hook failed: {e}")
        return 2


def pre_push_hook(repo_root: Path, remote_name: str, remote_url: str) -> int:
    """
    Pre-push hook: Validate user has locks for files being pushed.
    
    Args:
        repo_root: Repository root path
        remote_name: Name of remote (e.g., "origin")
        remote_url: URL of remote
        
    Returns:
        0 for success, 1 for failure
    """
    try:
        ctx = HookContext.from_repo(repo_root)
        
        # Read stdin for push refs (format: local_ref local_sha remote_ref remote_sha)
        push_info = sys.stdin.read().strip()
        if not push_info:
            return 0
        
        # Parse last line (most recent push)
        lines = push_info.split('\n')
        if not lines:
            return 0
        
        parts = lines[-1].split()
        if len(parts) < 4:
            return 0
        
        local_ref, local_sha, remote_ref, remote_sha = parts[0], parts[1], parts[2], parts[3]
        
        # Run git-lfs pre-push (pass stdin)
        try:
            subprocess.run(
                ['git', 'lfs', 'pre-push', remote_name, remote_url],
                input=push_info,
                text=True,
                cwd=str(repo_root),
                check=True
            )
        except subprocess.CalledProcessError:
            print("Warning: git-lfs pre-push failed", file=sys.stderr)
        
        # Check locks if required
        if not ctx.config.require_lock or not ctx.lock_manager:
            return 0
        
        # Get current user
        user_result = _run_git_command(['git', 'config', '--get', 'user.name'], repo_root)
        current_user = user_result.stdout.strip()
        
        if not current_user:
            print("Error: git config user.name not set!", file=sys.stderr)
            return 1
        
        # Get user's locks
        locks_result = ctx.lock_manager.get_locks()
        if not locks_result.ok:
            print(f"Error: Failed to get lock info: {locks_result.error}", file=sys.stderr)
            return 1
        
        user_locked_files = {
            lock.path for lock in locks_result.value
            if lock.owner == current_user
        }
        
        # Get commits being pushed
        if remote_sha == '0' * 40:  # New branch
            commits_range = local_sha
        else:
            commits_range = f"{remote_sha}..{local_sha}"
        
        # Get changed files in commits
        result = _run_git_command(
            ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', commits_range],
            repo_root
        )
        
        # Find .changefile modifications
        changefiles = [
            line for line in result.stdout.strip().split('\n')
            if line and line.lower().endswith('.changefile')
        ]
        
        # Verify locks for each modified file
        for changefile_rel in changefiles:
            changefile = repo_root / changefile_rel
            if not changefile.exists():
                continue
            
            try:
                content = changefile.read_text()
                for line in content.split('\n'):
                    if 'FCStd_file_relpath=' in line:
                        fcstd_relpath = line.split('=', 1)[1].strip().strip("'\"")
                        fcstd_path = str(repo_root / fcstd_relpath)
                        
                        if fcstd_path not in user_locked_files:
                            print(f"Error: You don't have a lock on {fcstd_relpath}", file=sys.stderr)
                            print(f"Cannot push changes without lock", file=sys.stderr)
                            return 1
                        break
            except Exception as e:
                log.error(f"Failed to check lock for {changefile}: {e}")
                continue
        
        return 0
        
    except Exception as e:
        log.error(f"Pre-push hook failed: {e}")
        print(f"Error: Pre-push hook failed: {e}", file=sys.stderr)
        return 1
