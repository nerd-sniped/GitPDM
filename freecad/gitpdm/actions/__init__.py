"""
GitPDM Actions Module

Pure-logic actions for git operations.
No Qt/UI dependencies - only business logic.

Each action:
- Takes an ActionContext
- Returns an ActionResult
- Is testable without FreeCAD/Qt
"""

from freecad.gitpdm.actions.types import ActionContext, ActionResult
from freecad.gitpdm.actions.backend import GitClientBackend
from freecad.gitpdm.actions.script_backend import ScriptBackend, create_script_backend
from freecad.gitpdm.actions.helpers import create_action_context
from freecad.gitpdm.actions.repository import (
    validate_repo,
    init_repo,
    clone_repo,
)
from freecad.gitpdm.actions.status import (
    refresh_status,
    get_file_changes,
)
from freecad.gitpdm.actions.commit_push import (
    commit_changes,
    push_changes,
)
from freecad.gitpdm.actions.fetch_pull import (
    fetch_from_remote,
    pull_from_remote,
)
from freecad.gitpdm.actions.remote import (
    add_remote,
    check_remote_exists,
)

__all__ = [
    "ActionContext",
    "ActionResult",
    "GitClientBackend",
    "ScriptBackend",
    "create_script_backend",
    "create_action_context",
    "validate_repo",
    "init_repo",
    "clone_repo",
    "refresh_status",
    "get_file_changes",
    "commit_changes",
    "push_changes",
    "fetch_from_remote",
    "pull_from_remote",
    "add_remote",
    "check_remote_exists",
]
