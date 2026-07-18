# -*- coding: utf-8 -*-
"""Tests for freecad_gitpdm.core.session_lock (Phase G5 / R2.3)."""

import json
import os
import sys

from freecad_gitpdm.core import session_lock


def _make_repo(tmp_path):
    repo_root = tmp_path / "repo"
    (repo_root / ".git").mkdir(parents=True)
    return str(repo_root)


def _lock_file(repo_root):
    return os.path.join(repo_root, ".git", session_lock.LOCK_FILENAME)


def test_acquire_lock_writes_file_when_free(tmp_path):
    repo_root = _make_repo(tmp_path)

    result = session_lock.acquire_lock(repo_root)

    assert result.ok is True
    assert os.path.isfile(_lock_file(repo_root))
    with open(_lock_file(repo_root)) as f:
        data = json.load(f)
    assert data["pid"] == os.getpid()
    assert "timestamp" in data
    assert "hostname" in data


def test_acquire_lock_reacquire_same_pid_succeeds(tmp_path):
    repo_root = _make_repo(tmp_path)

    first = session_lock.acquire_lock(repo_root)
    second = session_lock.acquire_lock(repo_root)

    assert first.ok is True
    assert second.ok is True


def test_acquire_lock_blocked_by_live_foreign_pid(tmp_path, monkeypatch):
    repo_root = _make_repo(tmp_path)
    foreign_pid = os.getpid() + 1

    with open(_lock_file(repo_root), "w") as f:
        json.dump(
            {
                "pid": foreign_pid,
                "timestamp": "2026-07-18T00:00:00+00:00",
                "hostname": "other-host",
            },
            f,
        )

    monkeypatch.setattr(session_lock, "_pid_alive", lambda pid: pid == foreign_pid)
    # Freeze "now" close to the lock's timestamp so it isn't judged stale by age.
    import datetime as real_datetime

    class _FrozenDateTime(real_datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.datetime(2026, 7, 18, 0, 1, tzinfo=tz)

    monkeypatch.setattr(session_lock, "datetime", _FrozenDateTime)

    result = session_lock.acquire_lock(repo_root)

    assert result.ok is False
    assert result.existing is not None
    assert result.existing.pid == foreign_pid
    assert result.existing.hostname == "other-host"


def test_acquire_lock_dead_pid_auto_clears(tmp_path, monkeypatch):
    repo_root = _make_repo(tmp_path)
    dead_pid = os.getpid() + 1

    with open(_lock_file(repo_root), "w") as f:
        json.dump(
            {
                "pid": dead_pid,
                "timestamp": "2026-07-18T00:00:00+00:00",
                "hostname": "h",
            },
            f,
        )

    monkeypatch.setattr(session_lock, "_pid_alive", lambda pid: pid != dead_pid)

    result = session_lock.acquire_lock(repo_root)

    assert result.ok is True
    with open(_lock_file(repo_root)) as f:
        data = json.load(f)
    assert data["pid"] == os.getpid()


def test_acquire_lock_stale_timestamp_auto_clears(tmp_path, monkeypatch):
    repo_root = _make_repo(tmp_path)
    foreign_pid = os.getpid() + 1

    with open(_lock_file(repo_root), "w") as f:
        json.dump(
            {
                "pid": foreign_pid,
                "timestamp": "2020-01-01T00:00:00+00:00",
                "hostname": "other-host",
            },
            f,
        )

    # Still alive, but the timestamp is ancient -> treated as stale.
    monkeypatch.setattr(session_lock, "_pid_alive", lambda pid: True)

    result = session_lock.acquire_lock(repo_root)

    assert result.ok is True


def test_acquire_lock_force_steals_live_lock(tmp_path, monkeypatch):
    repo_root = _make_repo(tmp_path)
    foreign_pid = os.getpid() + 1

    with open(_lock_file(repo_root), "w") as f:
        json.dump(
            {
                "pid": foreign_pid,
                "timestamp": "2026-07-18T00:00:00+00:00",
                "hostname": "other-host",
            },
            f,
        )

    monkeypatch.setattr(session_lock, "_pid_alive", lambda pid: True)
    import datetime as real_datetime

    class _FrozenDateTime(real_datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.datetime(2026, 7, 18, 0, 1, tzinfo=tz)

    monkeypatch.setattr(session_lock, "datetime", _FrozenDateTime)

    result = session_lock.acquire_lock(repo_root, force=True)

    assert result.ok is True
    with open(_lock_file(repo_root)) as f:
        data = json.load(f)
    assert data["pid"] == os.getpid()


def test_release_lock_removes_own_lock(tmp_path):
    repo_root = _make_repo(tmp_path)
    session_lock.acquire_lock(repo_root)
    assert os.path.isfile(_lock_file(repo_root))

    session_lock.release_lock(repo_root)

    assert not os.path.isfile(_lock_file(repo_root))


def test_release_lock_does_not_remove_foreign_lock(tmp_path):
    repo_root = _make_repo(tmp_path)
    foreign_pid = os.getpid() + 1
    with open(_lock_file(repo_root), "w") as f:
        json.dump(
            {
                "pid": foreign_pid,
                "timestamp": "2026-07-18T00:00:00+00:00",
                "hostname": "h",
            },
            f,
        )

    session_lock.release_lock(repo_root)

    assert os.path.isfile(_lock_file(repo_root))


def test_refresh_lock_updates_timestamp(tmp_path):
    repo_root = _make_repo(tmp_path)
    session_lock.acquire_lock(repo_root)
    with open(_lock_file(repo_root)) as f:
        original = json.load(f)

    session_lock.refresh_lock(repo_root)

    with open(_lock_file(repo_root)) as f:
        refreshed = json.load(f)
    assert refreshed["pid"] == original["pid"]


def test_acquire_lock_no_op_when_not_a_git_repo(tmp_path):
    non_repo = tmp_path / "not_a_repo"
    non_repo.mkdir()

    result = session_lock.acquire_lock(str(non_repo))

    assert result.ok is True
    assert not os.path.isdir(os.path.join(str(non_repo), ".git"))


def test_pid_alive_true_for_current_process():
    assert session_lock._pid_alive(os.getpid()) is True


def test_pid_alive_false_for_bogus_pid():
    # A PID astronomically unlikely to exist on either platform.
    assert session_lock._pid_alive(2**30) is False
