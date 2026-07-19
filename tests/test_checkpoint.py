# -*- coding: utf-8 -*-
"""
Tests for Phase G6 (R2.5): continuous checkpointing.

Two layers, tested separately per CLAUDE.md's "Tests must run without
FreeCAD": the scheduling/policy logic in core/checkpoint.py is pure Python
(fake clock, fake git_client) with zero FreeCAD or real-git dependency; the
git plumbing itself (GitClient.commit_recovery_checkpoint et al.) is
exercised against a real temporary repo, the same style as
test_generic_provider_flow.py, because the acceptance criteria here are
specifically about real git state (HEAD/index/working-tree byte-identity,
mainline history purity) that a mocked subprocess can't actually prove.
"""

from __future__ import annotations

import os
import subprocess
from unittest.mock import MagicMock

import pytest

from freecad_gitpdm.core import checkpoint, settings
from freecad_gitpdm.git.client import RECOVERY_REF, CmdResult, GitClient


# --- Real-git plumbing tests -------------------------------------------


@pytest.fixture
def git_client():
    client = GitClient()
    if not client.is_git_available():
        pytest.skip("git executable not available on this machine")
    return client


def _init_repo_with_commit(git_client, repo_root):
    init_result = git_client.init_repo(str(repo_root))
    assert init_result.ok, init_result.stderr
    git_client.set_config(str(repo_root), "user.name", "GitPDM Test", local=True)
    git_client.set_config(
        str(repo_root), "user.email", "gitpdm-test@example.invalid", local=True
    )
    (repo_root / "part.txt").write_text("revision 1\n", encoding="utf-8")
    git_client.stage_all(str(repo_root))
    commit = git_client.commit(str(repo_root), "Initial commit")
    assert commit.ok, commit.stderr


def _snapshot(path):
    """(HEAD sha, real-index bytes, sorted working-tree file listing+content)
    for the byte-identity assertion."""
    head = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    index_path = os.path.join(str(path), ".git", "index")
    index_bytes = open(index_path, "rb").read() if os.path.isfile(index_path) else b""
    files = {}
    for root, dirs, names in os.walk(path):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in names:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, path)
            files[rel] = open(full, "rb").read()
    return head, index_bytes, files


class TestCommitRecoveryCheckpoint:
    def test_checkpoint_leaves_head_index_and_working_tree_untouched(
        self, tmp_path, git_client
    ):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        _init_repo_with_commit(git_client, repo_root)

        # Dirty working tree the checkpoint should capture, without staging it.
        (repo_root / "part.txt").write_text("revision 2 (unsaved)\n", encoding="utf-8")
        (repo_root / "new_file.txt").write_text("untracked\n", encoding="utf-8")

        before = _snapshot(repo_root)

        result = git_client.commit_recovery_checkpoint(str(repo_root), "checkpoint 1")

        assert result.ok, result.stderr
        after = _snapshot(repo_root)
        assert before == after, "checkpoint must not touch HEAD, index, or working tree"

    def test_checkpoint_captures_current_working_tree_contents(
        self, tmp_path, git_client
    ):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        _init_repo_with_commit(git_client, repo_root)

        (repo_root / "part.txt").write_text("revision 2 (unsaved)\n", encoding="utf-8")
        (repo_root / "new_file.txt").write_text("untracked\n", encoding="utf-8")

        result = git_client.commit_recovery_checkpoint(str(repo_root), "checkpoint 1")
        assert result.ok, result.stderr
        sha = result.stdout

        show = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{sha}:part.txt"],
            capture_output=True,
            text=True,
        )
        assert show.stdout == "revision 2 (unsaved)\n"

        show_new = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{sha}:new_file.txt"],
            capture_output=True,
            text=True,
        )
        assert show_new.stdout == "untracked\n"

    def test_mainline_history_never_contains_recovery_commits(
        self, tmp_path, git_client
    ):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        _init_repo_with_commit(git_client, repo_root)

        (repo_root / "part.txt").write_text("dirty\n", encoding="utf-8")
        result = git_client.commit_recovery_checkpoint(str(repo_root), "checkpoint 1")
        assert result.ok, result.stderr

        log_result = subprocess.run(
            ["git", "-C", str(repo_root), "log", "--oneline", "HEAD"],
            capture_output=True,
            text=True,
        )
        assert "checkpoint" not in log_result.stdout.lower()

        branches = subprocess.run(
            ["git", "-C", str(repo_root), "branch", "--list"],
            capture_output=True,
            text=True,
        )
        # The recovery ref exists as its own branch, but it is never the
        # checked-out one ("*" marks the active branch).
        assert "* gitpdm/recovery" not in branches.stdout
        assert "gitpdm/recovery" in branches.stdout

    def test_second_checkpoint_chains_onto_first_not_head(self, tmp_path, git_client):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        _init_repo_with_commit(git_client, repo_root)

        (repo_root / "part.txt").write_text("dirty 1\n", encoding="utf-8")
        first = git_client.commit_recovery_checkpoint(str(repo_root), "checkpoint 1")
        assert first.ok, first.stderr

        (repo_root / "part.txt").write_text("dirty 2\n", encoding="utf-8")
        second = git_client.commit_recovery_checkpoint(str(repo_root), "checkpoint 2")
        assert second.ok, second.stderr

        parent = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", f"{second.stdout}^"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert parent == first.stdout

    def test_checkpoint_fails_cleanly_with_no_commits_yet(self, tmp_path, git_client):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        init_result = git_client.init_repo(str(repo_root))
        assert init_result.ok, init_result.stderr

        result = git_client.commit_recovery_checkpoint(str(repo_root), "checkpoint 1")

        assert result.ok is False
        assert result.error_code == "NO_HEAD"

    def test_rev_parse_returns_none_for_missing_ref(self, tmp_path, git_client):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        _init_repo_with_commit(git_client, repo_root)

        assert git_client.rev_parse(str(repo_root), RECOVERY_REF) is None
        assert git_client.rev_parse(str(repo_root), "HEAD") is not None


class TestRestoreAndPrune:
    def test_restore_from_recovery_writes_checkpointed_content(
        self, tmp_path, git_client
    ):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        _init_repo_with_commit(git_client, repo_root)

        (repo_root / "part.txt").write_text("checkpointed content\n", encoding="utf-8")
        checkpoint_result = git_client.commit_recovery_checkpoint(str(repo_root), "cp")
        assert checkpoint_result.ok, checkpoint_result.stderr

        # Simulate "crash lost the in-progress edit" by reverting on disk.
        (repo_root / "part.txt").write_text("revision 1\n", encoding="utf-8")

        head_before = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        ).stdout.strip()

        restore_result = git_client.restore_from_recovery(
            str(repo_root), checkpoint_result.stdout
        )
        assert restore_result.ok, restore_result.stderr
        assert (repo_root / "part.txt").read_text(encoding="utf-8") == (
            "checkpointed content\n"
        )

        head_after = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        # HEAD must not have moved -- this restores files, not branches.
        assert head_after == head_before

    def test_prune_recovery_branch_removes_local_ref(self, tmp_path, git_client):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        _init_repo_with_commit(git_client, repo_root)
        (repo_root / "part.txt").write_text("dirty\n", encoding="utf-8")
        assert git_client.commit_recovery_checkpoint(str(repo_root), "cp").ok
        assert git_client.rev_parse(str(repo_root), RECOVERY_REF) is not None

        git_client.delete_recovery_branch(str(repo_root))

        assert git_client.rev_parse(str(repo_root), RECOVERY_REF) is None

    def test_recovery_branch_status_reports_availability(self, tmp_path, git_client):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        _init_repo_with_commit(git_client, repo_root)

        assert (
            checkpoint.recovery_branch_status(git_client, str(repo_root)).available
            is False
        )

        (repo_root / "part.txt").write_text("dirty\n", encoding="utf-8")
        cp = git_client.commit_recovery_checkpoint(str(repo_root), "cp")
        assert cp.ok

        status = checkpoint.recovery_branch_status(git_client, str(repo_root))
        assert status.available is True
        assert status.recovery_sha == cp.stdout


# --- Pure scheduling/policy tests (no FreeCAD, no real git) -------------


class TestShouldCheckpoint:
    def test_clean_state_never_checkpoints(self):
        state = checkpoint.CheckpointState()
        assert checkpoint.should_checkpoint(state, now=1000.0) is False

    def test_idle_after_activity_triggers(self):
        state = checkpoint.CheckpointState()
        state.note_activity(now=1000.0)
        assert checkpoint.should_checkpoint(state, now=1010.0, idle_seconds=45) is False
        assert checkpoint.should_checkpoint(state, now=1046.0, idle_seconds=45) is True

    def test_max_interval_backstop_fires_during_continuous_activity(self):
        state = checkpoint.CheckpointState()
        state.note_activity(now=1000.0)
        # Still within idle window, but the backstop should fire regardless.
        assert (
            checkpoint.should_checkpoint(
                state, now=1000.0 + 179, idle_seconds=200, max_interval_seconds=180
            )
            is False
        )
        assert (
            checkpoint.should_checkpoint(
                state, now=1000.0 + 181, idle_seconds=200, max_interval_seconds=180
            )
            is True
        )

    def test_backstop_measures_from_last_checkpoint_not_from_renewed_activity(self):
        state = checkpoint.CheckpointState()
        state.note_activity(now=1000.0)
        state.note_checkpoint(now=1000.0)  # clears dirty; backstop baseline = 1000
        state.note_activity(now=1100.0)  # dirty again; activity clock resets

        # idle_seconds kept out of reach so only the backstop can fire; it
        # must be measured from last_checkpoint_at (1000), not from the
        # renewed activity at 1100.
        assert (
            checkpoint.should_checkpoint(
                state, now=1000.0 + 179, idle_seconds=1000, max_interval_seconds=180
            )
            is False
        )
        assert (
            checkpoint.should_checkpoint(
                state, now=1000.0 + 181, idle_seconds=1000, max_interval_seconds=180
            )
            is True
        )

    def test_note_checkpoint_clears_dirty_flag(self):
        state = checkpoint.CheckpointState()
        state.note_activity(now=1000.0)
        assert state.dirty is True
        state.note_checkpoint(now=1050.0)
        assert state.dirty is False
        assert checkpoint.should_checkpoint(state, now=5000.0) is False


class TestMaxIntervalForRepo:
    def test_delta_mode_uses_default_interval(self, tmp_path):
        repo_root = tmp_path / "repo"
        (repo_root / ".freecad-pdm").mkdir(parents=True)
        assert (
            checkpoint.max_interval_seconds_for_repo(str(repo_root))
            == checkpoint.DEFAULT_MAX_INTERVAL_SECONDS
        )

    def test_lfs_mode_lengthens_interval(self, tmp_path):
        from freecad_gitpdm.core import storage_mode

        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        storage_mode.apply_storage_mode(str(repo_root), storage_mode.MODE_LFS)

        assert (
            checkpoint.max_interval_seconds_for_repo(str(repo_root))
            == checkpoint.LFS_MAX_INTERVAL_SECONDS
        )
        assert (
            checkpoint.LFS_MAX_INTERVAL_SECONDS
            > checkpoint.DEFAULT_MAX_INTERVAL_SECONDS
        )


class TestShouldAutoPushRecovery:
    def test_default_is_push_on_desktop(self, monkeypatch):
        """Revised 2026-07-19: push-by-default applies on a plain desktop
        session too, not just when headless env-var backends are active --
        a checkpoint should be an off-machine record right away."""
        monkeypatch.delenv("GITPDM_TOKEN", raising=False)
        monkeypatch.delenv("GITPDM_TOKEN_FILE", raising=False)
        monkeypatch.setattr(
            settings, "load_checkpoint_auto_push_override", lambda: None
        )

        assert checkpoint.should_auto_push_recovery() is True

    def test_default_is_push_when_headless_too(self, monkeypatch):
        monkeypatch.setenv("GITPDM_TOKEN", "fake-token")
        monkeypatch.setattr(
            settings, "load_checkpoint_auto_push_override", lambda: None
        )

        assert checkpoint.should_auto_push_recovery() is True

    def test_explicit_override_can_disable_push(self, monkeypatch):
        monkeypatch.setattr(
            settings, "load_checkpoint_auto_push_override", lambda: False
        )

        assert checkpoint.should_auto_push_recovery() is False

    def test_explicit_override_can_force_push(self, monkeypatch):
        monkeypatch.setattr(
            settings, "load_checkpoint_auto_push_override", lambda: True
        )

        assert checkpoint.should_auto_push_recovery() is True


class TestCheckpointAutoPushOverrideSetting:
    def test_defaults_to_none(self, monkeypatch):
        monkeypatch.setattr(settings, "load_setting", lambda key, default="": default)
        assert settings.load_checkpoint_auto_push_override() is None

    def test_round_trips_true_and_false(self, monkeypatch):
        store = {}
        monkeypatch.setattr(
            settings,
            "save_setting",
            lambda key, value: store.__setitem__(key, str(value)),
        )
        monkeypatch.setattr(
            settings, "load_setting", lambda key, default="": store.get(key, default)
        )

        settings.save_checkpoint_auto_push_override(True)
        assert settings.load_checkpoint_auto_push_override() is True

        settings.save_checkpoint_auto_push_override(False)
        assert settings.load_checkpoint_auto_push_override() is False

        settings.save_checkpoint_auto_push_override(None)
        assert settings.load_checkpoint_auto_push_override() is None


class TestRunCheckpoint:
    def _fake_git_client(self, commit_ok=True, push_ok=True):
        client = MagicMock()
        client.commit_recovery_checkpoint.return_value = CmdResult(
            commit_ok, "abc123" if commit_ok else "", "" if commit_ok else "boom"
        )
        client.push_ref.return_value = CmdResult(
            push_ok, "", "" if push_ok else "push failed"
        )
        return client

    def test_busy_document_defers_and_does_not_save_or_commit(self):
        client = self._fake_git_client()
        save_calls = []

        result = checkpoint.run_checkpoint(
            client,
            "/repo",
            is_busy=lambda: True,
            save_if_dirty=lambda: save_calls.append(1),
        )

        assert result.ok is False
        assert result.skipped_reason == "busy"
        assert save_calls == []
        client.commit_recovery_checkpoint.assert_not_called()

    def test_not_busy_saves_then_commits(self):
        client = self._fake_git_client()
        save_calls = []

        result = checkpoint.run_checkpoint(
            client,
            "/repo",
            is_busy=lambda: False,
            save_if_dirty=lambda: save_calls.append(1),
        )

        assert result.ok is True
        assert result.sha == "abc123"
        assert save_calls == [1]
        client.commit_recovery_checkpoint.assert_called_once()

    def test_commit_failure_propagates(self):
        client = self._fake_git_client(commit_ok=False)

        result = checkpoint.run_checkpoint(
            client, "/repo", is_busy=lambda: False, save_if_dirty=lambda: None
        )

        assert result.ok is False
        client.push_ref.assert_not_called()

    def test_push_only_happens_when_policy_says_so(self, monkeypatch):
        client = self._fake_git_client()
        monkeypatch.setattr(checkpoint, "should_auto_push_recovery", lambda: False)

        result = checkpoint.run_checkpoint(
            client, "/repo", is_busy=lambda: False, save_if_dirty=lambda: None
        )

        assert result.ok is True
        assert result.pushed is False
        client.push_ref.assert_not_called()

    def test_push_runs_when_policy_says_so(self, monkeypatch):
        client = self._fake_git_client()
        monkeypatch.setattr(checkpoint, "should_auto_push_recovery", lambda: True)

        result = checkpoint.run_checkpoint(
            client, "/repo", is_busy=lambda: False, save_if_dirty=lambda: None
        )

        assert result.ok is True
        assert result.pushed is True
        client.push_ref.assert_called_once_with("/repo", RECOVERY_REF)

    def test_shutdown_checkpoint_ignores_busy_guard(self):
        client = self._fake_git_client()
        save_calls = []

        # No is_busy is even accepted -- run_shutdown_checkpoint hardcodes
        # is_busy=lambda: False and respect_busy_guard=False, so a "busy"
        # document doesn't block the shutdown path.
        result = checkpoint.run_shutdown_checkpoint(
            client, "/repo", save_if_dirty=lambda: save_calls.append(1)
        )

        assert result.ok is True
        assert save_calls == [1]


class TestSigtermHandler:
    def test_register_sigterm_handler_returns_bool(self):
        called = []
        ok = checkpoint.register_sigterm_handler(lambda: called.append(1))
        # On platforms without SIGTERM support this would be False; on CI
        # Linux/macOS/Windows-with-Python-signal-support it should succeed.
        assert isinstance(ok, bool)
