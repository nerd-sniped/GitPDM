# -*- coding: utf-8 -*-
"""
GitPDM Concurrent Session Guard
Phase G5 (R2.3): advisory lockfile so two GitPDM instances (e.g. two browser
tabs against one hosted-deployment repo) don't both write to the same
working tree while an .FCStd document may be open in one of them.

This is advisory, not enforced by the filesystem: it exists to warn, not to
block. A determined second instance can always override.
"""

from __future__ import annotations

import ctypes
import json
import os
import socket
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from freecad_gitpdm.core import log

LOCK_FILENAME = "gitpdm.lock"

# A lock older than this, held by a still-live PID, is treated as stale
# (crashed/suspended process that never released it) rather than a genuine
# second active session.
STALE_LOCK_SECONDS = 15 * 60


@dataclass
class LockInfo:
    pid: int
    timestamp: str
    hostname: str


@dataclass
class LockResult:
    ok: bool
    existing: Optional[LockInfo] = None


def _lock_path(repo_root: str) -> str:
    return os.path.join(repo_root, ".git", LOCK_FILENAME)


def _pid_alive(pid: int) -> bool:
    """Best-effort liveness check, stdlib only (no psutil dependency)."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        # PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but is owned by someone else - still alive.
        return True
    except OSError:
        return False
    return True


def _read_lock(repo_root: str) -> Optional[LockInfo]:
    path = _lock_path(repo_root)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return LockInfo(
            pid=int(data["pid"]),
            timestamp=str(data["timestamp"]),
            hostname=str(data.get("hostname", "")),
        )
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError) as e:
        log.warning(f"Could not read session lock at {path}, treating as free: {e}")
        return None


def _write_lock(repo_root: str) -> None:
    path = _lock_path(repo_root)
    payload = {
        "pid": os.getpid(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except OSError as e:
        # Advisory only - if we can't write the lock, proceed without one
        # rather than blocking repo activation.
        log.warning(f"Could not write session lock at {path}: {e}")


def _is_stale(info: LockInfo) -> bool:
    if not _pid_alive(info.pid):
        return True
    try:
        held_since = datetime.fromisoformat(info.timestamp)
        if held_since.tzinfo is None:
            held_since = held_since.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - held_since).total_seconds()
    except ValueError:
        # Unparseable timestamp - can't judge age, don't treat as stale
        # purely on that basis; liveness already checked above.
        return False
    return age > STALE_LOCK_SECONDS


def acquire_lock(repo_root: str, force: bool = False) -> LockResult:
    """
    Try to acquire the advisory session lock for repo_root.

    Returns LockResult(ok=True) on success (fresh lock written, or the lock
    was already ours/stale/dead and got reclaimed). Returns
    LockResult(ok=False, existing=...) when a live foreign session holds it
    and force is False - the caller should warn the user and retry with
    force=True if they choose to proceed anyway.
    """
    if not repo_root or not os.path.isdir(os.path.join(repo_root, ".git")):
        return LockResult(ok=True)

    existing = _read_lock(repo_root)
    if existing is not None and existing.pid == os.getpid():
        _write_lock(repo_root)
        return LockResult(ok=True)

    if existing is not None and not force and not _is_stale(existing):
        return LockResult(ok=False, existing=existing)

    if existing is not None and _is_stale(existing):
        log.info(
            f"Clearing stale GitPDM session lock (pid={existing.pid}, "
            f"host={existing.hostname}, ts={existing.timestamp})"
        )

    _write_lock(repo_root)
    return LockResult(ok=True)


def refresh_lock(repo_root: str) -> None:
    """Rewrite the timestamp on a lock we already hold, so a long-running
    session doesn't look abandoned/stale to a second instance."""
    if not repo_root:
        return
    existing = _read_lock(repo_root)
    if existing is not None and existing.pid != os.getpid():
        # Someone else's lock - don't touch it.
        return
    _write_lock(repo_root)


def release_lock(repo_root: str) -> None:
    """Remove our own lock, if present. Never removes a lock we don't own."""
    if not repo_root:
        return
    path = _lock_path(repo_root)
    existing = _read_lock(repo_root)
    if existing is None or existing.pid != os.getpid():
        return
    try:
        os.remove(path)
    except OSError as e:
        log.debug(f"Could not remove session lock at {path}: {e}")
