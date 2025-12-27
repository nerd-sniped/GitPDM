# -*- coding: utf-8 -*-
"""
GitPDM Git Client Module
Sprint 2: Minimal git wrapper using subprocess with fetch support
"""

import subprocess
import os
from datetime import datetime, timezone
from freecad_gitpdm.core import log


def _find_git_executable():
    """
    Find git executable, checking common Windows locations.
    
    Returns:
        str: Path to git.exe or 'git' if on PATH
    """
    # First try 'git' command (works if on PATH)
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return "git"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Common Git installation paths on Windows
    common_paths = [
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        os.path.expandvars(
            r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
        ),
        os.path.expandvars(
            r"%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app"
            r"\git\cmd\git.exe"
        ),
    ]
    
    for path in common_paths:
        # Handle wildcards in path
        if "*" in path:
            import glob
            matches = glob.glob(path)
            if matches:
                path = matches[0]
        
        if os.path.isfile(path):
            log.info(f"Found git at: {path}")
            return path
    
    return None


class GitClient:
    """
    Minimal git client using subprocess calls.
    All operations are local (no network).
    """

    def __init__(self):
        """Initialize GitClient"""
        self._git_available = None
        self._git_version = None
        self._git_exe = None

    def _get_git_command(self):
        """
        Get the git command to use.
        
        Returns:
            str or list: Git command/path
        """
        if self._git_exe is None:
            self._git_exe = _find_git_executable()
        return self._git_exe if self._git_exe else "git"

    def is_git_available(self):
        """
        Check whether git is available on PATH
        
        Returns:
            bool: True if git command is available
        """
        if self._git_available is not None:
            return self._git_available

        git_cmd = self._get_git_command()
        if git_cmd is None:
            self._git_available = False
            log.warning("Git not found on PATH or common locations")
            return False

        try:
            result = subprocess.run(
                [git_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            self._git_available = result.returncode == 0
            if self._git_available:
                self._git_version = result.stdout.strip()
                log.info(f"Git available: {self._git_version}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._git_available = False
            log.warning("Git not found on PATH or common locations")

        return self._git_available

    def git_version(self):
        """
        Get git version string
        
        Returns:
            str | None: Version string (e.g. "git version 2.35.1")
                or None if git not available
        """
        if not self.is_git_available():
            return None
        return self._git_version

    def get_repo_root(self, path):
        """
        Get the root directory of a git repository.
        Returns None if path is not inside a git repo.
        
        Args:
            path: Directory path to check (string)
            
        Returns:
            str | None: Repository root path or None if not a git repo
        """
        if not self.is_git_available():
            log.warning("Git not available for repo root check")
            return None

        if not path or not os.path.isdir(path):
            log.warning(f"Invalid path for repo check: {path}")
            return None

        git_cmd = self._get_git_command()

        try:
            result = subprocess.run(
                [git_cmd, "-C", path, "rev-parse",
                 "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode == 0:
                repo_root = result.stdout.strip()
                # Normalize path (git returns forward slashes on Windows)
                repo_root = os.path.normpath(repo_root)
                log.debug(f"Found repo root: {repo_root}")
                return repo_root
            else:
                log.warning(
                    f"Git command failed (exit {result.returncode}): "
                    f"{result.stderr.strip()}"
                )
        except subprocess.TimeoutExpired:
            log.warning("Git command timed out")
        except OSError as e:
            log.warning(f"Git command error: {e}")

        return None

    def current_branch(self, repo_root):
        """
        Get the current branch name.
        If HEAD is detached, returns "(detached)" with short SHA.
        
        Args:
            repo_root: Repository root path (string)
            
        Returns:
            str: Branch name, "(detached SHA)" or "(unknown)"
        """
        if not self.is_git_available():
            return "(unknown)"

        if not repo_root or not os.path.isdir(repo_root):
            return "(unknown)"

        git_cmd = self._get_git_command()

        try:
            result = subprocess.run(
                [git_cmd, "-C", repo_root, "branch",
                 "--show-current"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                if branch:
                    return branch
        except subprocess.TimeoutExpired:
            pass

        # Detached HEAD - get short SHA
        try:
            result = subprocess.run(
                [git_cmd, "-C", repo_root, "rev-parse",
                 "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode == 0:
                sha = result.stdout.strip()
                return f"(detached {sha})"
        except subprocess.TimeoutExpired:
            pass

        return "(unknown)"

    def status_summary(self, repo_root):
        """
        Get a summary of the working tree status.
        
        Args:
            repo_root: Repository root path (string)
            
        Returns:
            dict with keys:
                - is_clean: bool
                - modified: int
                - added: int
                - deleted: int
                - renamed: int
                - untracked: int
                - raw_lines: list[str] (for debugging)
        """
        result = {
            "is_clean": True,
            "modified": 0,
            "added": 0,
            "deleted": 0,
            "renamed": 0,
            "untracked": 0,
            "raw_lines": [],
        }

        if not self.is_git_available():
            return result

        if not repo_root or not os.path.isdir(repo_root):
            return result

        git_cmd = self._get_git_command()

        try:
            proc_result = subprocess.run(
                [git_cmd, "-C", repo_root, "status",
                 "--porcelain"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if proc_result.returncode != 0:
                return result

            lines = proc_result.stdout.strip().split("\n")
            lines = [line for line in lines if line]
            result["raw_lines"] = lines

            if not lines:
                result["is_clean"] = True
                return result

            result["is_clean"] = False

            for line in lines:
                if len(line) < 2:
                    continue

                status_code = line[:2]

                # Parse status codes (porcelain v1 format)
                if status_code[0] == 'M':
                    result["modified"] += 1
                elif status_code[0] == 'A':
                    result["added"] += 1
                elif status_code[0] == 'D':
                    result["deleted"] += 1
                elif status_code[0] == 'R':
                    result["renamed"] += 1

                if status_code[1] == '?':
                    result["untracked"] += 1

            return result

        except subprocess.TimeoutExpired:
            log.warning("Git status command timed out")
            return result
        except OSError as e:
            log.warning(f"Failed to run git status: {e}")
            return result

    def has_remote(self, repo_root, remote="origin"):
        """
        Check if a specific remote exists in the repository.
        
        Args:
            repo_root: Repository root path (string)
            remote: Remote name (default "origin")
            
        Returns:
            bool: True if remote exists
        """
        if not self.is_git_available():
            return False

        if not repo_root or not os.path.isdir(repo_root):
            return False

        git_cmd = self._get_git_command()

        try:
            result = subprocess.run(
                [git_cmd, "-C", repo_root, "remote"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                remotes = result.stdout.strip().split("\n")
                return remote in remotes
        except (subprocess.TimeoutExpired, OSError) as e:
            log.warning(f"Failed to list remotes: {e}")

        return False

    def fetch(self, repo_root, remote="origin"):
        """
        Fetch from remote repository.
        This contacts the network via git fetch.
        
        Args:
            repo_root: Repository root path (string)
            remote: Remote name (default "origin")
            
        Returns:
            dict with keys:
                - ok: bool
                - stdout: str
                - stderr: str
                - fetched_at: str (ISO 8601 UTC timestamp)
                - error: str | None
        """
        result = {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }

        if not self.is_git_available():
            result["error"] = "Git not available"
            return result

        if not repo_root or not os.path.isdir(repo_root):
            result["error"] = "Invalid repository path"
            return result

        git_cmd = self._get_git_command()

        try:
            proc_result = subprocess.run(
                [git_cmd, "-C", repo_root, "fetch", remote],
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes for fetch
            )
            result["ok"] = proc_result.returncode == 0
            result["stdout"] = proc_result.stdout.strip()
            result["stderr"] = proc_result.stderr.strip()

            if result["ok"]:
                log.info(f"Fetch completed: {remote}")
            else:
                result["error"] = (
                    f"Git fetch failed (exit {proc_result.returncode})"
                )
                log.warning(result["error"])

        except subprocess.TimeoutExpired:
            result["error"] = "Fetch timed out after 120 seconds"
            log.warning(result["error"])
        except OSError as e:
            result["error"] = f"Failed to run git fetch: {e}"
            log.warning(result["error"])

        return result

    def default_upstream_ref(self, repo_root, remote="origin"):
        """
        Determine the default upstream branch reference.
        Tries in order:
        1. symbolic-ref refs/remotes/origin/HEAD
        2. Check if origin/main exists
        3. Check if origin/master exists
        
        Args:
            repo_root: Repository root path (string)
            remote: Remote name (default "origin")
            
        Returns:
            str | None: Upstream ref like "origin/main" or None
        """
        if not self.is_git_available():
            return None

        if not repo_root or not os.path.isdir(repo_root):
            return None

        git_cmd = self._get_git_command()

        # Try symbolic-ref first
        try:
            result = subprocess.run(
                [git_cmd, "-C", repo_root, "symbolic-ref", "-q",
                 f"refs/remotes/{remote}/HEAD"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                ref = result.stdout.strip()
                # Convert refs/remotes/origin/main -> origin/main
                if ref.startswith("refs/remotes/"):
                    ref = ref[len("refs/remotes/") :]
                    log.debug(f"Found upstream via symbolic-ref: {ref}")
                    return ref
        except (subprocess.TimeoutExpired, OSError):
            pass

        # Try common default branches
        for branch in ["main", "master"]:
            try:
                result = subprocess.run(
                    [git_cmd, "-C", repo_root, "show-ref",
                     "--verify", "--quiet",
                     f"refs/remotes/{remote}/{branch}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    upstream = f"{remote}/{branch}"
                    log.debug(f"Found upstream branch: {upstream}")
                    return upstream
            except (subprocess.TimeoutExpired, OSError):
                pass

        log.debug("No default upstream reference found")
        return None

    def ahead_behind(self, repo_root, upstream):
        """
        Compute how many commits ahead/behind the current branch is
        compared to an upstream branch.
        
        Args:
            repo_root: Repository root path (string)
            upstream: Upstream ref like "origin/main"
            
        Returns:
            dict with keys:
                - ahead: int (commits ahead, or 0)
                - behind: int (commits behind, or 0)
                - ok: bool
                - error: str | None
        """
        result = {
            "ahead": 0,
            "behind": 0,
            "ok": False,
            "error": None,
        }

        if not self.is_git_available():
            result["error"] = "Git not available"
            return result

        if not repo_root or not os.path.isdir(repo_root):
            result["error"] = "Invalid repository path"
            return result

        if not upstream:
            result["error"] = "No upstream specified"
            return result

        git_cmd = self._get_git_command()

        try:
            proc_result = subprocess.run(
                [git_cmd, "-C", repo_root, "rev-list",
                 "--left-right", "--count",
                 f"HEAD...{upstream}"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if proc_result.returncode == 0:
                output = proc_result.stdout.strip()
                parts = output.split()
                if len(parts) == 2:
                    try:
                        result["ahead"] = int(parts[0])
                        result["behind"] = int(parts[1])
                        result["ok"] = True
                        log.debug(
                            f"Ahead/behind vs {upstream}: "
                            f"{result['ahead']}/{result['behind']}"
                        )
                    except ValueError:
                        result["error"] = (
                            f"Failed to parse rev-list output: {output}"
                        )
                else:
                    result["error"] = (
                        f"Unexpected rev-list output: {output}"
                    )
            else:
                result["error"] = (
                    f"Git rev-list failed: "
                    f"{proc_result.stderr.strip()}"
                )

        except subprocess.TimeoutExpired:
            result["error"] = "Git rev-list timed out"
        except OSError as e:
            result["error"] = f"Failed to run git rev-list: {e}"

        if result["error"]:
            log.debug(result["error"])

        return result

    def has_uncommitted_changes(self, repo_root):
        """
        Check whether the repository has uncommitted changes.
        Uses 'git status --porcelain' length to detect changes.
        
        Args:
            repo_root: Repository root path (string)
            
        Returns:
            bool: True if there are uncommitted changes
        """
        if not self.is_git_available():
            return False

        if not repo_root or not os.path.isdir(repo_root):
            return False

        git_cmd = self._get_git_command()

        try:
            result = subprocess.run(
                [git_cmd, "-C", repo_root, "status",
                 "--porcelain"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode != 0:
                return False

            # If output is non-empty, there are changes
            return len(result.stdout.strip()) > 0

        except (subprocess.TimeoutExpired, OSError) as e:
            log.warning(f"Failed to check uncommitted changes: {e}")
            return False

    def pull_ff_only(self, repo_root, remote="origin",
                     upstream=None):
        """
        Pull from upstream using fast-forward only strategy.
        If upstream is provided, pulls from that explicit ref.
        Otherwise runs 'git pull --ff-only' against the default.
        
        Args:
            repo_root: Repository root path (string)
            remote: Remote name (default "origin")
            upstream: Explicit upstream ref (e.g., "origin/main")
                      If None, uses 'git pull --ff-only'
            
        Returns:
            dict with keys:
                - ok: bool
                - stdout: str
                - stderr: str
                - error_code: str (category of error, or None if ok)
                - fetched_at: str (ISO 8601 UTC timestamp)
        """
        result = {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "error_code": None,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        if not self.is_git_available():
            result["error_code"] = "NO_GIT"
            return result

        if not repo_root or not os.path.isdir(repo_root):
            result["error_code"] = "INVALID_REPO"
            return result

        git_cmd = self._get_git_command()

        try:
            if upstream:
                # Extract branch name from upstream ref
                # e.g., "origin/main" -> "main"
                if "/" in upstream:
                    branch = upstream.split("/", 1)[1]
                else:
                    branch = upstream

                # Use: git pull --ff-only <remote> <branch>
                command = [git_cmd, "-C", repo_root,
                           "pull", "--ff-only", remote, branch]
            else:
                # Use: git pull --ff-only (default upstream)
                command = [git_cmd, "-C", repo_root,
                           "pull", "--ff-only"]

            proc_result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes for pull
            )

            result["stdout"] = proc_result.stdout.strip()
            result["stderr"] = proc_result.stderr.strip()
            result["ok"] = proc_result.returncode == 0

            if result["ok"]:
                log.info("Pull fast-forward completed successfully")
            else:
                # Classify the error
                result["error_code"] = self._classify_pull_error(
                    result["stderr"]
                )
                log.warning(
                    f"Pull failed with error code "
                    f"{result['error_code']}: {result['stderr']}"
                )

        except subprocess.TimeoutExpired:
            result["error_code"] = "TIMEOUT"
            log.warning("Pull timed out after 120 seconds")
        except OSError as e:
            result["error_code"] = "OS_ERROR"
            result["stderr"] = str(e)
            log.warning(f"Failed to run pull: {e}")

        return result

    def _classify_pull_error(self, stderr):
        """
        Classify a git pull error by inspecting stderr text.
        
        Args:
            stderr: Error output from git
            
        Returns:
            str: Error code category
        """
        stderr_lower = stderr.lower()

        # Check for dirty working tree
        if "working tree" in stderr_lower and "dirty" in stderr_lower:
            return "WORKING_TREE_DIRTY"
        if "please commit your changes" in stderr_lower:
            return "WORKING_TREE_DIRTY"
        if "local changes" in stderr_lower:
            return "WORKING_TREE_DIRTY"

        # Check for diverged/non-ff history
        if "not possible to fast-forward" in stderr_lower:
            return "DIVERGED_OR_NON_FF"
        if "commit before merging" in stderr_lower:
            return "DIVERGED_OR_NON_FF"
        if "conflict" in stderr_lower:
            return "DIVERGED_OR_NON_FF"

        # Check for authentication/permission issues
        if "authentication failed" in stderr_lower:
            return "AUTH_OR_PERMISSION"
        if "permission denied" in stderr_lower:
            return "AUTH_OR_PERMISSION"
        if "fatal: could not read" in stderr_lower:
            return "AUTH_OR_PERMISSION"

        # Check for no remote
        if "no such remote" in stderr_lower:
            return "NO_REMOTE"
        if "not a git repository" in stderr_lower:
            return "NO_REMOTE"
        if "does not appear to be a git repository" in \
                stderr_lower:
            return "NO_REMOTE"

        # Unknown error
        return "UNKNOWN_ERROR"
