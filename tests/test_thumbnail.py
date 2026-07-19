# -*- coding: utf-8 -*-
"""
Tests for freecad_gitpdm.export.thumbnail.read_embedded_thumbnail.

This is now the sole source of preview thumbnails (both the local
file-browser preview and the committed, GitHub-facing preview.png written
by export/exporter.py) after deprecating GitPDM's own viewport-render
pipeline in favor of FreeCAD's own save-time embedded thumbnail.
"""

import zipfile

from freecad_gitpdm.export.thumbnail import read_embedded_thumbnail


def _make_fcstd(path, thumbnail_entry=None, thumbnail_bytes=b"fake-png-bytes"):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Document.xml", "<Document/>")
        if thumbnail_entry:
            zf.writestr(thumbnail_entry, thumbnail_bytes)


def test_reads_embedded_thumbnail(tmp_path):
    fcstd = tmp_path / "part.FCStd"
    _make_fcstd(fcstd, "Thumbnails/Thumbnail.png", b"real-thumbnail-bytes")

    result = read_embedded_thumbnail(fcstd)

    assert result == b"real-thumbnail-bytes"


def test_matches_case_insensitively(tmp_path):
    fcstd = tmp_path / "part.FCStd"
    _make_fcstd(fcstd, "thumbnails/thumbnail.PNG", b"lowercase-folder-bytes")

    result = read_embedded_thumbnail(fcstd)

    assert result == b"lowercase-folder-bytes"


def test_matches_with_backslash_separators(tmp_path):
    fcstd = tmp_path / "part.FCStd"
    _make_fcstd(fcstd, "Thumbnails\\Thumbnail.png", b"backslash-path-bytes")

    result = read_embedded_thumbnail(fcstd)

    assert result == b"backslash-path-bytes"


def test_no_thumbnail_entry_returns_none(tmp_path):
    fcstd = tmp_path / "part.FCStd"
    _make_fcstd(fcstd, thumbnail_entry=None)

    assert read_embedded_thumbnail(fcstd) is None


def test_non_png_entry_in_thumbnails_folder_is_ignored(tmp_path):
    fcstd = tmp_path / "part.FCStd"
    _make_fcstd(fcstd, "Thumbnails/readme.txt", b"not a png")

    assert read_embedded_thumbnail(fcstd) is None


def test_not_a_zip_file_returns_none(tmp_path):
    fcstd = tmp_path / "part.FCStd"
    fcstd.write_text("this is not a zip archive", encoding="utf-8")

    assert read_embedded_thumbnail(fcstd) is None


def test_missing_file_returns_none(tmp_path):
    fcstd = tmp_path / "does_not_exist.FCStd"

    assert read_embedded_thumbnail(fcstd) is None
