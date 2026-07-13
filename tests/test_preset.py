# -*- coding: utf-8 -*-
"""Tests for freecad_gitpdm.export.preset (Part Glossary section only)"""

from freecad_gitpdm.export.preset import load_preset


class TestPartGlossaryDefaults:
    def test_defaults_when_no_preset_file(self, tmp_path):
        result = load_preset(tmp_path)
        assert result.preset["partGlossary"] == {
            "enabled": True,
            "onlyAssemblies": False,
            "exclude": [],
        }

    def test_sanitizes_partial_partGlossary_section(self, tmp_path):
        preset_dir = tmp_path / ".freecad-pdm"
        preset_dir.mkdir()
        (preset_dir / "preset.json").write_text(
            '{"partGlossary": {"onlyAssemblies": "yes", "exclude": ["cad/*", 5]}}',
            encoding="utf-8",
        )
        result = load_preset(tmp_path)
        pg = result.preset["partGlossary"]
        assert pg["enabled"] is True
        assert pg["onlyAssemblies"] is True
        assert pg["exclude"] == ["cad/*"]

    def test_non_list_exclude_becomes_empty_list(self, tmp_path):
        preset_dir = tmp_path / ".freecad-pdm"
        preset_dir.mkdir()
        (preset_dir / "preset.json").write_text(
            '{"partGlossary": {"exclude": "not-a-list"}}', encoding="utf-8"
        )
        result = load_preset(tmp_path)
        assert result.preset["partGlossary"]["exclude"] == []
