"""
GitPDM Action Types

Shared types for the actions layer.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


@dataclass
class ActionResult:
    """
    Result from an action operation.
    
    Attributes:
        ok: True if operation succeeded
        message: Human-readable message (success or error)
        details: Optional dict with extra data (e.g., file counts, ahead/behind)
        error_code: Optional error code for programmatic handling
    """
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    error_code: Optional[str] = None
    
    @staticmethod
    def success(message: str, **details) -> ActionResult:
        """Create a success result."""
        return ActionResult(ok=True, message=message, details=details)
    
    @staticmethod
    def error(message: str, error_code: Optional[str] = None, **details) -> ActionResult:
        """Create an error result."""
        return ActionResult(ok=False, message=message, error_code=error_code, details=details)


class GitBackend(Protocol):
    """
    Protocol for git operations backend.
    Can be implemented by GitClient or ScriptRunner.
    """
    
    def is_git_available(self) -> bool:
        """Check if git is available."""
        ...
    
    def get_repo_root(self, path: str) -> Optional[str]:
        """Get repository root from path."""
        ...
    
    def init_repo(self, path: str) -> Any:
        """Initialize a new repository."""
        ...
    
    def get_status_porcelain(self, repo_root: str) -> Any:
        """Get git status in porcelain format."""
        ...
    
    def current_branch(self, repo_root: str) -> Optional[str]:
        """Get current branch name."""
        ...
    
    def get_upstream_ref(self, repo_root: str) -> Optional[str]:
        """Get upstream tracking branch."""
        ...
    
    def get_ahead_behind(self, repo_root: str, upstream: str) -> dict:
        """Get ahead/behind counts."""
        ...
    
    def stage_files(self, repo_root: str, files: list[str]) -> Any:
        """Stage files for commit."""
        ...
    
    def stage_all(self, repo_root: str) -> Any:
        """Stage all changes."""
        ...
    
    def commit(self, repo_root: str, message: str) -> Any:
        """Create a commit."""
        ...
    
    def push(self, repo_root: str, remote: str, branch: str) -> Any:
        """Push to remote."""
        ...
    
    def pull_ff_only(self, repo_root: str, remote: str, upstream: Optional[str]) -> Any:
        """Pull with fast-forward only."""
        ...
    
    def fetch(self, repo_root: str, remote: str) -> Any:
        """Fetch from remote."""
        ...
    
    def add_remote(self, repo_root: str, name: str, url: str) -> Any:
        """Add a remote."""
        ...
    
    def has_remote(self, repo_root: str, name: str) -> bool:
        """Check if remote exists."""
        ...


class SettingsProvider(Protocol):
    """Protocol for settings access."""
    
    def load_remote_name(self) -> str:
        """Load configured remote name."""
        ...
    
    def save_repo_path(self, path: str) -> None:
        """Save repository path."""
        ...
    
    def load_repo_path(self) -> str:
        """Load repository path."""
        ...


@dataclass
class ActionContext:
    """
    Context passed to action functions.
    
    Contains all dependencies an action needs (git backend, settings, etc.)
    without coupling to UI/Qt.
    """
    git: GitBackend
    settings: Optional[SettingsProvider] = None
    repo_root: Optional[str] = None
    remote_name: str = "origin"
