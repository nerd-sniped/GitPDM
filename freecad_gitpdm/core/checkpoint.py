# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
GitPDM Continuous Checkpointing (Phase G6 / R2.5)

Delivers an Onshape-style "walk away anytime, lose <= ~1 minute" guarantee
via debounced checkpoints onto a `gitpdm/recovery` branch -- not per-action
persistence, which is prohibitive on FreeCAD's blocking whole-file save (see
R2.5's rationale in Dev_Docs/GITPDM_DEV_PLAN.md).

This module is deliberately FreeCAD-agnostic (CLAUDE.md: "Tests must run
without FreeCAD"). The two things only FreeCAD can answer -- "is the user
mid-edit right now" and "perform the actual document save" -- are taken as
injected callables (`is_busy`/`save_if_dirty`) rather than imported here;
`ui/panel.py` supplies the real FreeCAD-backed versions. Git plumbing itself
lives on GitClient (`git/client.py`), per the existing convention that all
git operations go through there.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from freecad_gitpdm.core import log, settings
from freecad_gitpdm.git.client import RECOVERY_REF, CmdResult, RecoveryCheckpointEntry

# Folder (inside .git/, never walked by `git add`/checked in by any commit,
# so it can never recursively capture itself into a later checkpoint)
# non-destructive recovery exports land in -- see export_recovery_snapshot.
RECOVERY_EXPORT_DIRNAME = "gitpdm-recovery"

# Each export folder is a full checked-out copy of the tracked files, not a
# diff -- unbounded growth across a long editing session could add up fast
# for a large CAD file, so only the most recent this many are kept (oldest
# pruned first). All of them are cleared outright once a real commit
# supersedes the whole recovery history anyway -- see prune_recovery_branch.
MAX_RETAINED_RECOVERY_EXPORTS = 30

# Marker file (also inside .git/) recording which document the most recent
# checkpoint actually saved -- see note_last_checkpoint_file/
# load_last_checkpoint_file below for why this can't live in FreeCAD's own
# parameter store.
_LAST_CHECKPOINT_FILENAME = "gitpdm-last-checkpoint.json"

# Idle-debounce: a checkpoint fires once the document has been dirty and
# untouched for this long (within R2.5's 30-60s band).
DEFAULT_IDLE_SECONDS = 45

# Max-interval backstop: a checkpoint fires even without idle time, so
# continuous active editing still gets checkpointed periodically (within
# R2.5's 2-5min band).
DEFAULT_MAX_INTERVAL_SECONDS = 180


@dataclass
class CheckpointState:
    """Mutable scheduling state the caller (ui/panel.py) owns and updates:
    `last_activity_at` on every document edit, `last_checkpoint_at` after
    every successful checkpoint. `dirty` tracks whether any edit has
    happened since the last checkpoint (or session start)."""

    last_activity_at: Optional[float] = None
    last_checkpoint_at: Optional[float] = None
    dirty: bool = False

    def note_activity(self, now: float) -> None:
        self.last_activity_at = now
        self.dirty = True

    def note_checkpoint(self, now: float) -> None:
        self.last_checkpoint_at = now
        self.dirty = False


@dataclass
class CheckpointResult:
    ok: bool
    sha: str = ""
    pushed: bool = False
    skipped_reason: str = ""
    message: str = ""
    # False only when save_if_dirty() was invoked and actually raised, i.e.
    # a checkpoint commit still landed on gitpdm/recovery but it's a no-op
    # re-snapshot of whatever was already on disk, NOT a capture of the
    # edit the user was making -- distinct from "nothing needed saving".
    # Surfaced so a caller (ui/panel.py) can tell "this checkpoint really
    # has your latest edit" apart from false confidence that it does just
    # because a new commit exists (see the seamless-recovery follow-up).
    save_ok: bool = True


@dataclass
class RecoveryStatus:
    available: bool
    recovery_sha: str = ""
    head_sha: str = ""


def max_interval_seconds_for_repo(repo_root) -> int:
    """The max-interval backstop for a repo. A single constant now that
    storage mode is gone (see Dev_Docs/PRESENCE_AND_LFS_REMOVAL_PLAN.md) --
    kept as a function rather than inlining the constant at call sites, in
    case a future per-repo override reappears."""
    return DEFAULT_MAX_INTERVAL_SECONDS


def should_checkpoint(
    state: CheckpointState,
    now: float,
    idle_seconds: int = DEFAULT_IDLE_SECONDS,
    max_interval_seconds: int = DEFAULT_MAX_INTERVAL_SECONDS,
) -> bool:
    """
    Pure scheduling decision: fire a checkpoint when there's unsaved-relative
    activity (dirty) AND either the idle window has elapsed since the last
    edit, or the max-interval backstop has elapsed since the last checkpoint
    (whichever baseline is more recent), so continuous active editing still
    gets checkpointed periodically instead of never going idle.
    """
    if not state.dirty:
        return False

    if (
        state.last_activity_at is not None
        and (now - state.last_activity_at) >= idle_seconds
    ):
        return True

    baseline = state.last_checkpoint_at
    if baseline is None:
        baseline = state.last_activity_at
    if baseline is not None and (now - baseline) >= max_interval_seconds:
        return True

    return False


def should_auto_push_recovery() -> bool:
    """
    Push policy (R2.5, revised 2026-07-19 per explicit user decision): ON by
    default everywhere, desktop and headless alike, so a checkpoint is a
    real off-machine record as soon as it's made rather than sitting local
    -only until the next real commit -- work shouldn't stay tied to one
    machine for long. (Originally OFF-on-desktop-by-default, to avoid
    surprise background pushes for an interactive user; that concern is
    still addressable via an explicit override below, just no longer the
    default.) An explicit user override in settings always wins -- e.g.
    "Never" for a bandwidth- or privacy-constrained desktop session.
    """
    override = settings.load_checkpoint_auto_push_override()
    if override is not None:
        return override

    return True


def _checkpoint_message() -> str:
    return f"GitPDM checkpoint {datetime.now(timezone.utc).isoformat()}"


def run_checkpoint(
    git_client,
    repo_root: str,
    is_busy: Callable[[], bool],
    save_if_dirty: Callable[[], bool],
    respect_busy_guard: bool = True,
) -> CheckpointResult:
    """
    One checkpoint attempt.

    `is_busy` must report whether FreeCAD has an active command/transaction
    (e.g. mid-sketch-edit) -- a checkpoint must never save mid-edit, so a
    busy document defers rather than saving (the caller's scheduler will
    retry on its next tick). `save_if_dirty` performs FreeCAD's actual
    blocking whole-document save when there are in-memory unsaved changes;
    only after that has the working tree changed on disk for the recovery
    commit to capture. It must return True when there was nothing to save
    or the save succeeded, and False only if a save was attempted and
    failed -- the commit below still runs either way (a stale checkpoint is
    still better than none), but the caller needs to know which case it got
    (see `CheckpointResult.save_ok`): a commit can succeed as pure git
    plumbing while re-snapshotting stale, pre-edit disk content if the
    actual document save silently failed, which would otherwise look
    identical to a real, edit-capturing checkpoint from the outside (both
    just look like "a new commit landed on gitpdm/recovery").

    `respect_busy_guard=False` is for the shutdown path (see
    run_shutdown_checkpoint): the process is exiting regardless, so there is
    no "later" to defer to -- capture whatever can be captured now.
    """
    if respect_busy_guard and is_busy():
        return CheckpointResult(ok=False, skipped_reason="busy")

    save_ok = save_if_dirty()

    commit_result = git_client.commit_recovery_checkpoint(
        repo_root, _checkpoint_message()
    )
    if not commit_result.ok:
        return CheckpointResult(
            ok=False, message=commit_result.stderr or commit_result.error_code or ""
        )

    pushed = False
    if should_auto_push_recovery():
        push_result = git_client.push_ref(repo_root, RECOVERY_REF)
        pushed = push_result.ok
        if not pushed:
            log.warning(f"Recovery-branch push failed: {push_result.stderr}")

    return CheckpointResult(
        ok=True, sha=commit_result.stdout, pushed=pushed, save_ok=bool(save_ok)
    )


def run_shutdown_checkpoint(
    git_client, repo_root: str, save_if_dirty: Callable[[], None]
) -> CheckpointResult:
    """
    Synchronous save+checkpoint+push for an external SIGTERM handler to
    invoke before the process exits (R2.5). Not installed automatically --
    see register_sigterm_handler() below -- since GitPDM runs embedded in
    FreeCAD's GUI process; a headless deployment's own process supervisor
    wires this in, the same pattern as auth/check.py being built for
    external headless invocation rather than calling itself.
    """
    return run_checkpoint(
        git_client,
        repo_root,
        is_busy=lambda: False,
        save_if_dirty=save_if_dirty,
        respect_busy_guard=False,
    )


def register_sigterm_handler(handler: Callable[[], None]) -> bool:
    """
    Best-effort: install `handler` (no-arg callable, typically wrapping
    run_shutdown_checkpoint) as the process's SIGTERM handler. Only usable
    from the main thread, and only where the platform supports SIGTERM.
    Returns True if installed. Failures are logged and swallowed -- this is
    a convenience for headless deployments, not a guarantee.
    """
    try:
        signal.signal(signal.SIGTERM, lambda signum, frame: handler())
        return True
    except (ValueError, AttributeError, OSError) as e:
        log.debug(f"Could not install SIGTERM checkpoint handler: {e}")
        return False


def recovery_branch_status(git_client, repo_root: str) -> RecoveryStatus:
    """For a restore-on-start prompt: is the recovery branch ahead of HEAD?"""
    head_sha = git_client.rev_parse(repo_root, "HEAD")
    recovery_sha = git_client.rev_parse(repo_root, RECOVERY_REF)
    if not recovery_sha or recovery_sha == head_sha:
        return RecoveryStatus(available=False)
    return RecoveryStatus(
        available=True, recovery_sha=recovery_sha, head_sha=head_sha or ""
    )


def list_recovery_checkpoints(
    git_client, repo_root: str, limit: int = 50
) -> list[RecoveryCheckpointEntry]:
    """
    Full gitpdm/recovery history, newest first -- for browsing/restoring
    any past checkpoint, not only ever the latest tip. A user report made
    this necessary: the checkpoint's real save is periodic and does touch
    the actual working file (that's the whole point -- see should_checkpoint's
    idle-debounce), so "restore the latest" alone is often a no-op once the
    working file already matches it; being able to go back to an earlier
    point in the session is what makes the recovery branch's continuous
    history actually useful rather than just a single redundant backup.
    """
    return git_client.list_recovery_checkpoints(repo_root, limit=limit)


def prune_recovery_branch(git_client, repo_root: str):
    """
    Delete the recovery branch once superseded by a real commit (R2.5's
    "prune/reset offer on next real commit"). Also clears the entire
    exported checkpoint-history folder tree (.git/gitpdm-recovery/) -- a
    real commit supersedes every earlier checkpoint by definition (it
    captures the current working tree, at least as up to date as any prior
    checkpoint of that same tree), so the accumulated per-checkpoint
    folders stop meaning anything either. Returns a CmdResult for the
    branch deletion; the folder cleanup is best-effort and doesn't affect
    the return value.
    """
    result = git_client.delete_recovery_branch(repo_root)
    _clear_all_recovery_exports(repo_root)
    return result


def _recovery_export_root(repo_root: str) -> str:
    return os.path.join(repo_root, ".git", RECOVERY_EXPORT_DIRNAME)


def _clear_all_recovery_exports(repo_root: str) -> None:
    shutil.rmtree(_recovery_export_root(repo_root), ignore_errors=True)


def _prune_old_recovery_exports(repo_root: str) -> None:
    """
    Keep only the most recent MAX_RETAINED_RECOVERY_EXPORTS export folders,
    deleting the rest. Safe because folder names are `<timestamp>-<sha8>`
    (see export_recovery_snapshot), so plain lexicographic sort is
    chronological order -- oldest names sort first.
    """
    export_root = _recovery_export_root(repo_root)
    try:
        names = sorted(
            name
            for name in os.listdir(export_root)
            if os.path.isdir(os.path.join(export_root, name))
        )
    except OSError:
        return
    excess = len(names) - MAX_RETAINED_RECOVERY_EXPORTS
    if excess <= 0:
        return
    for name in names[:excess]:
        shutil.rmtree(os.path.join(export_root, name), ignore_errors=True)


def restore_recovery_checkpoint(
    git_client, repo_root: str, recovery_sha: Optional[str] = None
) -> CmdResult:
    """
    Materialize the recovery branch's snapshot onto the working tree. Only
    safe to call when no document from this repo is open in FreeCAD -- the
    caller (ui/panel.py) must apply that guard before calling this, mirroring
    the existing "close all documents" checks around branch switching.
    """
    sha = recovery_sha or git_client.rev_parse(repo_root, RECOVERY_REF)
    if not sha:
        return CmdResult(False, "", "No recovery snapshot available", "NO_RECOVERY_SHA")
    return git_client.restore_from_recovery(repo_root, sha)


def export_recovery_snapshot(
    git_client, repo_root: str, recovery_sha: Optional[str] = None
) -> CmdResult:
    """
    Extract the recovery branch's snapshot into a dated, browsable folder
    under `.git/gitpdm-recovery/` instead of (in addition to, from the
    caller's point of view) overwriting the working tree -- gives the user
    a concrete artifact to open/compare/copy from by hand, addressing a
    real report where an in-place-only restore left no visible proof of
    what, if anything, actually happened. Safe to call regardless of
    whether any documents are open (never touches repo_root's real working
    tree, index, or HEAD -- see GitClient.export_recovery_snapshot).
    On success, `.stdout` holds the destination folder's absolute path.

    The folder is named `<timestamp>-<sha8>`, where the timestamp is the
    checkpoint commit's own commit time (via GitClient.commit_timestamp),
    NOT wall-clock "now" -- exporting can happen long after the checkpoint
    it's exporting (e.g. this function is also called automatically right
    after every checkpoint by ui/panel.py's _on_checkpoint_timer_tick, but
    ALSO on demand for an arbitrary older entry picked from the
    checkpoint-history browser), so using "now" would make folder names
    reflect when someone looked, not when the checkpoint actually happened
    -- exactly the "hard to chronologically track changes" problem a user
    report called out. Timestamp-first naming also means a plain
    alphabetical folder listing (Explorer's default) already sorts
    chronologically, no extra tooling needed. Prunes older exports down to
    MAX_RETAINED_RECOVERY_EXPORTS after a successful export (see
    _prune_old_recovery_exports) -- best-effort, doesn't affect the return
    value.
    """
    sha = recovery_sha or git_client.rev_parse(repo_root, RECOVERY_REF)
    if not sha:
        return CmdResult(False, "", "No recovery snapshot available", "NO_RECOVERY_SHA")

    commit_at = git_client.commit_timestamp(repo_root, sha)
    stamp = _folder_timestamp(commit_at)
    dest_dir = os.path.join(
        repo_root, ".git", RECOVERY_EXPORT_DIRNAME, f"{stamp}-{sha[:8]}"
    )
    result = git_client.export_recovery_snapshot(repo_root, sha, dest_dir)
    if result.ok:
        _prune_old_recovery_exports(repo_root)
    return result


def _folder_timestamp(commit_iso_at: Optional[str]) -> str:
    """Filename-safe, lexicographically-sortable timestamp derived from a
    checkpoint's own commit time; falls back to wall-clock "now" only if
    that timestamp couldn't be resolved at all (e.g. commit_timestamp()
    failed), so a folder is still produced rather than blocking export."""
    if commit_iso_at:
        try:
            return datetime.fromisoformat(commit_iso_at).strftime("%Y%m%d-%H%M%S")
        except ValueError:
            pass
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _last_checkpoint_marker_path(repo_root: str) -> str:
    return os.path.join(repo_root, ".git", _LAST_CHECKPOINT_FILENAME)


def note_last_checkpoint_file(repo_root: str, file_path: str) -> None:
    """
    Record which document a checkpoint just saved, so a later session's
    restore knows which file to reopen. Written directly to a plain JSON
    file under `.git/` -- deliberately NOT through FreeCAD's parameter
    store (core/settings.py) -- because FreeCAD's parameter tree is only
    guaranteed to reach disk on a clean shutdown, and surviving an unclean
    one (crash/force-quit) is the entire point of this feature; a user
    report confirmed the parameter-store version of this (this function's
    predecessor) came back empty after a force-quit, exactly the scenario
    it exists for. Mirrors core/session_lock.py's own reasoning for using
    a plain file instead of the parameter store. Best-effort: a failure
    here should never block the checkpoint itself.
    """
    try:
        path = _last_checkpoint_marker_path(repo_root)
        payload = {"file": file_path, "at": datetime.now(timezone.utc).isoformat()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except OSError as e:
        log.warning(f"Could not persist last-checkpoint-file marker: {e}")


def load_last_checkpoint_file(repo_root: str) -> str:
    """Load the path recorded by note_last_checkpoint_file(), or "" if
    none is recorded (or repo_root doesn't look like a repo yet)."""
    try:
        with open(_last_checkpoint_marker_path(repo_root), "r", encoding="utf-8") as f:
            data = json.load(f)
        return str(data.get("file", "") or "")
    except (FileNotFoundError, OSError, ValueError, KeyError, TypeError):
        return ""
