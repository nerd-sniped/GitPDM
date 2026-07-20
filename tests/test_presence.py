# -*- coding: utf-8 -*-
"""
Tests for freecad_gitpdm.core.presence (Plan A, 2026-07-20).

Exercised against a real temporary repo + a real bare "remote", the same
style as test_generic_provider_flow.py/test_checkpoint.py, because the
acceptance criteria here are specifically about real cross-repo git state
(what one user's clone can see of another's presence commits) that a mocked
subprocess can't actually prove.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from freecad_gitpdm.core import presence
from freecad_gitpdm.git.client import PRESENCE_REF, GitClient


@pytest.fixture
def git_client():
    client = GitClient()
    if not client.is_git_available():
        pytest.skip("git executable not available on this machine")
    return client


def _make_bare_remote(tmp_path):
    remote_dir = tmp_path / "remote.git"
    remote_dir.mkdir()
    client = GitClient()
    result = client._run_command(
        [client._get_git_command(), "init", "--bare", str(remote_dir)]
    )
    assert result.ok, result.stderr
    return str(remote_dir)


def _make_user_repo(git_client, tmp_path, dirname, remote_dir, name, email):
    repo_root = tmp_path / dirname
    repo_root.mkdir()
    init_result = git_client.init_repo(str(repo_root))
    assert init_result.ok, init_result.stderr
    git_client.set_config(str(repo_root), "user.name", name, local=True)
    git_client.set_config(str(repo_root), "user.email", email, local=True)
    remote_result = git_client.add_remote(str(repo_root), "origin", remote_dir)
    assert remote_result.ok, remote_result.stderr
    return str(repo_root)


@pytest.fixture
def two_user_repos(tmp_path, git_client):
    remote_dir = _make_bare_remote(tmp_path)
    repo_a = _make_user_repo(
        git_client, tmp_path, "user_a", remote_dir, "Alice", "alice@example.invalid"
    )
    repo_b = _make_user_repo(
        git_client, tmp_path, "user_b", remote_dir, "Bob", "bob@example.invalid"
    )
    return repo_a, repo_b


class TestAnnounceOpen:
    def test_first_opener_sees_nobody_else(self, git_client, two_user_repos):
        repo_a, _ = two_user_repos

        other = presence.announce_open(git_client, repo_a, "Part.FCStd")

        assert other is None

    def test_second_user_sees_first_users_entry(self, git_client, two_user_repos):
        repo_a, repo_b = two_user_repos

        presence.announce_open(git_client, repo_a, "Part.FCStd")
        other = presence.announce_open(git_client, repo_b, "Part.FCStd")

        assert other is not None
        assert other.user == "Alice"

    def test_different_files_dont_collide(self, git_client, two_user_repos):
        repo_a, repo_b = two_user_repos

        presence.announce_open(git_client, repo_a, "Part.FCStd")
        other = presence.announce_open(git_client, repo_b, "OtherPart.FCStd")

        assert other is None

    def test_presence_commit_lands_on_dedicated_ref_not_head(
        self, git_client, two_user_repos
    ):
        repo_a, _ = two_user_repos

        presence.announce_open(git_client, repo_a, "Part.FCStd")

        assert git_client.rev_parse(repo_a, "HEAD") is None  # never touched
        assert git_client.rev_parse(repo_a, PRESENCE_REF) is not None

    def test_reopening_own_file_is_not_treated_as_someone_else(
        self, git_client, two_user_repos
    ):
        repo_a, _ = two_user_repos

        presence.announce_open(git_client, repo_a, "Part.FCStd")
        other = presence.announce_open(git_client, repo_a, "Part.FCStd")

        assert other is None


class TestHeartbeat:
    def test_heartbeat_refreshes_timestamp_without_changing_opened_at(
        self, git_client, two_user_repos
    ):
        repo_a, _ = two_user_repos
        presence.announce_open(git_client, repo_a, "Part.FCStd")
        content = git_client.read_file_at_ref(
            repo_a, PRESENCE_REF, presence.PRESENCE_FILENAME
        )
        before = json.loads(content)["Part.FCStd"]

        presence.heartbeat(git_client, repo_a, "Part.FCStd")

        content = git_client.read_file_at_ref(
            repo_a, PRESENCE_REF, presence.PRESENCE_FILENAME
        )
        after = json.loads(content)["Part.FCStd"]
        assert after["opened_at"] == before["opened_at"]
        assert after["last_heartbeat"] >= before["last_heartbeat"]

    def test_heartbeat_is_visible_to_other_users(self, git_client, two_user_repos):
        repo_a, repo_b = two_user_repos
        presence.announce_open(git_client, repo_a, "Part.FCStd")

        presence.heartbeat(git_client, repo_a, "Part.FCStd")
        other = presence.announce_open(git_client, repo_b, "Part.FCStd")

        assert other is not None
        assert other.user == "Alice"


class TestAnnounceClose:
    def test_close_removes_own_entry(self, git_client, two_user_repos):
        repo_a, repo_b = two_user_repos
        presence.announce_open(git_client, repo_a, "Part.FCStd")

        presence.announce_close(git_client, repo_a, "Part.FCStd")

        other = presence.announce_open(git_client, repo_b, "Part.FCStd")
        assert other is None

    def test_close_never_removes_a_foreign_entry(self, git_client, two_user_repos):
        repo_a, repo_b = two_user_repos
        presence.announce_open(git_client, repo_a, "Part.FCStd")
        # Bob fetches Alice's state but never actually opened the file --
        # calling close for a file he never announced open for must be a
        # no-op, never touching Alice's entry.
        git_client.fetch_ref(repo_b, PRESENCE_REF)

        presence.announce_close(git_client, repo_b, "Part.FCStd")

        content = git_client.read_file_at_ref(
            repo_a, PRESENCE_REF, presence.PRESENCE_FILENAME
        )
        assert content is not None
        assert "Part.FCStd" in json.loads(content)

    def test_close_on_never_opened_file_is_a_no_op(self, git_client, two_user_repos):
        repo_a, _ = two_user_repos

        presence.announce_close(
            git_client, repo_a, "NeverOpened.FCStd"
        )  # must not raise

        assert git_client.rev_parse(repo_a, PRESENCE_REF) is None


class TestStaleness:
    def test_stale_entry_is_not_reported_as_someone_else(
        self, git_client, two_user_repos
    ):
        repo_a, repo_b = two_user_repos
        presence.announce_open(git_client, repo_a, "Part.FCStd")

        # Rewrite Alice's own entry with an ancient heartbeat, simulating a
        # crashed session that never announced a close.
        content = git_client.read_file_at_ref(
            repo_a, PRESENCE_REF, presence.PRESENCE_FILENAME
        )
        data = json.loads(content)
        ancient = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        data["Part.FCStd"]["last_heartbeat"] = ancient
        blob_sha = git_client.hash_object(repo_a, json.dumps(data))
        tree_sha = git_client.make_tree_with_file(
            repo_a, presence.PRESENCE_FILENAME, blob_sha
        )
        parent = git_client.rev_parse(repo_a, PRESENCE_REF)
        commit_result = git_client.commit_tree_with_parent(
            repo_a, tree_sha, parent, "backdate for staleness test"
        )
        git_client.update_ref_cas(
            repo_a, PRESENCE_REF, commit_result.stdout.strip(), expected_old_sha=parent
        )
        git_client.push_ref(repo_a, PRESENCE_REF)

        other = presence.announce_open(git_client, repo_b, "Part.FCStd")

        assert other is None


class TestDescribeLastSeen:
    def test_moments_ago(self):
        now = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
        entry = presence.PresenceEntry(
            user="Alice", host="H", opened_at="", last_heartbeat=now.isoformat()
        )
        assert presence.describe_last_seen(entry, now=now) == "moments ago"

    def test_minutes_ago(self):
        now = datetime(2026, 7, 20, 12, 5, 0, tzinfo=timezone.utc)
        seen = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
        entry = presence.PresenceEntry(
            user="Alice", host="H", opened_at="", last_heartbeat=seen.isoformat()
        )
        assert presence.describe_last_seen(entry, now=now) == "5m ago"

    def test_hours_ago(self):
        now = datetime(2026, 7, 20, 15, 0, 0, tzinfo=timezone.utc)
        seen = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
        entry = presence.PresenceEntry(
            user="Alice", host="H", opened_at="", last_heartbeat=seen.isoformat()
        )
        assert presence.describe_last_seen(entry, now=now) == "3h ago"

    def test_unparseable_timestamp_falls_back_to_recently(self):
        entry = presence.PresenceEntry(
            user="Alice", host="H", opened_at="", last_heartbeat="not-a-timestamp"
        )
        assert presence.describe_last_seen(entry) == "recently"


class TestGitClientPresencePlumbing:
    """Direct tests of the new GitClient plumbing methods, independent of
    core/presence.py's merge policy."""

    def test_hash_object_and_read_back_via_tree_commit(self, git_client, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        init_result = git_client.init_repo(str(repo_root))
        assert init_result.ok, init_result.stderr

        blob_sha = git_client.hash_object(str(repo_root), "hello world\n")
        assert blob_sha

        tree_sha = git_client.make_tree_with_file(
            str(repo_root), "greeting.txt", blob_sha
        )
        assert tree_sha

        commit_result = git_client.commit_tree_with_parent(
            str(repo_root), tree_sha, None, "root commit"
        )
        assert commit_result.ok, commit_result.stderr
        commit_sha = commit_result.stdout.strip()

        update_result = git_client.update_ref_cas(
            str(repo_root), "refs/heads/gitpdm/test-plumbing", commit_sha
        )
        assert update_result.ok, update_result.stderr

        content = git_client.read_file_at_ref(
            str(repo_root), "refs/heads/gitpdm/test-plumbing", "greeting.txt"
        )
        # Trailing whitespace is stripped, matching every other CmdResult.stdout
        # in this codebase -- harmless for the JSON payload this is built for.
        assert content == "hello world"

    def test_update_ref_cas_rejects_stale_expected_sha(self, git_client, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        git_client.init_repo(str(repo_root))

        blob_sha = git_client.hash_object(str(repo_root), "v1\n")
        tree_sha = git_client.make_tree_with_file(str(repo_root), "f.txt", blob_sha)
        commit1 = git_client.commit_tree_with_parent(
            str(repo_root), tree_sha, None, "v1"
        )
        ref = "refs/heads/gitpdm/test-cas"
        git_client.update_ref_cas(str(repo_root), ref, commit1.stdout.strip())

        # A second writer's commit lands...
        blob2 = git_client.hash_object(str(repo_root), "v2\n")
        tree2 = git_client.make_tree_with_file(str(repo_root), "f.txt", blob2)
        commit2 = git_client.commit_tree_with_parent(
            str(repo_root), tree2, commit1.stdout.strip(), "v2"
        )
        git_client.update_ref_cas(
            str(repo_root),
            ref,
            commit2.stdout.strip(),
            expected_old_sha=commit1.stdout.strip(),
        )

        # ...then a stale writer, still holding the old parent, tries to CAS
        # in a third version against the now-outdated commit1 -- must fail.
        blob3 = git_client.hash_object(str(repo_root), "v3-stale\n")
        tree3 = git_client.make_tree_with_file(str(repo_root), "f.txt", blob3)
        commit3 = git_client.commit_tree_with_parent(
            str(repo_root), tree3, commit1.stdout.strip(), "v3 stale"
        )
        result = git_client.update_ref_cas(
            str(repo_root),
            ref,
            commit3.stdout.strip(),
            expected_old_sha=commit1.stdout.strip(),
        )

        assert result.ok is False

    def test_fetch_ref_pulls_remote_branch_into_matching_local_ref(
        self, git_client, tmp_path
    ):
        remote_dir = _make_bare_remote(tmp_path)
        repo_a = _make_user_repo(
            git_client, tmp_path, "user_a", remote_dir, "Alice", "alice@example.invalid"
        )
        repo_b = _make_user_repo(
            git_client, tmp_path, "user_b", remote_dir, "Bob", "bob@example.invalid"
        )

        blob_sha = git_client.hash_object(repo_a, "data\n")
        tree_sha = git_client.make_tree_with_file(repo_a, "f.txt", blob_sha)
        commit_result = git_client.commit_tree_with_parent(
            repo_a, tree_sha, None, "msg"
        )
        git_client.update_ref_cas(repo_a, PRESENCE_REF, commit_result.stdout.strip())
        git_client.push_ref(repo_a, PRESENCE_REF)

        assert git_client.rev_parse(repo_b, PRESENCE_REF) is None

        fetch_result = git_client.fetch_ref(repo_b, PRESENCE_REF)

        assert fetch_result.ok, fetch_result.stderr
        assert (
            git_client.rev_parse(repo_b, PRESENCE_REF) == commit_result.stdout.strip()
        )
