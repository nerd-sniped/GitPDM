"""
Backend adapter for GitClient.

Makes the existing GitClient conform to the GitBackend protocol
used by actions.
"""

from freecad.gitpdm.git.client import GitClient, CmdResult


class GitClientBackend:
    """
    Adapter that wraps GitClient to implement the GitBackend protocol.
    
    This allows actions to work with the existing GitClient without
    knowing its implementation details.
    """
    
    def __init__(self, git_client: GitClient = None):
        """
        Initialize backend with a GitClient instance.
        
        Args:
            git_client: Existing GitClient (or creates new one)
        """
        self._git = git_client if git_client else GitClient()
    
    def is_git_available(self) -> bool:
        """Check if git is available."""
        return self._git.is_git_available()
    
    def get_repo_root(self, path: str) -> str | None:
        """Get repository root from path."""
        return self._git.get_repo_root(path)
    
    def init_repo(self, path: str) -> CmdResult:
        """Initialize a new repository."""
        return self._git.init_repo(path)
    
    def clone_repo(self, url: str, dest_path: str) -> CmdResult:
        """Clone a repository."""
        return self._git.clone_repo(url, dest_path)
    
    def get_status_porcelain(self, repo_root: str):
        """Get git status in porcelain format."""
        return self._git.get_status_porcelain(repo_root)
    
    def current_branch(self, repo_root: str) -> str | None:
        """Get current branch name."""
        return self._git.current_branch(repo_root)
    
    def get_upstream_ref(self, repo_root: str) -> str | None:
        """Get upstream tracking branch."""
        return self._git.get_upstream_ref(repo_root)
    
    def get_ahead_behind(self, repo_root: str, upstream: str) -> dict:
        """Get ahead/behind counts."""
        return self._git.get_ahead_behind(repo_root, upstream)
    
    def stage_files(self, repo_root: str, files: list[str]) -> CmdResult:
        """Stage specific files for commit."""
        return self._git.stage_files(repo_root, files)
    
    def stage_all(self, repo_root: str) -> CmdResult:
        """Stage all changes."""
        return self._git.stage_all(repo_root)
    
    def commit(self, repo_root: str, message: str) -> CmdResult:
        """Create a commit."""
        return self._git.commit(repo_root, message)
    
    def push(self, repo_root: str, remote: str, branch: str) -> CmdResult:
        """Push to remote."""
        return self._git.push(repo_root, remote, branch)
    
    def pull_ff_only(self, repo_root: str, remote: str, upstream: str | None) -> CmdResult:
        """Pull with fast-forward only."""
        return self._git.pull_ff_only(repo_root, remote, upstream)
    
    def fetch(self, repo_root: str, remote: str) -> CmdResult:
        """Fetch from remote."""
        return self._git.fetch(repo_root, remote)
    
    def add_remote(self, repo_root: str, name: str, url: str) -> CmdResult:
        """Add a remote."""
        return self._git.add_remote(repo_root, name, url)
    
    def has_remote(self, repo_root: str, name: str) -> bool:
        """Check if remote exists."""
        return self._git.has_remote(repo_root, name)
