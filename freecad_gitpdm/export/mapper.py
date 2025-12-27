# -*- coding: utf-8 -*-
"""
Path mapper for preview outputs.

Mirror-the-source-path convention:
For repo-relative source path: <rel_dir>/<name>.FCStd
Output directory: previews/<rel_dir>/<name>/
"""

from pathlib import Path
from typing import Tuple


def to_preview_dir_rel(source_rel: str) -> str:
    """
    Map source repo-relative path to preview dir repo-relative path.

    Example:
      source:  cad/parts/BRK-001/BRK-001.FCStd
      output:  previews/cad/parts/BRK-001/BRK-001/
    """
    p = Path(source_rel)
    name = p.stem
    rel_dir = p.parent.as_posix()
    # Construct preview dir using POSIX-style separators
    if rel_dir:
        preview_dir = Path("previews") / rel_dir / name
    else:
        preview_dir = Path("previews") / name
    return preview_dir.as_posix() + "/"


def preview_paths_rel(source_rel: str) -> Tuple[str, str]:
    """Return (png_rel, json_rel) under preview dir."""
    base = to_preview_dir_rel(source_rel)
    png_rel = base + "preview.png"
    json_rel = base + "preview.json"
    return (png_rel, json_rel)
