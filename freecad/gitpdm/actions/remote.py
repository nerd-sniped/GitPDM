"""
Remote management actions.
"""

from freecad.gitpdm.actions.types import ActionContext, ActionResult
from freecad.gitpdm.core import log


def add_remote(ctx: ActionContext, name: str, url: str) -> ActionResult:
    """
    Add a remote to the repository.
    
    Args:
        ctx: Action context with repo_root set
        name: Remote name (e.g., "origin")
        url: Remote URL
    
    Returns:
        ActionResult indicating success/failure
    """
    if not ctx.repo_root:
        return ActionResult.error("No repository path", error_code="no_repo")
    
    if not name or not name.strip():
        return ActionResult.error("Remote name is required", error_code="no_name")
    
    if not url or not url.strip():
        return ActionResult.error("Remote URL is required", error_code="no_url")
    
    if not ctx.git.is_git_available():
        return ActionResult.error("Git not available", error_code="git_not_found")
    
    # Check if remote already exists
    if ctx.git.has_remote(ctx.repo_root, name):
        return ActionResult.error(
            f"Remote '{name}' already exists",
            error_code="remote_exists"
        )
    
    # Add remote
    add_result = ctx.git.add_remote(ctx.repo_root, name.strip(), url.strip())
    
    if add_result.ok:
        log.info(f"Remote '{name}' added: {url}")
        return ActionResult.success(
            f"Remote '{name}' added successfully",
            name=name,
            url=url
        )
    else:
        log.error(f"Failed to add remote: {add_result.stderr}")
        return ActionResult.error(
            f"Failed to add remote: {add_result.stderr}",
            error_code=add_result.error_code or "add_remote_failed"
        )


def check_remote_exists(ctx: ActionContext, name: str) -> ActionResult:
    """
    Check if a remote exists in the repository.
    
    Args:
        ctx: Action context with repo_root set
        name: Remote name to check
    
    Returns:
        ActionResult with ok=True if remote exists
    """
    if not ctx.repo_root:
        return ActionResult.error("No repository path", error_code="no_repo")
    
    if not name or not name.strip():
        return ActionResult.error("Remote name is required", error_code="no_name")
    
    if not ctx.git.is_git_available():
        return ActionResult.error("Git not available", error_code="git_not_found")
    
    exists = ctx.git.has_remote(ctx.repo_root, name.strip())
    
    if exists:
        return ActionResult.success(
            f"Remote '{name}' exists",
            name=name,
            exists=True
        )
    else:
        return ActionResult.success(
            f"Remote '{name}' does not exist",
            name=name,
            exists=False
        )
