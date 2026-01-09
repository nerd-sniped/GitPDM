"""
Helper utilities for working with actions.
"""

from freecad.gitpdm.actions.types import ActionContext
from freecad.gitpdm.actions.backend import GitClientBackend


def create_action_context(
    git_client=None,
    settings=None,
    repo_root=None,
    remote_name="origin"
) -> ActionContext:
    """
    Create an ActionContext with sensible defaults.
    
    Args:
        git_client: GitClient instance (creates new if None)
        settings: Settings provider (uses core.settings if None)
        repo_root: Repository root path
        remote_name: Remote name (default "origin")
    
    Returns:
        ActionContext ready to use
    """
    # Wrap git_client in backend adapter
    backend = GitClientBackend(git_client)
    
    # Use default settings if not provided
    if settings is None:
        from freecad.gitpdm.core import settings as default_settings
        settings = default_settings
    
    # Load remote name from settings if not specified
    if remote_name == "origin" and settings:
        try:
            saved_remote = settings.load_remote_name()
            if saved_remote:
                remote_name = saved_remote
        except Exception:
            pass
    
    return ActionContext(
        git=backend,
        settings=settings,
        repo_root=repo_root,
        remote_name=remote_name
    )
