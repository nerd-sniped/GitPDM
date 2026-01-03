# -*- coding: utf-8 -*-
"""
GitCAD Repository Detection and Validation
Utilities for detecting and validating GitCAD repositories.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

from freecad_gitpdm.core import log
from freecad_gitpdm.core.result import Result


@dataclass
class GitCADStatus:
    """Status of GitCAD in a repository."""

    is_initialized: bool
    has_config: bool
    has_fcstd_tool: bool
    has_init_script: bool
    has_git_hooks: bool
    config_valid: bool
    freecad_python_configured: bool
    missing_components: List[str]
    warnings: List[str]


def check_gitcad_status(repo_root: str) -> Result:
    """
    Check the status of GitCAD in a repository.
    
    Args:
        repo_root: Path to repository root
        
    Returns:
        Result containing GitCADStatus, or error
    """
    repo_path = Path(repo_root)
    automation_dir = repo_path / "FreeCAD_Automation"

    missing = []
    warnings = []

    # Check for automation directory
    if not automation_dir.exists():
        return Result.ok(
            GitCADStatus(
                is_initialized=False,
                has_config=False,
                has_fcstd_tool=False,
                has_init_script=False,
                has_git_hooks=False,
                config_valid=False,
                freecad_python_configured=False,
                missing_components=["FreeCAD_Automation directory"],
                warnings=["GitCAD not installed in this repository"],
            )
        )

    # Check for key files
    config_file = automation_dir / "config.json"
    has_config = config_file.exists()
    if not has_config:
        missing.append("config.json")

    fcstd_tool = automation_dir / "FCStdFileTool.py"
    has_fcstd_tool = fcstd_tool.exists()
    if not has_fcstd_tool:
        missing.append("FCStdFileTool.py")

    init_script = automation_dir / "user_scripts" / "init-repo"
    has_init_script = init_script.exists()
    if not has_init_script:
        missing.append("user_scripts/init-repo")

    # Check for git hooks
    git_hooks_dir = repo_path / ".git" / "hooks"
    has_hooks = False
    if git_hooks_dir.exists():
        # Check for key hooks
        required_hooks = ["pre-commit", "post-checkout", "post-merge"]
        hook_files = [git_hooks_dir / hook for hook in required_hooks]
        has_hooks = all(h.exists() for h in hook_files)

        if not has_hooks:
            missing_hooks = [h.name for h in hook_files if not h.exists()]
            warnings.append(
                f"Missing git hooks: {', '.join(missing_hooks)}. Run init-repo to install."
            )

    # Check config validity
    config_valid = False
    freecad_python_configured = False
    if has_config:
        from .config import load_gitcad_config

        config_result = load_gitcad_config(repo_root)
        if config_result.ok:
            config_valid = True
            config = config_result.value

            # Check if FreeCAD Python path is configured
            if config.freecad_python_instance_path:
                python_path = Path(config.freecad_python_instance_path)
                if python_path.exists():
                    freecad_python_configured = True
                else:
                    warnings.append(
                        f"FreeCAD Python path configured but not found: {python_path}"
                    )
            else:
                warnings.append(
                    "FreeCAD Python path not configured in config.json"
                )
        else:
            warnings.append(f"Config file invalid: {config_result.error}")

    # Determine if initialized
    is_initialized = has_config and has_fcstd_tool and has_init_script

    status = GitCADStatus(
        is_initialized=is_initialized,
        has_config=has_config,
        has_fcstd_tool=has_fcstd_tool,
        has_init_script=has_init_script,
        has_git_hooks=has_hooks,
        config_valid=config_valid,
        freecad_python_configured=freecad_python_configured,
        missing_components=missing,
        warnings=warnings,
    )

    return Result.ok(status)


def find_fcstd_files(repo_root: str, recursive: bool = True) -> List[str]:
    """
    Find all .FCStd files in a repository.
    
    Args:
        repo_root: Path to repository root
        recursive: If True, search recursively
        
    Returns:
        List of paths to .FCStd files (relative to repo root)
    """
    repo_path = Path(repo_root)
    pattern = "**/*.FCStd" if recursive else "*.FCStd"

    fcstd_files = []
    try:
        for fcstd_file in repo_path.glob(pattern):
            # Skip files in hidden directories (like .git)
            if any(part.startswith(".") for part in fcstd_file.parts):
                continue

            # Get relative path
            try:
                rel_path = fcstd_file.relative_to(repo_path)
                fcstd_files.append(str(rel_path))
            except ValueError:
                continue

    except Exception as e:
        log.error(f"Error finding .FCStd files: {e}")

    return fcstd_files


def get_fcstd_uncompressed_dir(
    fcstd_file_path: str, repo_root: str
) -> Optional[str]:
    """
    Get the uncompressed directory path for a .FCStd file.
    
    Args:
        fcstd_file_path: Path to .FCStd file (relative to repo root)
        repo_root: Path to repository root
        
    Returns:
        str: Path to uncompressed directory (relative to repo root), or None if not found
    """
    from .config import load_gitcad_config, get_uncompressed_dir_path

    # Load config to determine directory structure
    config_result = load_gitcad_config(repo_root)
    if not config_result.ok:
        log.warning(f"Failed to load config: {config_result.error}")
        return None

    config = config_result.value
    uncompressed_path = get_uncompressed_dir_path(fcstd_file_path, config, repo_root)

    # Check if directory exists
    full_path = Path(repo_root) / uncompressed_path
    if full_path.exists():
        return uncompressed_path

    return None


def is_fcstd_exported(fcstd_file_path: str, repo_root: str) -> bool:
    """
    Check if a .FCStd file has been exported (uncompressed directory exists).
    
    Args:
        fcstd_file_path: Path to .FCStd file (relative to repo root)
        repo_root: Path to repository root
        
    Returns:
        bool: True if exported
    """
    uncompressed_dir = get_fcstd_uncompressed_dir(fcstd_file_path, repo_root)
    return uncompressed_dir is not None
