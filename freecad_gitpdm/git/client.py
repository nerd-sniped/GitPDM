# -*- coding: utf-8 -*-
"""
GitPDM Git Client Module
Sprint 2: Minimal git wrapper using subprocess with fetch support
Sprint PERF: Suppress terminal windows on Windows
"""

from __future__ import annotations

import subprocess
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from freecad_gitpdm.core import log
from freecad_gitpdm.core.result import Result


# Sprint PERF: Windows subprocess configuration to suppress console windows
def _get_subprocess_kwargs():
    """
    Get platform-specific kwargs for subprocess to suppress console windows.

    Returns:
        dict: kwargs to pass to subprocess.run/Popen
    """
    kwargs = {}
    if sys.platform == "win32":
        # Suppress console window on Windows
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


# Status kinds for porcelain parsing
STATUS_MODIFIED = "MODIFIED"
STATUS_ADDED = "ADDED"
STATUS_DELETED = "DELETED"
STATUS_RENAMED = "RENAMED"
STATUS_COPIED = "COPIED"
STATUS_UNTRACKED = "UNTRACKED"
STATUS_CONFLICT = "CONFLICT"
STATUS_UNKNOWN = "UNKNOWN"


@dataclass
class FileStatus:
    """Structured representation of a porcelain status entry."""

    path: str
    x: str
    y: str
    kind: str
    is_staged: bool
    is_untracked: bool


@dataclass
class CmdResult:
    """Simple command result wrapper."""

    ok: bool
    stdout: str
    stderr: str
    error_code: Optional[str] = None


def _find_git_executable():
    """
    Find git executable, checking common platform-specific locations.

    Returns:
        str: Path to git or 'git' if on PATH
    """
    import sys

    if sys.platform == "win32":
        # Windows: Prefer GitHub Desktop git so we leverage its credential helper
        # (helps avoid AUTH errors when users are signed in to Desktop).
        common_paths = [
            os.path.expandvars(
                r"%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app"
                r"\git\cmd\git.exe"
            ),
            r"C:\\Program Files\\Git\\cmd\\git.exe",
            r"C:\\Program Files (x86)\\Git\\cmd\\git.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe"),
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
    else:
        # Linux/macOS: Check common system paths
        common_paths = [
            "/usr/bin/git",
            "/usr/local/bin/git",
            "/opt/local/bin/git",  # MacPorts
            "/opt/homebrew/bin/git",  # Homebrew on Apple Silicon
        ]

        for path in common_paths:
            if os.path.isfile(path):
                log.info(f"Found git at: {path}")
                return path

    # Fallback to PATH
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=2,
            **_get_subprocess_kwargs(),
        )
        if result.returncode == 0:
            return "git"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
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
                timeout=10,
                **_get_subprocess_kwargs(),
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
                [git_cmd, "-C", path, "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=15,
                **_get_subprocess_kwargs(),
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

    def init_repo(self, path):
        """
        Initialize a new git repository in the given path.

        Args:
            path: Directory path where to create the repository (string)

        Returns:
            CmdResult: Result of the init operation
        """
        if not self.is_git_available():
            log.error("Git not available for repo init")
            return CmdResult(
                ok=False, stdout="", stderr="Git not available", error_code="no_git"
            )

        if not path or not os.path.isdir(path):
            log.error(f"Invalid path for repo init: {path}")
            return CmdResult(
                ok=False, stdout="", stderr="Path does not exist", error_code="bad_path"
            )

        git_cmd = self._get_git_command()

        try:
            result = subprocess.run(
                [git_cmd, "-C", path, "init"],
                capture_output=True,
                text=True,
                timeout=15,
                **_get_subprocess_kwargs(),
            )
            if result.returncode == 0:
                log.info(f"Repository initialized at: {path}")
                return CmdResult(ok=True, stdout=result.stdout.strip(), stderr="")
            else:
                log.error(
                    f"Git init failed (exit {result.returncode}): "
                    f"{result.stderr.strip()}"
                )
                return CmdResult(
                    ok=False,
                    stdout=result.stdout.strip(),
                    stderr=result.stderr.strip(),
                    error_code="init_failed",
                )
        except subprocess.TimeoutExpired:
            log.error("Git init command timed out")
            return CmdResult(
                ok=False, stdout="", stderr="Command timed out", error_code="timeout"
            )
        except OSError as e:
            log.error(f"Git init error: {e}")
            return CmdResult(ok=False, stdout="", stderr=str(e), error_code="os_error")

    def add_remote(self, repo_root, name, url):
        """
        Add a remote to the repository.
        Uses the Git executable (from PATH or GitHub Desktop) so credentials
        are handled by the Git credential helper (e.g., GitHub Desktop).

        Args:
            repo_root: str - repository root path
            name: str - remote name (e.g., "origin")
            url: str - remote URL

        Returns:
            CmdResult indicating success/failure
        """
        if not self.is_git_available():
            log.error("Git not available for adding remote")
            return CmdResult(
                ok=False, stdout="", stderr="Git not available", error_code="no_git"
            )

        if not repo_root or not os.path.isdir(repo_root):
            log.error(f"Invalid repo root for add_remote: {repo_root}")
            return CmdResult(
                ok=False,
                stdout="",
                stderr="Invalid repository path",
                error_code="bad_path",
            )

        url = (url or "").strip()
        name = (name or "").strip()
        if not url or not name:
            log.error("Missing remote name or URL for add_remote")
            return CmdResult(
                ok=False,
                stdout="",
                stderr="Missing remote name or URL",
                error_code="bad_args",
            )

        git_cmd = self._get_git_command()

        try:
            result = subprocess.run(
                [git_cmd, "-C", repo_root, "remote", "add", name, url],
                capture_output=True,
                text=True,
                timeout=15,
                **_get_subprocess_kwargs(),
            )
            if result.returncode == 0:
                log.info(f"Remote '{name}' added: {url}")
                return CmdResult(ok=True, stdout=result.stdout.strip(), stderr="")

            stderr = result.stderr.strip()
            log.error(f"Git remote add failed (exit {result.returncode}): {stderr}")
            error_code = "add_remote_failed"
            if "already exists" in stderr.lower():
                error_code = "remote_exists"
            return CmdResult(
                ok=False,
                stdout=result.stdout.strip(),
                stderr=stderr,
                error_code=error_code,
            )
        except subprocess.TimeoutExpired:
            log.error("Git remote add timed out")
            return CmdResult(
                ok=False, stdout="", stderr="Command timed out", error_code="timeout"
            )
        except OSError as e:
            log.error(f"Git remote add error: {e}")
            return CmdResult(ok=False, stdout="", stderr=str(e), error_code="os_error")

    def clone_repo(self, clone_url: str, dest_path: str) -> CmdResult:
        """Clone a repository to dest_path using https clone URL."""
        if not self.is_git_available():
            log.error("Git not available for clone")
            return CmdResult(False, "", "Git not available", error_code="no_git")

        clone_url = (clone_url or "").strip()
        dest_path = (dest_path or "").strip()
        if not clone_url or not dest_path:
            log.error("Missing clone URL or destination for clone")
            return CmdResult(
                False, "", "Missing clone URL or destination", error_code="bad_args"
            )

        git_cmd = self._get_git_command()
        dest_abs = os.path.abspath(dest_path)
        parent_dir = os.path.dirname(dest_abs)
        try:
            if parent_dir and not os.path.isdir(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            if os.path.isdir(dest_abs):
                try:
                    existing = os.listdir(dest_abs)
                except OSError:
                    existing = []
                if existing:
                    log.warning(
                        "Destination folder already contains files; aborting clone"
                    )
                    return CmdResult(
                        False,
                        "",
                        "Destination folder is not empty.",
                        error_code="dest_not_empty",
                    )

            result = subprocess.run(
                [git_cmd, "clone", clone_url, dest_abs],
                capture_output=True,
                text=True,
                timeout=300,
                **_get_subprocess_kwargs(),
            )
            if result.returncode == 0:
                log.info(f"Repository cloned to: {dest_abs}")
                return CmdResult(True, result.stdout.strip(), result.stderr.strip())

            stderr_safe = (result.stderr or "").replace(clone_url, "<repo>")
            log.error(f"Git clone failed (exit {result.returncode})")
            return CmdResult(
                False,
                result.stdout.strip(),
                stderr_safe.strip(),
                error_code="clone_failed",
            )
        except subprocess.TimeoutExpired:
            log.error("Git clone timed out")
            return CmdResult(False, "", "Clone timed out", error_code="timeout")
        except OSError as e:
            log.error(f"Git clone error: {e}")
            return CmdResult(False, "", str(e), error_code="os_error")

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
                [git_cmd, "-C", repo_root, "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=15,
                **_get_subprocess_kwargs(),
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
                [git_cmd, "-C", repo_root, "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=15,
                **_get_subprocess_kwargs(),
            )
            if result.returncode == 0:
                sha = result.stdout.strip()
                return f"(detached {sha})"
        except subprocess.TimeoutExpired:
            pass

        return "(unknown)"

    def list_local_branches(self, repo_root):
        """
        List all local branches in the repository.

        Args:
            repo_root: Repository root path (string)

        Returns:
            list[str]: List of local branch names, or empty list on error
        """
        if not self.is_git_available():
            log.warning("Git not available for list_local_branches")
            return []

        if not repo_root or not os.path.isdir(repo_root):
            log.warning(f"Invalid repo_root for list_local_branches: {repo_root}")
            return []

        git_cmd = self._get_git_command()

        try:
            result = subprocess.run(
                [git_cmd, "-C", repo_root, "branch", "--format=%(refname:short)"],
                capture_output=True,
                text=True,
                timeout=15 ** _get_subprocess_kwargs(),
            )
            if result.returncode == 0:
                branches = [
                    line.strip()
                    for line in result.stdout.strip().split("\n")
                    if line.strip()
                ]
                log.debug(f"Found {len(branches)} local branches")
                return branches
            else:
                log.warning(f"list_local_branches failed: {result.stderr.strip()}")
                return []
        except subprocess.TimeoutExpired:
            log.warning("list_local_branches timed out")
            return []
        except OSError as e:
            log.warning(f"list_local_branches error: {e}")
            return []

    def list_remote_branches(self, repo_root, remote="origin"):
        """
        List all remote branches for the given remote.
        Filters out pseudo-refs like "origin/HEAD".

        Args:
            repo_root: Repository root path (string)
            remote: Remote name (default "origin")

        Returns:
            list[str]: List of remote branch refs (e.g., "origin/main"),
                       or empty list on error
        """
        if not self.is_git_available():
            log.warning("Git not available for list_remote_branches")
            return []

        if not repo_root or not os.path.isdir(repo_root):
            log.warning(f"Invalid repo_root for list_remote_branches: {repo_root}")
            return []

        git_cmd = self._get_git_command()

        try:
            result = subprocess.run(
                [git_cmd, "-C", repo_root, "branch", "-r", "--format=%(refname:short)"],
                capture_output=True,
                text=True,
                timeout=15 ** _get_subprocess_kwargs(),
            )
            if result.returncode == 0:
                branches = [
                    line.strip()
                    for line in result.stdout.strip().split("\n")
                    if line.strip() and not line.strip().endswith("/HEAD")
                ]
                # Filter to only the requested remote
                prefix = f"{remote}/"
                branches = [b for b in branches if b.startswith(prefix)]
                log.debug(f"Found {len(branches)} remote branches for {remote}")
                return branches
            else:
                log.warning(f"list_remote_branches failed: {result.stderr.strip()}")
                return []
        except subprocess.TimeoutExpired:
            log.warning("list_remote_branches timed out")
            return []
        except OSError as e:
            log.warning(f"list_remote_branches error: {e}")
            return []

    def create_branch(self, repo_root, name, start_point=None):
        """
        Create a new branch at the specified start point.

        Args:
            repo_root: Repository root path (string)
            name: Branch name to create
            start_point: Starting commit/branch (default: HEAD)

        Returns:
            CmdResult: Result of the branch creation
        """
        if not self.is_git_available():
            return CmdResult(
                ok=False, stdout="", stderr="Git not available", error_code="NO_GIT"
            )

        if not repo_root or not os.path.isdir(repo_root):
            return CmdResult(
                ok=False,
                stdout="",
                stderr="Invalid repository",
                error_code="INVALID_REPO",
            )

        git_cmd = self._get_git_command()

        if start_point:
            args = [git_cmd, "-C", repo_root, "branch", name, start_point]
        else:
            args = [git_cmd, "-C", repo_root, "branch", name]

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=15,
                **_get_subprocess_kwargs(),
            )
            if result.returncode == 0:
                log.info(f"Created branch: {name}")
                return CmdResult(ok=True, stdout=result.stdout.strip(), stderr="")
            else:
                log.warning(f"create_branch failed: {result.stderr.strip()}")
                return CmdResult(
                    ok=False,
                    stdout=result.stdout.strip(),
                    stderr=result.stderr.strip(),
                    error_code="CREATE_FAILED",
                )
        except subprocess.TimeoutExpired:
            return CmdResult(
                ok=False, stdout="", stderr="Command timed out", error_code="TIMEOUT"
            )
        except OSError as e:
            return CmdResult(ok=False, stdout="", stderr=str(e), error_code="OS_ERROR")

    def checkout_branch(self, repo_root, name):
        """
        Switch to the specified branch.
        Prefers 'git switch', falls back to 'git checkout'.

        Args:
            repo_root: Repository root path (string)
            name: Branch name to switch to

        Returns:
            CmdResult: Result of the checkout operation
        """
        if not self.is_git_available():
            return CmdResult(
                ok=False, stdout="", stderr="Git not available", error_code="NO_GIT"
            )

        if not repo_root or not os.path.isdir(repo_root):
            return CmdResult(
                ok=False,
                stdout="",
                stderr="Invalid repository",
                error_code="INVALID_REPO",
            )

        git_cmd = self._get_git_command()

        # Try 'git switch' first (modern command)
        args = [git_cmd, "-C", repo_root, "switch", name]
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=15,
                **_get_subprocess_kwargs(),
            )
            if result.returncode == 0:
                log.info(f"Switched to branch: {name}")
                return CmdResult(ok=True, stdout=result.stdout.strip(), stderr="")
            else:
                # Check if 'switch' is not recognized
                if (
                    "switch" in result.stderr.lower()
                    and "not a git command" in result.stderr.lower()
                ):
                    # Fallback to checkout
                    log.debug(
                        "'git switch' not available, falling back to 'git checkout'"
                    )
                    args = [git_cmd, "-C", repo_root, "checkout", name]
                    result = subprocess.run(
                        args,
                        capture_output=True,
                        text=True,
                        timeout=15,
                        **_get_subprocess_kwargs(),
                    )
                    if result.returncode == 0:
                        log.info(f"Checked out branch: {name}")
                        return CmdResult(
                            ok=True, stdout=result.stdout.strip(), stderr=""
                        )

                log.warning(f"checkout_branch failed: {result.stderr.strip()}")
                return CmdResult(
                    ok=False,
                    stdout=result.stdout.strip(),
                    stderr=result.stderr.strip(),
                    error_code="CHECKOUT_FAILED",
                )
        except subprocess.TimeoutExpired:
            return CmdResult(
                ok=False, stdout="", stderr="Command timed out", error_code="TIMEOUT"
            )
        except OSError as e:
            return CmdResult(ok=False, stdout="", stderr=str(e), error_code="OS_ERROR")

    def delete_local_branch(self, repo_root, name, force=False):
        """
        Delete a local branch.

        Args:
            repo_root: Repository root path (string)
            name: Branch name to delete
            force: Whether to force delete (use -D instead of -d)

        Returns:
            CmdResult: Result of the delete operation
        """
        if not self.is_git_available():
            return CmdResult(
                ok=False, stdout="", stderr="Git not available", error_code="NO_GIT"
            )

        if not repo_root or not os.path.isdir(repo_root):
            return CmdResult(
                ok=False,
                stdout="",
                stderr="Invalid repository",
                error_code="INVALID_REPO",
            )

        git_cmd = self._get_git_command()
        flag = "-D" if force else "-d"
        args = [git_cmd, "-C", repo_root, "branch", flag, name]

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=15,
                **_get_subprocess_kwargs(),
            )
            if result.returncode == 0:
                log.info(f"Deleted branch: {name}")
                return CmdResult(ok=True, stdout=result.stdout.strip(), stderr="")
            else:
                log.warning(f"delete_local_branch failed: {result.stderr.strip()}")
                return CmdResult(
                    ok=False,
                    stdout=result.stdout.strip(),
                    stderr=result.stderr.strip(),
                    error_code="DELETE_FAILED",
                )
        except subprocess.TimeoutExpired:
            return CmdResult(
                ok=False, stdout="", stderr="Command timed out", error_code="TIMEOUT"
            )
        except OSError as e:
            return CmdResult(ok=False, stdout="", stderr=str(e), error_code="OS_ERROR")

    def get_upstream_ref(self, repo_root):
        """
        Get the upstream tracking ref for the current branch.

        Args:
            repo_root: Repository root path (string)

        Returns:
            str | None: Upstream ref (e.g., "origin/feature-x") or None if no upstream
        """
        if not self.is_git_available():
            return None

        if not repo_root or not os.path.isdir(repo_root):
            return None

        git_cmd = self._get_git_command()

        try:
            result = subprocess.run(
                [
                    git_cmd,
                    "-C",
                    repo_root,
                    "rev-parse",
                    "--abbrev-ref",
                    "--symbolic-full-name",
                    "@{u}",
                ],
                capture_output=True,
                text=True,
                timeout=15,
                **_get_subprocess_kwargs(),
            )
            if result.returncode == 0:
                upstream = result.stdout.strip()
                log.debug(
                    f"Upstream ref for current branch: '{upstream}' (returncode={result.returncode})"
                )
                return upstream if upstream else None
            else:
                log.debug(
                    f"No upstream ref set (returncode={result.returncode}, stderr={result.stderr.strip()})"
                )
                return None
        except subprocess.TimeoutExpired:
            log.warning("get_upstream_ref timed out")
            return None
        except OSError as e:
            log.warning(f"get_upstream_ref error: {e}")
            return None

    def _classify_status_kind(self, x_code, y_code):
        """Classify porcelain XY codes into a status kind."""
        if x_code == "?" and y_code == "?":
            return STATUS_UNTRACKED

        if "U" in (x_code, y_code):
            return STATUS_CONFLICT

        if (x_code == "A" and y_code == "D") or (x_code == "D" and y_code == "A"):
            return STATUS_CONFLICT

        if "R" in (x_code, y_code):
            return STATUS_RENAMED

        if "C" in (x_code, y_code):
            return STATUS_COPIED

        if "D" in (x_code, y_code):
            return STATUS_DELETED

        if "A" in (x_code, y_code):
            return STATUS_ADDED

        if "M" in (x_code, y_code) or "T" in (x_code, y_code):
            return STATUS_MODIFIED

        return STATUS_UNKNOWN

    def status_porcelain(self, repo_root):
        """
        Return detailed working tree status using porcelain -z.

        Args:
            repo_root: Repository root path (string)

        Returns:
            list[FileStatus]: parsed file status entries
        """
        entries: List[FileStatus] = []

        if not self.is_git_available():
            return entries

        if not repo_root or not os.path.isdir(repo_root):
            return entries

        git_cmd = self._get_git_command()

        try:
            proc_result = subprocess.run(
                [git_cmd, "-C", repo_root, "status", "--porcelain=v1", "-z"],
                capture_output=True,
                text=True,
                timeout=20,
                **_get_subprocess_kwargs(),
            )
        except subprocess.TimeoutExpired:
            log.warning("Git status command timed out")
            return entries
        except OSError as e:
            log.warning(f"Failed to run git status: {e}")
            return entries

        if proc_result.returncode != 0:
            stderr = proc_result.stderr.strip()
            log.debug(f"Git status returned {proc_result.returncode}: {stderr}")
            return entries

        raw = proc_result.stdout
        if not raw:
            return entries

        tokens = [t for t in raw.split("\0") if t]
        idx = 0

        while idx < len(tokens):
            token = tokens[idx]
            idx += 1

            if len(token) < 3:
                continue

            x_code = token[0]
            y_code = token[1]
            path_part = token[3:] if len(token) > 3 else ""

            rename_target = None
            if (x_code in ("R", "C") or y_code in ("R", "C")) and (idx < len(tokens)):
                rename_target = tokens[idx]
                idx += 1

            display_path = path_part
            if rename_target:
                display_path = f"{path_part} -> {rename_target}"

            kind = self._classify_status_kind(x_code, y_code)

            entry = FileStatus(
                path=display_path,
                x=x_code,
                y=y_code,
                kind=kind,
                is_staged=x_code not in (" ", "?"),
                is_untracked=(x_code == "?" and y_code == "?"),
            )
            entries.append(entry)

        return entries

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

        statuses = self.status_porcelain(repo_root)

        if not statuses:
            return result

        result["is_clean"] = False

        for entry in statuses:
            if entry.kind == STATUS_MODIFIED:
                result["modified"] += 1
            elif entry.kind == STATUS_ADDED:
                result["added"] += 1
            elif entry.kind == STATUS_DELETED:
                result["deleted"] += 1
            elif entry.kind == STATUS_RENAMED:
                result["renamed"] += 1
            elif entry.kind == STATUS_UNTRACKED:
                result["untracked"] += 1

            line_repr = f"{entry.x}{entry.y} {entry.path}"
            result["raw_lines"].append(line_repr)

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
                timeout=10,
                **_get_subprocess_kwargs(),
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
        # Internal Result-based implementation (Sprint 2) while keeping
        # the public return shape stable for existing callers.
        fetched_at = datetime.now(timezone.utc).isoformat()

        res = self._fetch_result(repo_root, remote=remote, fetched_at=fetched_at)
        if res.ok:
            payload = res.value or {}
            return {
                "ok": True,
                "stdout": payload.get("stdout", ""),
                "stderr": payload.get("stderr", ""),
                "fetched_at": payload.get("fetched_at", fetched_at),
                "error": None,
            }

        err = res.error
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "fetched_at": fetched_at,
            "error": err.message if err else "Fetch failed",
        }

    def _fetch_result(
        self, repo_root: str, remote: str, fetched_at: str
    ) -> Result[dict]:
        if not self.is_git_available():
            return Result.failure("GIT_NOT_AVAILABLE", "Git not available")

        if not repo_root or not os.path.isdir(repo_root):
            return Result.failure("INVALID_REPO_PATH", "Invalid repository path")

        git_cmd = self._get_git_command()
        try:
            proc_result = subprocess.run(
                [git_cmd, "-C", repo_root, "fetch", remote],
                capture_output=True,
                text=True,
                timeout=120,
                **_get_subprocess_kwargs(),
            )
        except subprocess.TimeoutExpired:
            return Result.failure("TIMEOUT", "Fetch timed out after 120 seconds")
        except OSError as e:
            return Result.failure("OS_ERROR", "Failed to run git fetch", details=str(e))

        stdout = (proc_result.stdout or "").strip()
        stderr = (proc_result.stderr or "").strip()

        if proc_result.returncode == 0:
            log.info(f"Fetch completed: {remote}")
            return Result.success(
                {"stdout": stdout, "stderr": stderr, "fetched_at": fetched_at}
            )

        msg = f"Git fetch failed (exit {proc_result.returncode})"
        log.warning(msg)
        return Result.failure("GIT_FETCH_FAILED", msg, details=stderr)

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
                [
                    git_cmd,
                    "-C",
                    repo_root,
                    "symbolic-ref",
                    "-q",
                    f"refs/remotes/{remote}/HEAD",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                **_get_subprocess_kwargs(),
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
                    [
                        git_cmd,
                        "-C",
                        repo_root,
                        "show-ref",
                        "--verify",
                        "--quiet",
                        f"refs/remotes/{remote}/{branch}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    **_get_subprocess_kwargs(),
                )
                if result.returncode == 0:
                    upstream = f"{remote}/{branch}"
                    log.debug(f"Found upstream branch: {upstream}")
                    return upstream
            except (subprocess.TimeoutExpired, OSError):
                pass

        log.debug("No default upstream reference found")
        return None

    def get_ahead_behind_with_upstream(self, repo_root):
        """
        Compute ahead/behind using the tracking upstream if available,
        otherwise fall back to default upstream (origin/main or origin/master).

        Args:
            repo_root: Repository root path (string)

        Returns:
            dict with keys:
                - ahead: int (commits ahead, or 0)
                - behind: int (commits behind, or 0)
                - ok: bool
                - error: str | None
                - upstream: str | None (the upstream ref used, or None if no tracking)
        """
        # Try to get the tracking upstream first
        upstream_ref = self.get_upstream_ref(repo_root)

        if upstream_ref:
            # Use the tracking upstream
            log.debug(f"Using tracking upstream: {upstream_ref}")
            result = self.ahead_behind(repo_root, upstream_ref)
            result["upstream"] = upstream_ref
            return result
        else:
            # No tracking upstream - return empty result
            # The UI will show "(not set)" for upstream
            log.debug("No tracking upstream found")
            return {
                "ahead": 0,
                "behind": 0,
                "ok": False,
                "error": "No upstream configured",
                "upstream": None,
            }

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
                [
                    git_cmd,
                    "-C",
                    repo_root,
                    "rev-list",
                    "--left-right",
                    "--count",
                    f"HEAD...{upstream}",
                ],
                capture_output=True,
                text=True,
                timeout=15,
                **_get_subprocess_kwargs(),
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
                        result["error"] = f"Failed to parse rev-list output: {output}"
                else:
                    result["error"] = f"Unexpected rev-list output: {output}"
            else:
                result["error"] = f"Git rev-list failed: {proc_result.stderr.strip()}"

        except subprocess.TimeoutExpired:
            result["error"] = "Git rev-list timed out"
        except OSError as e:
            result["error"] = f"Failed to run git rev-list: {e}"

        if result["error"]:
            log.debug(result["error"])

        return result

    def _run_command(self, args, timeout=60):
        """Run a git command and wrap result."""
        cmd_result = CmdResult(
            ok=False,
            stdout="",
            stderr="",
            error_code=None,
        )

        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                **_get_subprocess_kwargs(),
            )
            cmd_result.stdout = proc.stdout.strip()
            cmd_result.stderr = proc.stderr.strip()
            cmd_result.ok = proc.returncode == 0
        except subprocess.TimeoutExpired:
            cmd_result.stderr = "Command timed out"
            cmd_result.error_code = "TIMEOUT"
        except OSError as e:
            cmd_result.stderr = str(e)
            cmd_result.error_code = "OS_ERROR"

        return cmd_result

    def _classify_commit_error(self, stderr_text):
        """Map commit stderr output to a friendly code."""
        lower = stderr_text.lower()

        if "nothing to commit" in lower:
            return "NOTHING_TO_COMMIT"
        if "no changes added to commit" in lower:
            return "NOTHING_TO_COMMIT"
        if "user.name" in lower or "user.email" in lower:
            return "MISSING_IDENTITY"
        if "please tell me who you are" in lower:
            return "MISSING_IDENTITY"

        return "UNKNOWN_ERROR"

    def _classify_push_error(self, stderr_text):
        """Map push stderr output to a friendly code."""
        lower = stderr_text.lower()

        if "authentication failed" in lower:
            return "AUTH_OR_PERMISSION"
        if "permission denied" in lower:
            return "AUTH_OR_PERMISSION"
        if "could not read from remote repository" in lower:
            return "AUTH_OR_PERMISSION"

        if "no configured push destination" in lower:
            return "NO_UPSTREAM"
        if "no upstream" in lower:
            return "NO_UPSTREAM"
        if "set the remote as upstream" in lower:
            return "NO_UPSTREAM"

        if "does not appear to be a git repository" in lower:
            return "NO_REMOTE"
        if "no such remote" in lower:
            return "NO_REMOTE"

        if "rejected" in lower or "failed to push" in lower:
            return "REJECTED"

        return "UNKNOWN_ERROR"

    def stage_all(self, repo_root):
        """Stage all changes (git add -A)."""
        if not self.is_git_available():
            return CmdResult(False, "", "Git not available", "NO_GIT")

        if not repo_root or not os.path.isdir(repo_root):
            return CmdResult(False, "", "Invalid repository", "INVALID_REPO")

        git_cmd = self._get_git_command()
        return self._run_command(
            [git_cmd, "-C", repo_root, "add", "-A"],
            timeout=60,
        )

    def stage_paths(self, repo_root, paths):
        """Stage only specified paths."""
        if not paths:
            return CmdResult(True, "", "", None)

        if not self.is_git_available():
            return CmdResult(False, "", "Git not available", "NO_GIT")

        if not repo_root or not os.path.isdir(repo_root):
            return CmdResult(False, "", "Invalid repository", "INVALID_REPO")

        git_cmd = self._get_git_command()
        args = [git_cmd, "-C", repo_root, "add", "--"]
        args.extend(paths)
        return self._run_command(args, timeout=60)

    def commit(self, repo_root, message):
        """Create a commit with the provided message."""
        if not message:
            return CmdResult(False, "", "Empty commit message", "EMPTY_MESSAGE")

        # SECURITY: Sanitize commit message to prevent injection attacks
        from freecad_gitpdm.core import input_validator
        sanitized_message = input_validator.sanitize_commit_message(message)
        
        if not sanitized_message:
            return CmdResult(False, "", "Commit message is empty after sanitization", "EMPTY_MESSAGE")
        
        if sanitized_message != message:
            log.debug("Commit message was sanitized (removed unsafe characters)")

        if not self.is_git_available():
            return CmdResult(False, "", "Git not available", "NO_GIT")

        if not repo_root or not os.path.isdir(repo_root):
            return CmdResult(False, "", "Invalid repository", "INVALID_REPO")

        git_cmd = self._get_git_command()
        # Use sanitized message
        cmd_result = self._run_command(
            [git_cmd, "-C", repo_root, "commit", "-m", sanitized_message],
            timeout=120,
        )

        if cmd_result.ok:
            truncated = sanitized_message[:60].replace("\n", " ")
            log.debug(f"Commit created: {truncated}")
        else:
            cmd_result.error_code = self._classify_commit_error(cmd_result.stderr)

        return cmd_result

    def has_upstream(self, repo_root):
        """Return True if current branch has an upstream set."""
        return self.get_upstream_ref(repo_root) is not None

    def push(self, repo_root, remote="origin"):
        """Push current branch, setting upstream if needed."""
        if not self.is_git_available():
            return CmdResult(False, "", "Git not available", "NO_GIT")

        if not repo_root or not os.path.isdir(repo_root):
            return CmdResult(False, "", "Invalid repository", "INVALID_REPO")

        git_cmd = self._get_git_command()

        if self.has_upstream(repo_root):
            args = [git_cmd, "-C", repo_root, "push"]
        else:
            args = [git_cmd, "-C", repo_root, "push", "-u", remote, "HEAD"]

        result = self._run_command(args, timeout=180)

        if not result.ok:
            result.error_code = self._classify_push_error(result.stderr)

        return result

    def has_uncommitted_changes(self, repo_root):
        """Return True if porcelain status reports any entries."""
        statuses = self.status_porcelain(repo_root)
        return len(statuses) > 0

    def pull_ff_only(self, repo_root, remote="origin", upstream=None):
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
                command = [
                    git_cmd,
                    "-C",
                    repo_root,
                    "pull",
                    "--ff-only",
                    remote,
                    branch,
                ]
            else:
                # Use: git pull --ff-only (default upstream)
                command = [git_cmd, "-C", repo_root, "pull", "--ff-only"]

            proc_result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes for pull
                ** _get_subprocess_kwargs(),
            )

            result["stdout"] = proc_result.stdout.strip()
            result["stderr"] = proc_result.stderr.strip()
            result["ok"] = proc_result.returncode == 0

            if result["ok"]:
                log.info("Pull fast-forward completed successfully")
            else:
                # Classify the error
                result["error_code"] = self._classify_pull_error(result["stderr"])
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
        if "does not appear to be a git repository" in stderr_lower:
            return "NO_REMOTE"

        # Unknown error
        return "UNKNOWN_ERROR"

    # --- Sprint 5: Repo file listing ---

    def list_tracked_files(self, repo_root):
        """
        List files currently tracked by git in working tree.

        Args:
            repo_root: Repository root path (string)

        Returns:
            list[str]: repo-relative paths (NUL-safe parsing)
        """
        files: List[str] = []

        if not self.is_git_available():
            log.warning("Git not available for ls-files")
            return files

        if not repo_root or not os.path.isdir(repo_root):
            log.warning("Invalid repository path for ls-files")
            return files

        git_cmd = self._get_git_command()

        try:
            proc = subprocess.run(
                [git_cmd, "-C", repo_root, "ls-files", "-z"],
                capture_output=True,
                text=True,
                timeout=20,
                **_get_subprocess_kwargs(),
            )
        except subprocess.TimeoutExpired:
            log.warning("git ls-files timed out")
            return files
        except OSError as e:
            log.warning(f"Failed to run git ls-files: {e}")
            return files

        if proc.returncode != 0:
            err = proc.stderr.strip()
            log.warning(f"git ls-files failed: {err}")
            return files

        # NUL-separated output; entries may be empty at ends
        raw = proc.stdout
        if not raw:
            return files

        for token in raw.split("\0"):
            if token:
                # git returns repo-relative paths
                files.append(token)

        return files

    def list_cad_files(self, repo_root, extensions):
        """
        Filter tracked files by CAD extensions.

        Args:
            repo_root: repo root path
            extensions: list[str] of extensions (case-insensitive)

        Returns:
            list[str]: repo-relative CAD file paths
        """
        tracked = self.list_tracked_files(repo_root)
        if not tracked:
            return []

        # Normalize extension list for matching
        norm_exts = []
        for e in extensions or []:
            if not e:
                continue
            s = e.strip().lower()
            if not s:
                continue
            if not s.startswith("."):
                s = "." + s
            if s not in norm_exts:
                norm_exts.append(s)

        if not norm_exts:
            return []

        cad_files: List[str] = []
        for p in tracked:
            # Extract extension safely; consider multi-dot names
            name = p.rsplit("/", 1)[-1]
            # Also handle Windows separators if any
            name = name.rsplit("\\", 1)[-1]
            # If no dot, skip
            if "." not in name:
                continue
            ext = "." + name.split(".")[-1].lower()
            if ext in norm_exts:
                cad_files.append(p)

        return cad_files

    def set_default_branch(self, repo_root, branch="main"):
        """
        Rename/set the default branch to the specified name.
        Uses 'git branch -M <branch>' to rename HEAD branch.

        Args:
            repo_root: Repository root path (string)
            branch: Target branch name (default "main")

        Returns:
            CmdResult indicating success/failure
        """
        if not self.is_git_available():
            return CmdResult(False, "", "Git not available", "NO_GIT")

        if not repo_root or not os.path.isdir(repo_root):
            return CmdResult(False, "", "Invalid repository", "INVALID_REPO")

        branch = (branch or "main").strip()
        if not branch:
            branch = "main"

        git_cmd = self._get_git_command()
        return self._run_command(
            [git_cmd, "-C", repo_root, "branch", "-M", branch],
            timeout=30,
        )

    def lfs_install(self):
        """
        Run 'git lfs install' to set up Git LFS hooks in git config.
        This is a one-time setup per user environment.

        Returns:
            CmdResult indicating success/failure
        """
        if not self.is_git_available():
            return CmdResult(False, "", "Git not available", "NO_GIT")

        git_cmd = self._get_git_command()
        return self._run_command(
            [git_cmd, "lfs", "install", "--skip-smudge"],
            timeout=30,
        )

    def get_config(self, repo_root, key, local=False):
        """
        Get a git config value.

        Args:
            repo_root: Repository root path (string), or None for global
            key: Config key (e.g., "user.name")
            local: If True, use --local; else use --global (if repo_root is None)

        Returns:
            str: Config value, or empty string if not found
        """
        if not self.is_git_available():
            return ""

        git_cmd = self._get_git_command()

        args = [git_cmd, "config"]
        if local and repo_root:
            args.append("--local")
        elif repo_root:
            args.append("--global")
        args.append(key)

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=repo_root if repo_root and os.path.isdir(repo_root) else None,
                **_get_subprocess_kwargs(),
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            pass

        return ""

    def set_config(self, repo_root, key, value, local=False):
        """
        Set a git config value.

        Args:
            repo_root: Repository root path (string), or None for global
            key: Config key (e.g., "user.name")
            value: Config value
            local: If True, use --local; else use --global (if repo_root is None)

        Returns:
            CmdResult indicating success/failure
        """
        if not self.is_git_available():
            return CmdResult(False, "", "Git not available", "NO_GIT")

        if not key or not value:
            return CmdResult(False, "", "Missing key or value", "INVALID_ARGS")

        git_cmd = self._get_git_command()

        args = [git_cmd, "config"]
        if local and repo_root:
            args.append("--local")
        elif repo_root:
            args.append("--global")
        args.extend([key, value])

        return self._run_command(args, timeout=30)
