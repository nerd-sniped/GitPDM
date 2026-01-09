"""
Status and file change actions.
"""

from freecad.gitpdm.actions.types import ActionContext, ActionResult
from freecad.gitpdm.core import log


def refresh_status(ctx: ActionContext) -> ActionResult:
    """
    Refresh repository status (branch, upstream, ahead/behind).
    
    Args:
        ctx: Action context with repo_root set
    
    Returns:
        ActionResult with details containing:
            - branch: current branch name
            - upstream: upstream ref (or None)
            - ahead: commits ahead of upstream
            - behind: commits behind upstream
            - has_remote: whether remote exists
    """
    if not ctx.repo_root:
        return ActionResult.error("No repository path", error_code="no_repo")
    
    if not ctx.git.is_git_available():
        return ActionResult.error("Git not available", error_code="git_not_found")
    
    # Get current branch
    branch = ctx.git.current_branch(ctx.repo_root)
    if not branch:
        return ActionResult.error(
            "Could not determine current branch",
            error_code="no_branch"
        )
    
    # Get upstream tracking branch
    upstream = ctx.git.get_upstream_ref(ctx.repo_root)
    
    # Get ahead/behind counts if we have upstream
    ahead = 0
    behind = 0
    
    if upstream:
        ab_result = ctx.git.get_ahead_behind(ctx.repo_root, upstream)
        if ab_result.get("ok"):
            ahead = ab_result.get("ahead", 0)
            behind = ab_result.get("behind", 0)
    
    # Check if remote exists
    remote_name = ctx.remote_name
    has_remote = ctx.git.has_remote(ctx.repo_root, remote_name)
    
    status_msg = f"Branch: {branch}"
    if upstream:
        status_msg += f", tracking {upstream}"
    if ahead > 0:
        status_msg += f", {ahead} ahead"
    if behind > 0:
        status_msg += f", {behind} behind"
    
    return ActionResult.success(
        status_msg,
        branch=branch,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        has_remote=has_remote
    )


def get_file_changes(ctx: ActionContext) -> ActionResult:
    """
    Get list of file changes (modified, added, deleted, untracked).
    
    Args:
        ctx: Action context with repo_root set
    
    Returns:
        ActionResult with details containing:
            - files: list of FileStatus objects
            - modified_count: count of modified files
            - staged_count: count of staged files
            - untracked_count: count of untracked files
    """
    if not ctx.repo_root:
        return ActionResult.error("No repository path", error_code="no_repo")
    
    if not ctx.git.is_git_available():
        return ActionResult.error("Git not available", error_code="git_not_found")
    
    status_result = ctx.git.get_status_porcelain(ctx.repo_root)
    
    if not status_result.ok:
        return ActionResult.error(
            f"Failed to get status: {status_result.stderr}",
            error_code="status_failed"
        )
    
    files = status_result.file_statuses
    
    # Count file types
    modified_count = sum(1 for f in files if not f.is_untracked)
    staged_count = sum(1 for f in files if f.is_staged)
    untracked_count = sum(1 for f in files if f.is_untracked)
    
    total = len(files)
    msg = f"{total} file(s) changed"
    if staged_count > 0:
        msg += f" ({staged_count} staged)"
    
    return ActionResult.success(
        msg,
        files=files,
        modified_count=modified_count,
        staged_count=staged_count,
        untracked_count=untracked_count
    )
