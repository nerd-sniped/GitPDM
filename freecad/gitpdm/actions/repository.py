"""
Repository-level actions (validate, init, clone).
"""

import os
from freecad.gitpdm.actions.types import ActionContext, ActionResult
from freecad.gitpdm.core import log


def validate_repo(ctx: ActionContext, path: str) -> ActionResult:
    """
    Validate if a path is a valid git repository.
    
    Args:
        ctx: Action context with git backend
        path: Directory path to validate
    
    Returns:
        ActionResult with ok=True if valid repo, details contains repo_root
    """
    if not path:
        return ActionResult.error("No path provided", error_code="no_path")
    
    if not os.path.isdir(path):
        return ActionResult.error(f"Path does not exist: {path}", error_code="path_not_found")
    
    if not ctx.git.is_git_available():
        return ActionResult.error("Git is not available on PATH", error_code="git_not_found")
    
    repo_root = ctx.git.get_repo_root(path)
    
    if repo_root:
        return ActionResult.success(
            f"Valid repository",
            repo_root=repo_root
        )
    else:
        return ActionResult.error(
            "Not a git repository",
            error_code="not_a_repo"
        )


def init_repo(ctx: ActionContext, path: str) -> ActionResult:
    """
    Initialize a new git repository.
    
    Args:
        ctx: Action context
        path: Directory path where to create repository
    
    Returns:
        ActionResult indicating success/failure
    """
    if not path:
        return ActionResult.error("No path provided", error_code="no_path")
    
    if not os.path.isdir(path):
        return ActionResult.error(f"Path does not exist: {path}", error_code="path_not_found")
    
    if not ctx.git.is_git_available():
        return ActionResult.error("Git is not available on PATH", error_code="git_not_found")
    
    # Check if already a repo
    existing_root = ctx.git.get_repo_root(path)
    if existing_root:
        return ActionResult.error(
            f"Already a git repository: {existing_root}",
            error_code="already_repo"
        )
    
    result = ctx.git.init_repo(path)
    
    if result.ok:
        log.info(f"Repository initialized at: {path}")
        return ActionResult.success(
            f"Repository initialized",
            repo_root=path
        )
    else:
        log.error(f"Failed to initialize repo: {result.stderr}")
        return ActionResult.error(
            f"Failed to initialize repository: {result.stderr}",
            error_code=result.error_code or "init_failed"
        )


def clone_repo(ctx: ActionContext, url: str, dest_path: str) -> ActionResult:
    """
    Clone a repository from URL.
    
    Args:
        ctx: Action context
        url: Git repository URL
        dest_path: Local destination path
    
    Returns:
        ActionResult indicating success/failure
    """
    if not url:
        return ActionResult.error("No URL provided", error_code="no_url")
    
    if not dest_path:
        return ActionResult.error("No destination path provided", error_code="no_path")
    
    if not ctx.git.is_git_available():
        return ActionResult.error("Git is not available on PATH", error_code="git_not_found")
    
    # Check if destination already exists
    if os.path.exists(dest_path):
        return ActionResult.error(
            f"Destination already exists: {dest_path}",
            error_code="dest_exists"
        )
    
    result = ctx.git.clone_repo(url, dest_path)
    
    if result.ok:
        log.info(f"Repository cloned to: {dest_path}")
        return ActionResult.success(
            "Repository cloned successfully",
            repo_root=dest_path
        )
    else:
        log.error(f"Failed to clone repo: {result.stderr}")
        return ActionResult.error(
            f"Failed to clone repository: {result.stderr}",
            error_code=result.error_code or "clone_failed"
        )
