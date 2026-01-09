"""
Commit and push actions.
"""

from freecad.gitpdm.actions.types import ActionContext, ActionResult
from freecad.gitpdm.core import log


def commit_changes(ctx: ActionContext, message: str, stage_all: bool = False) -> ActionResult:
    """
    Commit changes to the repository.
    
    Args:
        ctx: Action context with repo_root set
        message: Commit message
        stage_all: If True, stage all changes before committing
    
    Returns:
        ActionResult indicating success/failure
    """
    if not ctx.repo_root:
        return ActionResult.error("No repository path", error_code="no_repo")
    
    if not message or not message.strip():
        return ActionResult.error("Commit message is required", error_code="no_message")
    
    if not ctx.git.is_git_available():
        return ActionResult.error("Git not available", error_code="git_not_found")
    
    # Stage files if requested
    if stage_all:
        stage_result = ctx.git.stage_all(ctx.repo_root)
        if not stage_result.ok:
            return ActionResult.error(
                f"Failed to stage files: {stage_result.stderr}",
                error_code="stage_failed"
            )
    
    # Commit
    commit_result = ctx.git.commit(ctx.repo_root, message.strip())
    
    if commit_result.ok:
        log.info(f"Commit successful: {message}")
        return ActionResult.success(
            "Changes committed successfully",
            message=message
        )
    else:
        # Check for "nothing to commit" case
        stderr = commit_result.stderr.lower()
        if "nothing to commit" in stderr or "no changes added" in stderr:
            return ActionResult.error(
                "No changes to commit",
                error_code="nothing_to_commit"
            )
        
        log.error(f"Commit failed: {commit_result.stderr}")
        return ActionResult.error(
            f"Failed to commit: {commit_result.stderr}",
            error_code=commit_result.error_code or "commit_failed"
        )


def push_changes(ctx: ActionContext, force: bool = False) -> ActionResult:
    """
    Push commits to remote repository.
    
    Args:
        ctx: Action context with repo_root set
        force: If True, force push (use with caution)
    
    Returns:
        ActionResult indicating success/failure
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
    
    # Check if remote exists
    remote_name = ctx.remote_name
    if not ctx.git.has_remote(ctx.repo_root, remote_name):
        return ActionResult.error(
            f"Remote '{remote_name}' not found. Add a remote first.",
            error_code="no_remote"
        )
    
    # Push
    push_result = ctx.git.push(ctx.repo_root, remote_name, branch)
    
    if push_result.ok:
        log.info(f"Push successful to {remote_name}/{branch}")
        return ActionResult.success(
            f"Pushed to {remote_name}/{branch}",
            remote=remote_name,
            branch=branch
        )
    else:
        stderr = push_result.stderr
        
        # Provide helpful error messages for common cases
        if "rejected" in stderr.lower() and "non-fast-forward" in stderr.lower():
            return ActionResult.error(
                "Push rejected: Remote has changes you don't have. Pull first.",
                error_code="push_rejected_behind"
            )
        elif "no upstream" in stderr.lower():
            return ActionResult.error(
                f"No upstream branch set. Try: git push -u {remote_name} {branch}",
                error_code="no_upstream"
            )
        elif "authentication" in stderr.lower() or "permission" in stderr.lower():
            return ActionResult.error(
                "Authentication failed. Check your credentials.",
                error_code="auth_failed"
            )
        
        log.error(f"Push failed: {stderr}")
        return ActionResult.error(
            f"Failed to push: {stderr}",
            error_code=push_result.error_code or "push_failed"
        )
