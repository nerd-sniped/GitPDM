# -*- coding: utf-8 -*-
"""
GitCAD Script Wrapper
Provides Python interface to GitCAD's bash scripts and tools.
Handles platform differences for bash execution.
"""

from __future__ import annotations

import subprocess
import sys
import os
import glob
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

from freecad_gitpdm.core import log
from freecad_gitpdm.core.result import Result


@dataclass
class LockInfo:
    """Information about a locked file."""

    path: str  # Path to .FCStd file (not .lockfile)
    owner: str  # Username who owns the lock
    lock_id: str  # LFS lock ID


@dataclass
class GitCADPaths:
    """Paths to GitCAD components in a repository."""

    automation_dir: Path
    config_file: Path
    fcstd_tool: Path
    init_script: Path
    lock_script: Path
    unlock_script: Path
    git_wrapper: Path


def _find_bash_executable() -> Optional[str]:
    """
    Find bash executable, checking platform-specific locations.
    
    Returns:
        str: Path to bash executable, or None if not found
    """
    if sys.platform == "win32":
        # Windows: Check common Git Bash locations
        common_paths = [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
            os.path.expandvars(r"%PROGRAMFILES%\Git\bin\bash.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\bin\bash.exe"),
        ]

        for path in common_paths:
            if os.path.isfile(path):
                log.info(f"Found bash at: {path}")
                return path

        # Try PATH as fallback
        try:
            result = subprocess.run(
                ["bash", "--version"],
                capture_output=True,
                text=True,
                timeout=2,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                return "bash"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        log.warning("Bash not found on Windows (Git Bash required)")
        return None
    else:
        # Linux/macOS: bash should be on PATH
        common_paths = [
            "/bin/bash",
            "/usr/bin/bash",
            "/usr/local/bin/bash",
        ]

        for path in common_paths:
            if os.path.isfile(path):
                return path

        # Try PATH
        try:
            result = subprocess.run(
                ["bash", "--version"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                return "bash"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        log.warning("Bash not found on system")
        return None


def _get_subprocess_kwargs():
    """Get platform-specific kwargs for subprocess to suppress console windows."""
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def _get_gitcad_paths(repo_root: str) -> Optional[GitCADPaths]:
    """
    Get paths to GitCAD components in a repository.
    
    Args:
        repo_root: Path to repository root
        
    Returns:
        GitCADPaths object, or None if GitCAD directory not found
    """
    automation_dir = Path(repo_root) / "FreeCAD_Automation"
    if not automation_dir.exists():
        log.debug(f"GitCAD automation directory not found: {automation_dir}")
        return None

    return GitCADPaths(
        automation_dir=automation_dir,
        config_file=automation_dir / "config.json",
        fcstd_tool=automation_dir / "FCStdFileTool.py",
        init_script=automation_dir / "user_scripts" / "init-repo",
        lock_script=automation_dir / "git_aliases" / "lock.sh",
        unlock_script=automation_dir / "git_aliases" / "unlock.sh",
        git_wrapper=automation_dir / "git",
    )


def is_gitcad_initialized(repo_root: str) -> bool:
    """
    Check if GitCAD is initialized in the repository.
    
    Args:
        repo_root: Path to repository root
        
    Returns:
        bool: True if GitCAD automation directory exists
    """
    paths = _get_gitcad_paths(repo_root)
    if paths is None:
        return False

    # Check for key components
    return (
        paths.automation_dir.exists()
        and paths.fcstd_tool.exists()
        and paths.init_script.exists()
    )


class GitCADWrapper:
    """
    Wrapper for executing GitCAD bash scripts from Python.
    Handles platform differences and provides high-level interface.
    """

    def __init__(self, repo_root: str):
        """
        Initialize wrapper for a repository.
        
        Args:
            repo_root: Path to repository root
            
        Raises:
            ValueError: If GitCAD not found in repository
        """
        self.repo_root = Path(repo_root).resolve()
        self.paths = _get_gitcad_paths(str(self.repo_root))

        if self.paths is None:
            raise ValueError(f"GitCAD not found in repository: {repo_root}")

        self._bash_exe = _find_bash_executable()
        if self._bash_exe is None:
            raise RuntimeError("Bash executable not found (required for GitCAD)")

    def _run_bash_script(
        self,
        script_path: Path,
        args: List[str],
        env_vars: Optional[dict] = None,
    ) -> Tuple[bool, str, str]:
        """
        Run a bash script with arguments.
        
        Args:
            script_path: Path to bash script
            args: List of arguments to pass to script
            env_vars: Optional environment variables to set
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        if not script_path.exists():
            return False, "", f"Script not found: {script_path}"

        cmd = [self._bash_exe, str(script_path)] + args

        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        try:
            log.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                env=env,
                **_get_subprocess_kwargs(),
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", "Script execution timed out (5 minutes)"
        except Exception as e:
            return False, "", f"Script execution failed: {e}"

    def lock_file(self, file_path: str, force: bool = False) -> Result:
        """
        Lock a .FCStd file using GitCAD's locking system.
        
        Args:
            file_path: Path to .FCStd file (relative to repo root or absolute)
            force: If True, force lock (steal from other user)
            
        Returns:
            Result indicating success/failure
        """
        # Convert to relative path if absolute
        file_path_obj = Path(file_path)
        if file_path_obj.is_absolute():
            try:
                file_path = str(file_path_obj.relative_to(self.repo_root))
            except ValueError:
                return Result.failure("GITCAD_ERROR", f"File not in repository: {file_path}")

        args = ["", file_path]  # First arg is GIT_PREFIX (caller subdir)
        if force:
            args.append("--force")

        success, stdout, stderr = self._run_bash_script(self.paths.lock_script, args)

        if success:
            return Result.success(f"Locked: {file_path}")
        else:
            return Result.failure("GITCAD_ERROR", f"Lock failed: {stderr}")

    def unlock_file(self, file_path: str, force: bool = False) -> Result:
        """
        Unlock a .FCStd file using GitCAD's locking system.
        
        Args:
            file_path: Path to .FCStd file (relative to repo root or absolute)
            force: If True, force unlock (break lock from other user)
            
        Returns:
            Result indicating success/failure
        """
        # Convert to relative path if absolute
        file_path_obj = Path(file_path)
        if file_path_obj.is_absolute():
            try:
                file_path = str(file_path_obj.relative_to(self.repo_root))
            except ValueError:
                return Result.failure("GITCAD_ERROR", f"File not in repository: {file_path}")

        args = ["", file_path]  # First arg is GIT_PREFIX (caller subdir)
        if force:
            args.append("--force")

        success, stdout, stderr = self._run_bash_script(
            self.paths.unlock_script, args
        )

        if success:
            return Result.success(f"Unlocked: {file_path}")
        else:
            return Result.failure("GITCAD_ERROR", f"Unlock failed: {stderr}")

    def get_locks(self) -> Result:
        """
        Get list of currently locked files in the repository.
        
        Returns:
            Result containing list of LockInfo objects, or error
        """
        try:
            result = subprocess.run(
                ["git", "lfs", "locks"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=10,
                **_get_subprocess_kwargs(),
            )

            if result.returncode != 0:
                return Result.failure("GITCAD_ERROR", f"Failed to get locks: {result.stderr}")

            locks = []
            for line in result.stdout.strip().splitlines():
                # Parse: "path/to/.lockfile  username  ID:123"
                parts = line.split()
                if len(parts) >= 3 and parts[2].startswith("ID:"):
                    lockfile_path = parts[0]
                    owner = parts[1]
                    lock_id = parts[2][3:]  # Remove "ID:" prefix

                    # Convert .lockfile path to .FCStd path
                    # .lockfile is in: path/to/file.FCStd_uncompressed/.lockfile
                    # We need: path/to/file.FCStd
                    fcstd_path = lockfile_path.replace("/.lockfile", "")
                    # Remove uncompressed suffix (configurable, but default is _uncompressed)
                    # For now, assume pattern: basename_uncompressed
                    parts = fcstd_path.rsplit("/", 1)
                    if len(parts) == 2:
                        dir_path, dir_name = parts
                        # Try to strip suffix
                        for suffix in ["_uncompressed", "_data", ""]:
                            if dir_name.endswith(suffix) and suffix:
                                fcstd_name = dir_name[: -len(suffix)]
                                fcstd_path = f"{dir_path}/{fcstd_name}.FCStd"
                                break
                    else:
                        # Root directory
                        dir_name = parts[0]
                        for suffix in ["_uncompressed", "_data", ""]:
                            if dir_name.endswith(suffix) and suffix:
                                fcstd_name = dir_name[: -len(suffix)]
                                fcstd_path = f"{fcstd_name}.FCStd"
                                break

                    locks.append(LockInfo(path=fcstd_path, owner=owner, lock_id=lock_id))

            return Result.success(locks)

        except Exception as e:
            return Result.failure("GITCAD_ERROR", f"Failed to get locks: {e}")

    def export_fcstd(self, file_path: str) -> Result:
        """
        Export (decompress) a .FCStd file to its uncompressed directory.
        Uses GitCAD's FCStdFileTool.py.
        
        Args:
            file_path: Path to .FCStd file (relative to repo root or absolute)
            
        Returns:
            Result indicating success/failure
        """
        # Convert to absolute path
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            file_path_obj = self.repo_root / file_path

        if not file_path_obj.exists():
            return Result.failure("GITCAD_ERROR", f"File not found: {file_path}")

        # Get Python executable from config
        from .config import load_gitcad_config

        config_result = load_gitcad_config(str(self.repo_root))
        if not config_result.ok:
            return Result.failure("GITCAD_ERROR", f"Failed to load config: {config_result.error}")

        config = config_result.value
        python_path = config.freecad_python_instance_path

        if not python_path or not Path(python_path).exists():
            return Result.failure("GITCAD_ERROR", 
                "FreeCAD executable path not configured or not found in config.json"
            )

        # Run FCStdFileTool using FreeCAD with the script as first argument
        # FreeCAD automatically runs .py files in console mode
        cmd = [
            python_path,
            str(self.paths.fcstd_tool),
            "--CONFIG-FILE",
            str(self.paths.config_file),
            "--export",
            str(file_path_obj),
        ]

        try:
            log.debug(f"Exporting: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                **_get_subprocess_kwargs(),
            )

            if result.returncode == 0:
                return Result.success(f"Exported: {file_path}")
            else:
                return Result.failure("GITCAD_ERROR", f"Export failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            return Result.failure("GITCAD_ERROR", "Export timed out (2 minutes)")
        except Exception as e:
            return Result.failure("GITCAD_ERROR", f"Export failed: {e}")

    def import_fcstd(self, file_path: str) -> Result:
        """
        Import (compress) uncompressed directory into a .FCStd file.
        Uses GitCAD's FCStdFileTool.py.
        
        Args:
            file_path: Path to .FCStd file (relative to repo root or absolute)
            
        Returns:
            Result indicating success/failure
        """
        # Convert to absolute path
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            file_path_obj = self.repo_root / file_path

        # Get Python executable from config
        from .config import load_gitcad_config

        config_result = load_gitcad_config(str(self.repo_root))
        if not config_result.ok:
            return Result.failure("GITCAD_ERROR", f"Failed to load config: {config_result.error}")

        config = config_result.value
        python_path = config.freecad_python_instance_path

        if not python_path or not Path(python_path).exists():
            return Result.failure("GITCAD_ERROR", 
                "FreeCAD executable path not configured or not found in config.json"
            )

        # Run FCStdFileTool using FreeCAD with the script as first argument
        # FreeCAD automatically runs .py files in console mode
        cmd = [
            python_path,
            str(self.paths.fcstd_tool),
            "--CONFIG-FILE",
            str(self.paths.config_file),
            "--import",
            str(file_path_obj),
        ]

        try:
            log.debug(f"Importing: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                **_get_subprocess_kwargs(),
            )

            if result.returncode == 0:
                return Result.success(f"Imported: {file_path}")
            else:
                return Result.failure("GITCAD_ERROR", f"Import failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            return Result.failure("GITCAD_ERROR", "Import timed out (2 minutes)")
        except Exception as e:
            return Result.failure("GITCAD_ERROR", f"Import failed: {e}")

    def init_repository(self) -> Result:
        """
        Initialize GitCAD in the repository by running init-repo script.
        Note: This requires config.json to be pre-configured.
        
        Returns:
            Result indicating success/failure
        """
        if not self.paths.init_script.exists():
            return Result.failure("GITCAD_ERROR", f"Init script not found: {self.paths.init_script}")

        success, stdout, stderr = self._run_bash_script(self.paths.init_script, [])

        if success:
            return Result.success("GitCAD initialized successfully")
        else:
            return Result.failure("GITCAD_ERROR", f"Initialization failed: {stderr}\n{stdout}")


# Convenience functions for quick access without creating wrapper instance


def init_repository(repo_root: str) -> Result:
    """Initialize GitCAD in a repository."""
    try:
        wrapper = GitCADWrapper(repo_root)
        return wrapper.init_repository()
    except Exception as e:
        return Result.failure("GITCAD_ERROR", str(e))


def lock_file(repo_root: str, file_path: str, force: bool = False) -> Result:
    """Lock a .FCStd file."""
    try:
        wrapper = GitCADWrapper(repo_root)
        return wrapper.lock_file(file_path, force)
    except Exception as e:
        return Result.failure("GITCAD_ERROR", str(e))


def unlock_file(repo_root: str, file_path: str, force: bool = False) -> Result:
    """Unlock a .FCStd file."""
    try:
        wrapper = GitCADWrapper(repo_root)
        return wrapper.unlock_file(file_path, force)
    except Exception as e:
        return Result.failure("GITCAD_ERROR", str(e))


def export_fcstd(repo_root: str, file_path: str) -> Result:
    """Export (decompress) a .FCStd file."""
    try:
        wrapper = GitCADWrapper(repo_root)
        return wrapper.export_fcstd(file_path)
    except Exception as e:
        return Result.failure("GITCAD_ERROR", str(e))


def import_fcstd(repo_root: str, file_path: str) -> Result:
    """Import (compress) a .FCStd file."""
    try:
        wrapper = GitCADWrapper(repo_root)
        return wrapper.import_fcstd(file_path)
    except Exception as e:
        return Result.failure("GITCAD_ERROR", str(e))


def get_locks(repo_root: str) -> Result:
    """Get list of locked files."""
    try:
        wrapper = GitCADWrapper(repo_root)
        return wrapper.get_locks()
    except Exception as e:
        return Result.failure("GITCAD_ERROR", str(e))
