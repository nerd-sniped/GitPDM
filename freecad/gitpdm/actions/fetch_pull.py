"""
Fetch and pull actions.
"""

from freecad.gitpdm.actions.types import ActionContext, ActionResult
from freecad.gitpdm.core import log


def fetch_from_remote(ctx: ActionContext) -> ActionResult:
    """
    Fetch changes from remote repository.
    
    Args:
        ctx: Action context with repo_root set
    
    Returns:
        ActionResult indicating success/failure
    """
    if not ctx.repo_root:
        return ActionResult.error("No repository path", error_code="no_repo")
    
    if not ctx.git.is_git_available():
        return ActionResult.error("Git not available", error_code="git_not_found")
    
    # Check if remote exists
    remote_name = ctx.remote_name
    if not ctx.git.has_remote(ctx.repo_root, remote_name):
        return ActionResult.error(
            f"Remote '{remote_name}' not found",
            error_code="no_remote"
        )
    
    # Fetch
    fetch_result = ctx.git.fetch(ctx.repo_root, remote_name)
    
    if fetch_result.ok:
        log.info(f"Fetch successful from {remote_name}")
        
        # Save timestamp if settings available
        if ctx.settings:
            from datetime import datetime, timezone
            ctx.settings.save_last_fetch_at(datetime.now(timezone.utc).isoformat())
        
        return ActionResult.success(
            f"Fetched from {remote_name}",
            remote=remote_name
        )
    else:
        stderr = fetch_result.stderr
        
        # Provide helpful error messages
        if "authentication" in stderr.lower() or "permission" in stderr.lower():
            return ActionResult.error(
                "Authentication failed. Check your credentials.",
                error_code="auth_failed"
            )
        elif "could not resolve host" in stderr.lower():
            return ActionResult.error(
                "Could not connect to remote. Check network connection.",
                error_code="network_error"
            )
        
        log.error(f"Fetch failed: {stderr}")
        return ActionResult.error(
            f"Failed to fetch: {stderr}",
            error_code=fetch_result.error_code or "fetch_failed"
        )


def pull_from_remote(ctx: ActionContext) -> ActionResult:
    """
    Pull changes from remote repository (fast-forward only).
    
    Args:
        ctx: Action context with repo_root set
    
    Returns:
        ActionResult indicating success/failure
    """
    if not ctx.repo_root:
        return ActionResult.error("No repository path", error_code="no_repo")
    
    if not ctx.git.is_git_available():
        return ActionResult.error("Git not available", error_code="git_not_found")
    
    # Get upstream
    upstream = ctx.git.get_upstream_ref(ctx.repo_root)
    if not upstream:
        return ActionResult.error(
            "No upstream tracking branch set",
            error_code="no_upstream"
        )
    
    # Pull with fast-forward only
    remote_name = ctx.remote_name
    pull_result = ctx.git.pull_ff_only(ctx.repo_root, remote_name, upstream)
    
    if pull_result.ok:
        log.info(f"Pull successful from {remote_name}")
        
        # Save timestamp if settings available
        if ctx.settings:
            from datetime import datetime, timezone
            ctx.settings.save_last_pull_at(datetime.now(timezone.utc).isoformat())
        
        return ActionResult.success(
            f"Pulled from {remote_name}",
            remote=remote_name
        )
    else:
        stderr = pull_result.stderr
        
        # Provide helpful error messages for common cases
        if "not possible to fast-forward" in stderr.lower():
            return ActionResult.error(
                "Cannot fast-forward. You have local commits that conflict with remote.",
                error_code="cannot_ff"
            )
        elif "authentication" in stderr.lower() or "permission" in stderr.lower():
            return ActionResult.error(
                "Authentication failed. Check your credentials.",
                error_code="auth_failed"
            )
        elif "could not resolve host" in stderr.lower():
            return ActionResult.error(
                "Could not connect to remote. Check network connection.",
                error_code="network_error"
            )
        
        log.error(f"Pull failed: {stderr}")
        return ActionResult.error(
            f"Failed to pull: {stderr}",
            error_code=pull_result.error_code or "pull_failed"
        )
