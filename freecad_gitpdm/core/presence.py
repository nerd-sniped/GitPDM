# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
GitPDM Advisory File Presence (Plan A, 2026-07-20)

Warns, never blocks: "this file may already be open elsewhere," nothing more.
Deliberately not real file locking -- see Dev_Docs/PRESENCE_AND_LFS_REMOVAL_PLAN.md
for the reasoning. `.FCStd` conflicts are always manually reconcilable (git
history is never lost), so the actual value here is avoiding *wasted* editing
effort by telling a second person someone's already in a file, not preventing
data loss.

Cross-user, so (unlike core/session_lock.py, which is local-filesystem/PID
-scoped for two GitPDM instances on one shared working tree) this has to
travel through the one channel every user shares: the git remote itself, via
a dedicated `gitpdm/presence` branch (see GitClient's PRESENCE_REF) holding a
single small JSON file. Built on GitClient's presence plumbing (hash-object/
mktree/commit-tree/update-ref/fetch_ref) the same way core/checkpoint.py is
built on the recovery-branch plumbing.

Deliberately FreeCAD-agnostic (CLAUDE.md: "Tests must run without FreeCAD") --
`ui/panel.py` calls these functions from FreeCAD document-open/close hooks and
a heartbeat timer, but nothing here imports FreeCAD.

Every write is best-effort: a failure here (offline, race with another user,
git not available) must never block opening or closing a document -- it just
means presence data is stale or absent, which degrades to "no warning shown,"
never a wrong block.
"""

from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from freecad_gitpdm.core import log
from freecad_gitpdm.git.client import PRESENCE_REF

PRESENCE_FILENAME = "open-files.json"

# An entry with no heartbeat in this long is treated as abandoned (crashed,
# force-quit, or just never announced a close) -- pruned on the next write
# rather than kept forever, and never surfaced as a "someone has this open"
# warning. Same order of magnitude as session_lock.STALE_LOCK_SECONDS.
STALE_PRESENCE_SECONDS = 15 * 60

# Bounded retry for the read-modify-write race: another user's presence
# commit can land between our fetch and our push. One retry (re-fetch,
# re-merge, re-push) resolves the overwhelmingly common case; this is
# advisory data, not a guarantee, so we don't retry indefinitely.
_MAX_WRITE_ATTEMPTS = 2


@dataclass
class PresenceEntry:
    """One other user's claim on a file, as of their last heartbeat."""

    user: str
    host: str
    opened_at: str
    last_heartbeat: str


def relative_path(repo_root: str, abs_path: str) -> str:
    """Repo-relative, forward-slash path -- the presence map's keys must be
    portable across machines/OSes, unlike a raw OS-native absolute path."""
    rel = os.path.relpath(abs_path, repo_root)
    return rel.replace(os.sep, "/")


def describe_last_seen(entry: PresenceEntry, now: Optional[datetime] = None) -> str:
    """One-line "Xm ago" style string for UI display."""
    now = now or datetime.now(timezone.utc)
    seen = _parse_timestamp(entry.last_heartbeat)
    if seen is None:
        return "recently"
    delta_s = max(0, int((now - seen).total_seconds()))
    if delta_s < 60:
        return "moments ago"
    minutes = delta_s // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    return f"{hours}h ago"


def announce_open(
    git_client, repo_root: str, file_rel_path: str
) -> Optional[PresenceEntry]:
    """
    Call when a document is opened. Best-effort: fetches the latest presence
    state, records our own open, and returns another user's live entry for
    this same file if one exists (so the caller can show a non-blocking
    warning) -- or None if the file looks free, or on any failure (offline,
    git unavailable, brand-new repo with no presence branch yet).
    """
    try:
        return _announce_open_impl(git_client, repo_root, file_rel_path)
    except Exception as e:
        log.debug(f"Presence announce_open failed (non-fatal): {e}")
        return None


def heartbeat(git_client, repo_root: str, file_rel_path: str) -> None:
    """Call periodically while a document stays open, so our entry doesn't
    look abandoned to other users. Best-effort; never raises."""
    try:
        _heartbeat_impl(git_client, repo_root, file_rel_path)
    except Exception as e:
        log.debug(f"Presence heartbeat failed (non-fatal): {e}")


def announce_close(git_client, repo_root: str, file_rel_path: str) -> None:
    """Call when a document is closed, so other users stop seeing it as
    open. Best-effort; never raises. Never removes another user's entry."""
    try:
        _announce_close_impl(git_client, repo_root, file_rel_path)
    except Exception as e:
        log.debug(f"Presence announce_close failed (non-fatal): {e}")


# --- internals ------------------------------------------------------------


def _own_identity(git_client, repo_root: str) -> tuple[str, str]:
    """Effective (local-overrides-global) user.name/user.email for
    repo_root. GitClient.get_config()'s `local` flag is an explicit
    either/or (not "prefer local"), so the fallback is done here: try the
    repo-local value first, then the global one, matching what a plain
    `git commit` in this repo would actually use."""
    name = git_client.get_config(
        repo_root, "user.name", local=True
    ) or git_client.get_config(repo_root, "user.name")
    email = git_client.get_config(
        repo_root, "user.email", local=True
    ) or git_client.get_config(repo_root, "user.email")
    user = name or email or "unknown"
    return user, socket.gethostname()


def _parse_timestamp(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _entry_is_stale(entry: dict, now: datetime) -> bool:
    seen = _parse_timestamp(entry.get("last_heartbeat", ""))
    if seen is None:
        return True
    return (now - seen).total_seconds() > STALE_PRESENCE_SECONDS


def _load_presence_map(git_client, repo_root: str) -> dict:
    """Read+parse the JSON map at PRESENCE_REF's tip. Empty dict if the
    branch, file, or JSON is missing/malformed -- never raises."""
    content = git_client.read_file_at_ref(repo_root, PRESENCE_REF, PRESENCE_FILENAME)
    if not content:
        return {}
    try:
        data = json.loads(content)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _write_presence_map(git_client, repo_root: str, data: dict, message: str) -> bool:
    """One commit replacing the whole JSON file, CAS'd against whatever
    PRESENCE_REF pointed at when we started building this commit."""
    parent = git_client.rev_parse(repo_root, PRESENCE_REF)
    content = json.dumps(data, indent=2, sort_keys=True) + "\n"

    blob_sha = git_client.hash_object(repo_root, content)
    if not blob_sha:
        return False
    tree_sha = git_client.make_tree_with_file(repo_root, PRESENCE_FILENAME, blob_sha)
    if not tree_sha:
        return False
    commit_result = git_client.commit_tree_with_parent(
        repo_root, tree_sha, parent, message
    )
    if not commit_result.ok or not commit_result.stdout.strip():
        return False
    new_sha = commit_result.stdout.strip()

    update_result = git_client.update_ref_cas(
        repo_root, PRESENCE_REF, new_sha, expected_old_sha=parent
    )
    return update_result.ok


def _push_presence(git_client, repo_root: str) -> None:
    result = git_client.push_ref(repo_root, PRESENCE_REF)
    if not result.ok:
        log.debug(f"Presence branch push failed (non-fatal): {result.stderr}")


def _announce_open_impl(
    git_client, repo_root: str, file_rel_path: str
) -> Optional[PresenceEntry]:
    git_client.fetch_ref(repo_root, PRESENCE_REF)

    user, host = _own_identity(git_client, repo_root)
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    other: Optional[PresenceEntry] = None

    for attempt in range(_MAX_WRITE_ATTEMPTS):
        data = {
            path: entry
            for path, entry in _load_presence_map(git_client, repo_root).items()
            if isinstance(entry, dict) and not _entry_is_stale(entry, now)
        }

        existing = data.get(file_rel_path)
        is_ours = bool(
            existing and existing.get("user") == user and existing.get("host") == host
        )
        if existing and not is_ours:
            other = PresenceEntry(
                user=str(existing.get("user", "someone")),
                host=str(existing.get("host", "")),
                opened_at=str(existing.get("opened_at", "")),
                last_heartbeat=str(existing.get("last_heartbeat", "")),
            )

        data[file_rel_path] = {
            "user": user,
            "host": host,
            "opened_at": existing.get("opened_at") if is_ours else now_iso,
            "last_heartbeat": now_iso,
        }

        if _write_presence_map(
            git_client, repo_root, data, f"GitPDM presence: open {file_rel_path}"
        ):
            _push_presence(git_client, repo_root)
            return other

        if attempt + 1 < _MAX_WRITE_ATTEMPTS:
            git_client.fetch_ref(repo_root, PRESENCE_REF)

    return other


def _heartbeat_impl(git_client, repo_root: str, file_rel_path: str) -> None:
    user, host = _own_identity(git_client, repo_root)
    now_iso = datetime.now(timezone.utc).isoformat()

    for attempt in range(_MAX_WRITE_ATTEMPTS):
        data = dict(_load_presence_map(git_client, repo_root))
        existing = data.get(file_rel_path)
        opened_at = existing.get("opened_at") if existing else now_iso

        data[file_rel_path] = {
            "user": user,
            "host": host,
            "opened_at": opened_at,
            "last_heartbeat": now_iso,
        }

        if _write_presence_map(
            git_client, repo_root, data, f"GitPDM presence: heartbeat {file_rel_path}"
        ):
            _push_presence(git_client, repo_root)
            return

        if attempt + 1 < _MAX_WRITE_ATTEMPTS:
            git_client.fetch_ref(repo_root, PRESENCE_REF)


def _announce_close_impl(git_client, repo_root: str, file_rel_path: str) -> None:
    user, host = _own_identity(git_client, repo_root)

    for attempt in range(_MAX_WRITE_ATTEMPTS):
        data = dict(_load_presence_map(git_client, repo_root))
        existing = data.get(file_rel_path)
        if not existing:
            return  # nothing to remove
        if existing.get("user") != user or existing.get("host") != host:
            return  # someone else's entry (e.g. we lost a prior race) -- not ours to remove

        del data[file_rel_path]

        if _write_presence_map(
            git_client, repo_root, data, f"GitPDM presence: close {file_rel_path}"
        ):
            _push_presence(git_client, repo_root)
            return

        if attempt + 1 < _MAX_WRITE_ATTEMPTS:
            git_client.fetch_ref(repo_root, PRESENCE_REF)


__all__ = [
    "PresenceEntry",
    "relative_path",
    "describe_last_seen",
    "announce_open",
    "heartbeat",
    "announce_close",
    "STALE_PRESENCE_SECONDS",
    "PRESENCE_FILENAME",
]
