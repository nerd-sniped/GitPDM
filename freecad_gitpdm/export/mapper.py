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
    # Extract part name from source path for consistent naming
    p = Path(source_rel)
    part_name = p.stem
    png_rel = base + f"{part_name}.png"
    json_rel = base + f"{part_name}.json"
    return (png_rel, json_rel)


def stl_root_path_rel(source_rel: str) -> str:
    """
    Return the STL file path at the previews root (not in part subfolder).

    Example:
      source:  cad/parts/BRK-001/BRK-001.FCStd
      output:  previews/BRK-001.stl

    The STL uses just the part name without the directory structure.
    """
    p = Path(source_rel)
    name = p.stem
    stl_path = Path("previews") / f"{name}.stl"
    return stl_path.as_posix()
