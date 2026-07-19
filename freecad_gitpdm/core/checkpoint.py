# -*- coding: utf-8 -*-
"""
GitPDM Continuous Checkpointing (Phase G6 / R2.5)

Delivers an Onshape-style "walk away anytime, lose <= ~1 minute" guarantee
via debounced checkpoints onto a `gitpdm/recovery` branch -- not per-action
persistence, which is prohibitive on FreeCAD's blocking whole-file save (see
R2.5's rationale in GITPDM_DEV_PLAN.md).

This module is deliberately FreeCAD-agnostic (CLAUDE.md: "Tests must run
without FreeCAD"). The two things only FreeCAD can answer -- "is the user
mid-edit right now" and "perform the actual document save" -- are taken as
injected callables (`is_busy`/`save_if_dirty`) rather than imported here;
`ui/panel.py` supplies the real FreeCAD-backed versions. Git plumbing itself
lives on GitClient (`git/client.py`), per the existing convention that all
git operations go through there.
"""

from __future__ import annotations

import signal
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from freecad_gitpdm.core import log, settings, storage_mode
from freecad_gitpdm.git.client import RECOVERY_REF, CmdResult

# Idle-debounce: a checkpoint fires once the document has been dirty and
# untouched for this long (within R2.5's 30-60s band).
DEFAULT_IDLE_SECONDS = 45

# Max-interval backstop: a checkpoint fires even without idle time, so
# continuous active editing still gets checkpointed periodically (within
# R2.5's 2-5min band).
DEFAULT_MAX_INTERVAL_SECONDS = 180

# In "lfs" storage mode each checkpoint is a full stored LFS object rather
# than a cheap delta-compressible commit, so the backstop is lengthened
# (R2.5's settings-coupling requirement).
LFS_MAX_INTERVAL_SECONDS = 600


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


@dataclass
class RecoveryStatus:
    available: bool
    recovery_sha: str = ""
    head_sha: str = ""


def max_interval_seconds_for_repo(repo_root) -> int:
    """R2.5's settings coupling: lfs mode gets a longer backstop interval."""
    mode = storage_mode.get_storage_mode(repo_root)
    if mode == storage_mode.MODE_LFS:
        return LFS_MAX_INTERVAL_SECONDS
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
    save_if_dirty: Callable[[], None],
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
    commit to capture.

    `respect_busy_guard=False` is for the shutdown path (see
    run_shutdown_checkpoint): the process is exiting regardless, so there is
    no "later" to defer to -- capture whatever can be captured now.
    """
    if respect_busy_guard and is_busy():
        return CheckpointResult(ok=False, skipped_reason="busy")

    save_if_dirty()

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

    return CheckpointResult(ok=True, sha=commit_result.stdout, pushed=pushed)


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


def prune_recovery_branch(git_client, repo_root: str):
    """Delete the recovery branch once superseded by a real commit (R2.5's
    "prune/reset offer on next real commit"). Returns a CmdResult."""
    return git_client.delete_recovery_branch(repo_root)


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
