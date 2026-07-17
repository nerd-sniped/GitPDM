# -*- coding: utf-8 -*-
"""
Tests for core/provider_config.py — per-repo provider selection (Phase G4).
"""

import json
import os

import pytest

from freecad_gitpdm.core import provider_config


class TestDefaults:
    def test_missing_config_defaults_to_github(self, tmp_path):
        assert provider_config.get_provider_id(str(tmp_path)) == "github"

    def test_malformed_json_defaults_to_github(self, tmp_path):
        config_dir = tmp_path / ".freecad-pdm"
        config_dir.mkdir()
        (config_dir / "config.json").write_text("{not valid json", encoding="utf-8")
        assert provider_config.get_provider_id(str(tmp_path)) == "github"

    def test_unknown_provider_id_defaults_to_github(self, tmp_path):
        config_dir = tmp_path / ".freecad-pdm"
        config_dir.mkdir()
        (config_dir / "config.json").write_text(
            json.dumps({"provider": "bitbucket"}), encoding="utf-8"
        )
        assert provider_config.get_provider_id(str(tmp_path)) == "github"

    def test_missing_config_no_remote_host(self, tmp_path):
        assert provider_config.get_remote_host(str(tmp_path)) is None


class TestSetProviderConfig:
    def test_writes_provider_field(self, tmp_path):
        provider_config.set_provider_config(str(tmp_path), "generic")
        assert provider_config.get_provider_id(str(tmp_path)) == "generic"

    def test_writes_remote_host(self, tmp_path):
        provider_config.set_provider_config(
            str(tmp_path), "github", remote_host="github.example.com"
        )
        assert provider_config.get_remote_host(str(tmp_path)) == "github.example.com"

    def test_switching_provider_clears_stale_remote_host(self, tmp_path):
        provider_config.set_provider_config(
            str(tmp_path), "github", remote_host="github.example.com"
        )
        provider_config.set_provider_config(str(tmp_path), "generic")
        assert provider_config.get_remote_host(str(tmp_path)) is None

    def test_preserves_other_config_keys(self, tmp_path):
        config_dir = tmp_path / ".freecad-pdm"
        config_dir.mkdir()
        (config_dir / "config.json").write_text(
            json.dumps({"storageMode": "delta"}), encoding="utf-8"
        )

        provider_config.set_provider_config(str(tmp_path), "generic")

        data = json.loads((config_dir / "config.json").read_text(encoding="utf-8"))
        assert data["storageMode"] == "delta"
        assert data["provider"] == "generic"

    def test_rejects_unknown_provider_id(self, tmp_path):
        with pytest.raises(ValueError):
            provider_config.set_provider_config(str(tmp_path), "bitbucket")

    def test_creates_config_dir_if_missing(self, tmp_path):
        provider_config.set_provider_config(str(tmp_path), "gitlab")
        assert os.path.isdir(str(tmp_path / ".freecad-pdm"))
