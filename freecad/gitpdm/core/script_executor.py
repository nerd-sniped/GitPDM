"""
Direct Script Executor - Minimal Python Wrapper

Ultra-thin wrapper for executing PowerShell/bash scripts directly from UI buttons.
Eliminates action layer, backend abstraction, and most Python code.

Usage from button handler:
    result = execute_script("git_commit.ps1", repo_path=path, message=msg)
    if result.success:
        show_success(result.output)
    else:
        show_error(result.error)
"""

import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScriptResult:
    """Minimal result wrapper."""
    success: bool
    output: str
    error: str
    exit_code: int


def execute_script(
    script_name: str,
    repo_path: Optional[str] = None,
    **kwargs
) -> ScriptResult:
    """
    Execute a PowerShell/bash script with minimal overhead.
    
    Args:
        script_name: Name of script file (e.g., "git_commit.ps1")
        repo_path: Repository path (passed as -RepoPath parameter)
        **kwargs: Additional parameters passed to script
        
    Returns:
        ScriptResult with success/output/error
        
    Example:
        # Commit button handler (3 lines):
        result = execute_script("git_commit.ps1", repo_path=path, message=msg, stage_all=True)
        if result.success:
            show_success("Committed!")
    """
    # Find script file
    scripts_dir = Path(__file__).parent.parent / "scripts"
    script_path = scripts_dir / script_name
    
    if not script_path.exists():
        return ScriptResult(
            success=False,
            output="",
            error=f"Script not found: {script_path}",
            exit_code=-1
        )
    
    # Build command
    if sys.platform == "win32":
        cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
    else:
        cmd = ["bash", str(script_path)]
    
    # Add parameters
    if repo_path:
        cmd.extend(["-RepoPath", repo_path])
    
    for key, value in kwargs.items():
        param_name = f"-{key.replace('_', '').title()}"
        if isinstance(value, bool):
            if value:  # Only add switch if True
                cmd.append(param_name)
        else:
            cmd.extend([param_name, str(value)])
    
    # Execute
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return ScriptResult(
            success=(result.returncode == 0),
            output=result.stdout.strip(),
            error=result.stderr.strip(),
            exit_code=result.returncode
        )
        
    except subprocess.TimeoutExpired:
        return ScriptResult(
            success=False,
            output="",
            error="Script execution timed out (30s)",
            exit_code=-1
        )
    except Exception as e:
        return ScriptResult(
            success=False,
            output="",
            error=str(e),
            exit_code=-1
        )


# Convenience functions for common operations

def script_commit(repo_path: str, message: str, stage_all: bool = False) -> ScriptResult:
    """1-line commit: script_commit(path, msg)"""
    return execute_script("git_commit.ps1", repo_path=repo_path, message=message, stage_all=stage_all)


def script_push(repo_path: str, force: bool = False) -> ScriptResult:
    """1-line push: script_push(path)"""
    return execute_script("git_push.ps1", repo_path=repo_path, force=force)


def script_fetch(repo_path: str) -> ScriptResult:
    """1-line fetch: script_fetch(path)"""
    return execute_script("git_fetch.ps1", repo_path=repo_path)


def script_pull(repo_path: str) -> ScriptResult:
    """1-line pull: script_pull(path)"""
    return execute_script("git_pull.ps1", repo_path=repo_path)


def script_validate(repo_path: str) -> ScriptResult:
    """1-line validate: script_validate(path)"""
    return execute_script("git_validate_repo.ps1", repo_path=repo_path)


def script_init(repo_path: str) -> ScriptResult:
    """1-line init: script_init(path)"""
    return execute_script("git_init_repo.ps1", repo_path=repo_path)


def script_status(repo_path: str) -> ScriptResult:
    """1-line status: script_status(path)"""
    return execute_script("git_status.ps1", repo_path=repo_path)


def script_add_remote(repo_path: str, name: str, url: str) -> ScriptResult:
    """1-line add remote: script_add_remote(path, 'origin', url)"""
    return execute_script("git_add_remote.ps1", repo_path=repo_path, name=name, url=url)
