# -*- coding: utf-8 -*-
"""
Tests for core.storage_mode (Phase G3): repo-scoped storage mode
(.freecad-pdm/config.json) and the .gitattributes stanza it drives.
"""

from freecad_gitpdm.core import storage_mode


class TestGetStorageMode:
    def test_defaults_to_delta_when_no_config(self, tmp_path):
        assert storage_mode.get_storage_mode(str(tmp_path)) == storage_mode.MODE_DELTA

    def test_reads_configured_mode(self, tmp_path):
        storage_mode.apply_storage_mode(str(tmp_path), storage_mode.MODE_LFS)
        assert storage_mode.get_storage_mode(str(tmp_path)) == storage_mode.MODE_LFS

    def test_falls_back_to_default_on_invalid_value(self, tmp_path):
        cfg_dir = tmp_path / ".freecad-pdm"
        cfg_dir.mkdir()
        (cfg_dir / "config.json").write_text(
            '{"storageMode": "bogus"}', encoding="utf-8"
        )
        assert storage_mode.get_storage_mode(str(tmp_path)) == storage_mode.MODE_DELTA

    def test_falls_back_to_default_on_malformed_json(self, tmp_path):
        cfg_dir = tmp_path / ".freecad-pdm"
        cfg_dir.mkdir()
        (cfg_dir / "config.json").write_text("{not json", encoding="utf-8")
        assert storage_mode.get_storage_mode(str(tmp_path)) == storage_mode.MODE_DELTA


class TestApplyStorageModeDelta:
    def test_writes_exact_delta_stanza(self, tmp_path):
        result = storage_mode.apply_storage_mode(str(tmp_path), storage_mode.MODE_DELTA)
        assert result.ok

        content = (tmp_path / ".gitattributes").read_text(encoding="utf-8")
        assert "*.FCStd binary" in content
        assert "-delta" not in content
        assert "filter=lfs" not in content

    def test_switching_from_lfs_to_delta_removes_lfs_filter(self, tmp_path):
        storage_mode.apply_storage_mode(str(tmp_path), storage_mode.MODE_LFS)
        result = storage_mode.apply_storage_mode(str(tmp_path), storage_mode.MODE_DELTA)
        assert result.ok

        content = (tmp_path / ".gitattributes").read_text(encoding="utf-8")
        fcstd_lines = [
            ln for ln in content.splitlines() if ln.strip().startswith("*.FCStd")
        ]
        assert fcstd_lines == ["*.FCStd binary"]

    def test_preserves_unrelated_gitattributes_lines(self, tmp_path):
        (tmp_path / ".gitattributes").write_text(
            "*.png binary\n# a comment\n", encoding="utf-8"
        )
        storage_mode.apply_storage_mode(str(tmp_path), storage_mode.MODE_DELTA)

        content = (tmp_path / ".gitattributes").read_text(encoding="utf-8")
        assert "*.png binary" in content
        assert "# a comment" in content
        assert "*.FCStd binary" in content


class TestApplyStorageModeLfs:
    def test_writes_exact_lfs_stanza(self, tmp_path):
        result = storage_mode.apply_storage_mode(str(tmp_path), storage_mode.MODE_LFS)
        assert result.ok

        content = (tmp_path / ".gitattributes").read_text(encoding="utf-8")
        assert "*.FCStd filter=lfs diff=lfs merge=lfs -text" in content

    def test_switching_from_delta_to_lfs_removes_binary_line(self, tmp_path):
        storage_mode.apply_storage_mode(str(tmp_path), storage_mode.MODE_DELTA)
        result = storage_mode.apply_storage_mode(str(tmp_path), storage_mode.MODE_LFS)
        assert result.ok

        content = (tmp_path / ".gitattributes").read_text(encoding="utf-8")
        fcstd_lines = [
            ln for ln in content.splitlines() if ln.strip().startswith("*.FCStd")
        ]
        assert fcstd_lines == ["*.FCStd filter=lfs diff=lfs merge=lfs -text"]

    def test_calls_lfs_install_when_git_client_given(self, tmp_path):
        class FakeResult:
            ok = True
            stderr = ""

        class FakeGitClient:
            def __init__(self):
                self.called = False

            def lfs_install(self):
                self.called = True
                return FakeResult()

        client = FakeGitClient()
        storage_mode.apply_storage_mode(
            str(tmp_path), storage_mode.MODE_LFS, git_client=client
        )
        assert client.called


class TestForbiddenStatesUnreachable:
    """R1.1: compression 0 + LFS, and -delta on *.FCStd, must never occur."""

    def test_never_writes_delta_flag_for_fcstd(self, tmp_path):
        for mode in (storage_mode.MODE_DELTA, storage_mode.MODE_LFS):
            storage_mode.apply_storage_mode(str(tmp_path), mode)
            content = (tmp_path / ".gitattributes").read_text(encoding="utf-8")
            assert "-delta" not in content

    def test_never_has_both_binary_and_lfs_filter_for_fcstd(self, tmp_path):
        for mode in (
            storage_mode.MODE_DELTA,
            storage_mode.MODE_LFS,
            storage_mode.MODE_DELTA,
        ):
            storage_mode.apply_storage_mode(str(tmp_path), mode)
            content = (tmp_path / ".gitattributes").read_text(encoding="utf-8")
            fcstd_lines = [
                ln for ln in content.splitlines() if ln.strip().startswith("*.FCStd")
            ]
            assert len(fcstd_lines) == 1

    def test_unknown_mode_rejected(self, tmp_path):
        result = storage_mode.apply_storage_mode(str(tmp_path), "nonsense")
        assert not result.ok


class TestApplyStorageModeErrors:
    def test_rejects_missing_repo_root(self, tmp_path):
        result = storage_mode.apply_storage_mode(
            str(tmp_path / "does-not-exist"), storage_mode.MODE_DELTA
        )
        assert not result.ok
