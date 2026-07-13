# -*- coding: utf-8 -*-
"""Tests for freecad_gitpdm.export.glossary"""

import json
from types import SimpleNamespace

from freecad_gitpdm.export import glossary


def _obj(type_id):
    return SimpleNamespace(TypeId=type_id)


class TestDetectCategory:
    def test_single_body_is_part(self):
        doc = SimpleNamespace(Objects=[_obj("PartDesign::Body")])
        assert glossary.detect_category(doc) == "part"

    def test_multiple_bodies_is_assembly(self):
        doc = SimpleNamespace(
            Objects=[_obj("PartDesign::Body"), _obj("PartDesign::Body")]
        )
        assert glossary.detect_category(doc) == "assembly"

    def test_app_link_is_assembly(self):
        doc = SimpleNamespace(Objects=[_obj("App::Link")])
        assert glossary.detect_category(doc) == "assembly"

    def test_assembly_workbench_type_is_assembly(self):
        doc = SimpleNamespace(Objects=[_obj("Assembly::AssemblyObject")])
        assert glossary.detect_category(doc) == "assembly"

    def test_broken_doc_defaults_to_part(self):
        doc = SimpleNamespace()  # no .Objects
        assert glossary.detect_category(doc) == "part"


def _write_manifest(
    previews_dir,
    rel_dir,
    part_name,
    source_rel,
    category="part",
    bbox=None,
    artifacts=None,
):
    out_dir = previews_dir / rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{part_name}.png").write_bytes(b"fake-png")
    if artifacts is None:
        artifacts = {
            "model": f"previews/{rel_dir}/{part_name}.obj",
            "stl": f"previews/{part_name}.stl",
        }
    manifest = {
        "source": {"path": source_rel},
        "artifacts": artifacts,
        "stats": {"bboxMm": bbox or [10.0, 20.0, 30.0]},
        "category": category,
    }
    (out_dir / f"{part_name}.json").write_text(json.dumps(manifest), encoding="utf-8")


class TestCollectEntries:
    def test_no_previews_dir_returns_empty(self, tmp_path):
        assert glossary.collect_entries(tmp_path, {}) == []

    def test_collects_and_sorts_entries(self, tmp_path):
        previews = tmp_path / "previews"
        _write_manifest(previews, "cad/b", "B", "cad/b/B.FCStd")
        _write_manifest(previews, "cad/a", "A", "cad/a/A.FCStd")
        entries = glossary.collect_entries(tmp_path, {})
        assert [e["source_rel"] for e in entries] == ["cad/a/A.FCStd", "cad/b/B.FCStd"]
        assert entries[0]["png_rel"] == "previews/cad/a/A.png"

    def test_exclude_glob_filters_entries(self, tmp_path):
        previews = tmp_path / "previews"
        _write_manifest(previews, "cad/fasteners", "Bolt", "cad/fasteners/Bolt.FCStd")
        _write_manifest(previews, "cad/parts", "Bracket", "cad/parts/Bracket.FCStd")
        entries = glossary.collect_entries(tmp_path, {"exclude": ["cad/fasteners/*"]})
        assert [e["name"] for e in entries] == ["Bracket"]

    def test_only_assemblies_filters_by_category(self, tmp_path):
        previews = tmp_path / "previews"
        _write_manifest(previews, "cad/a", "A", "cad/a/A.FCStd", category="part")
        _write_manifest(previews, "cad/b", "B", "cad/b/B.FCStd", category="assembly")
        entries = glossary.collect_entries(tmp_path, {"onlyAssemblies": True})
        assert [e["name"] for e in entries] == ["B"]

    def test_malformed_manifest_is_skipped(self, tmp_path):
        previews = tmp_path / "previews"
        previews.mkdir()
        (previews / "bad.json").write_text("not json", encoding="utf-8")
        assert glossary.collect_entries(tmp_path, {}) == []

    def test_link_prefers_stl_over_model(self, tmp_path):
        previews = tmp_path / "previews"
        _write_manifest(previews, "cad/a", "A", "cad/a/A.FCStd")
        entries = glossary.collect_entries(tmp_path, {})
        assert entries[0]["link_rel"] == "previews/A.stl"

    def test_link_falls_back_to_model_without_stl(self, tmp_path):
        previews = tmp_path / "previews"
        _write_manifest(
            previews,
            "cad/a",
            "A",
            "cad/a/A.FCStd",
            artifacts={"model": "previews/cad/a/A.obj"},
        )
        entries = glossary.collect_entries(tmp_path, {})
        assert entries[0]["link_rel"] == "previews/cad/a/A.obj"


class TestRenderSection:
    def test_empty_state(self):
        section = glossary.render_section([])
        assert glossary.START_MARKER in section
        assert glossary.END_MARKER in section
        assert "No parts exported yet" in section

    def test_renders_table_row(self):
        entries = [
            {
                "name": "Bracket",
                "source_rel": "cad/Bracket.FCStd",
                "category": "part",
                "png_rel": "previews/Bracket.png",
                "link_rel": "previews/Bracket.stl",
                "bbox": "10.0 x 20.0 x 30.0",
            }
        ]
        section = glossary.render_section(entries)
        assert "Bracket" in section
        assert "cad/Bracket.FCStd" in section
        assert "[![Bracket](previews/Bracket.png)](previews/Bracket.stl)" in section
        assert "[Bracket](previews/Bracket.stl)" in section

    def test_renders_thumbnail_without_link_when_no_model(self):
        entries = [
            {
                "name": "Bracket",
                "source_rel": "cad/Bracket.FCStd",
                "category": "part",
                "png_rel": "previews/Bracket.png",
                "link_rel": None,
                "bbox": "10.0 x 20.0 x 30.0",
            }
        ]
        section = glossary.render_section(entries)
        assert "![Bracket](previews/Bracket.png)" in section
        assert "[![Bracket]" not in section


class TestUpdateReadme:
    def test_creates_readme_if_missing(self, tmp_path):
        section = glossary.render_section([])
        readme_path = glossary.update_readme(tmp_path, section)
        assert readme_path == tmp_path / "README.md"
        content = readme_path.read_text(encoding="utf-8")
        assert glossary.START_MARKER in content
        assert content.startswith(f"# {tmp_path.name}")

    def test_replaces_existing_section(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text(
            f"# My Project\n\nIntro text.\n\n{glossary.START_MARKER}\nold\n"
            f"{glossary.END_MARKER}\n\nFooter text.\n",
            encoding="utf-8",
        )
        new_section = glossary.render_section([])
        glossary.update_readme(tmp_path, new_section)
        content = readme.read_text(encoding="utf-8")
        assert "old" not in content
        assert "Intro text." in content
        assert "Footer text." in content
        assert "No parts exported yet" in content

    def test_appends_section_to_existing_readme_without_markers(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# My Project\n\nHand-written docs.\n", encoding="utf-8")
        section = glossary.render_section([])
        glossary.update_readme(tmp_path, section)
        content = readme.read_text(encoding="utf-8")
        assert "Hand-written docs." in content
        assert glossary.START_MARKER in content

    def test_respects_alternate_readme_casing(self, tmp_path):
        readme = tmp_path / "readme.md"
        readme.write_text("# lowercase readme\n", encoding="utf-8")
        section = glossary.render_section([])
        result_path = glossary.update_readme(tmp_path, section)
        assert result_path == readme
        assert list(tmp_path.glob("*.md")) == [readme]


class TestRegenerate:
    def test_disabled_returns_none_and_does_not_touch_readme(self, tmp_path):
        result = glossary.regenerate(tmp_path, {"partGlossary": {"enabled": False}})
        assert result is None
        assert not (tmp_path / "README.md").exists()

    def test_enabled_writes_readme(self, tmp_path):
        previews = tmp_path / "previews"
        _write_manifest(previews, "cad/a", "A", "cad/a/A.FCStd")
        result = glossary.regenerate(tmp_path, {"partGlossary": {"enabled": True}})
        assert result == tmp_path / "README.md"
        content = result.read_text(encoding="utf-8")
        assert "cad/a/A.FCStd" in content

    def test_defaults_to_enabled_when_key_missing(self, tmp_path):
        result = glossary.regenerate(tmp_path, {})
        assert result == tmp_path / "README.md"
