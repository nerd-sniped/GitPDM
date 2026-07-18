# -*- coding: utf-8 -*-
"""
Phase G4 forcing test (R5.1): GenericProvider against a bare git remote
completes configure -> clone -> save -> commit -> push, with zero HTTP
calls.

This is what "GenericProvider alone must make GitPDM fully functional"
means in practice: the transport layer (git/client.py) is already
host-agnostic, so the only thing G4 adds is the provider choice itself
(core/provider_config.py) plus the guarantee that nothing on this path
touches urllib. We assert that guarantee directly by making urlopen raise
if it's ever called.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from freecad_gitpdm.core import provider_config
from freecad_gitpdm.git.client import GitClient
from freecad_gitpdm.providers import get_provider
from freecad_gitpdm.providers.base import GenericProvider


def _fail_if_called(*args, **kwargs):
    raise AssertionError(
        "GenericProvider flow made an HTTP call via urllib — it must make "
        "zero host API calls by construction (R5.1)."
    )


@pytest.fixture
def git_client():
    client = GitClient()
    if not client.is_git_available():
        pytest.skip("git executable not available on this machine")
    return client


class TestGenericProviderEndToEnd:
    def test_configure_clone_save_commit_push(self, tmp_path, git_client):
        remote_dir = tmp_path / "remote.git"
        remote_dir.mkdir()
        bare_init = git_client._run_command(
            [git_client._get_git_command(), "init", "--bare", str(remote_dir)],
            timeout=15,
        )
        assert bare_init.ok, bare_init.stderr

        with patch("urllib.request.urlopen", side_effect=_fail_if_called):
            # === configure: pick GenericProvider for this repo ===
            work_dir = tmp_path / "work"
            work_dir.mkdir()

            provider_config.set_provider_config(str(work_dir), "generic")
            provider = get_provider(provider_config.get_provider_id(str(work_dir)))
            assert isinstance(provider, GenericProvider)
            assert provider.capabilities.supports_repo_creation is False
            # GenericProvider has no host API client at all.
            assert provider.build_api_client("unused-token") is None

            # === "clone": init a local repo and point it at the bare remote
            # (GenericProvider's repo-creation story is "paste a URL you
            # already have" — a local bare repo stands in for that here) ===
            init_result = git_client.init_repo(str(work_dir))
            assert init_result.ok, init_result.stderr

            git_client.set_config(str(work_dir), "user.name", "GitPDM Test", local=True)
            git_client.set_config(
                str(work_dir), "user.email", "gitpdm-test@example.invalid", local=True
            )

            remote_result = git_client.add_remote(
                str(work_dir), "origin", str(remote_dir)
            )
            assert remote_result.ok, remote_result.stderr

            # === save: write a file into the working tree ===
            (work_dir / "part.txt").write_text("revision 1\n", encoding="utf-8")

            # === commit ===
            stage_result = git_client.stage_all(str(work_dir))
            assert stage_result.ok, stage_result.stderr

            commit_result = git_client.commit(str(work_dir), "Initial commit")
            assert commit_result.ok, commit_result.stderr

            # === push ===
            push_result = git_client.push(str(work_dir), "origin")
            assert push_result.ok, push_result.stderr

        # The remote actually received the commit.
        log_in_bare = git_client._run_command(
            [git_client._get_git_command(), "-C", str(remote_dir), "log", "--oneline"],
            timeout=15,
        )
        assert log_in_bare.ok
        assert "Initial commit" in log_in_bare.stdout
