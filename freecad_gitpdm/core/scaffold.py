# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
GitPDM Repository Scaffolding
Sprint OAUTH-4: Create CAD-friendly folder structure and config files

Creates:
  - cad/ (for FreeCAD models)
  - previews/ (for rendered thumbnails)
  - .freecad-pdm/preset.json (export configuration)
  - .gitattributes (marks *.FCStd as binary so git never tries to text-diff it)
"""

import os
import json
from typing import List
from pathlib import Path

from freecad_gitpdm.core import log


# Default preset (same structure as in export/preset.py)
_DEFAULT_PRESET = {
    "presetVersion": 1,
    "thumbnail": {
        "size": [512, 512],
        "projection": "orthographic",
        "view": "isometric",
        "background": "#ffffff",
        "showEdges": False,
    },
    "stats": {"precision": 2},
    "mesh": {
        "linearDeflection": 0.1,
        "angularDeflectionDeg": 15,
        "relative": False,
    },
    "partGlossary": {
        "enabled": True,
        "onlyAssemblies": False,
        "exclude": [],
    },
}


_FCSTD_PATTERN = "*.FCStd"
_FCSTD_ATTR_LINE = "*.FCStd binary"


def _ensure_fcstd_gitattributes_line(repo_root: str) -> None:
    """
    Ensure exactly one `*.FCStd` line in `.gitattributes`, marking it
    binary so git never tries to text-diff a `.FCStd` ZIP archive. All
    other lines (comments, other patterns) are preserved untouched; safe to
    call on an already-scaffolded repo without duplicating the line.
    """
    path = Path(repo_root) / ".gitattributes"

    lines = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()

    kept = []
    for ln in lines:
        stripped = ln.strip()
        if not stripped or stripped.startswith("#"):
            kept.append(ln)
            continue
        if stripped.split()[0] == _FCSTD_PATTERN:
            continue  # drop; replaced below
        kept.append(ln)

    kept.append(_FCSTD_ATTR_LINE)
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def apply_scaffold(
    repo_root: str,
    write_preset: bool = True,
) -> List[str]:
    """
    Create CAD-friendly scaffolding in a repository.

    Creates:
      - cad/ directory
      - previews/ directory
      - .freecad-pdm/ directory
      - .freecad-pdm/preset.json (if write_preset)
      - .gitattributes (marks *.FCStd as binary)

    Args:
        repo_root: Repository root path (must exist)
        write_preset: If True, create .freecad-pdm/preset.json

    Returns:
        List of relative paths created/modified (for logging/staging)

    Raises:
        OSError: If directory creation or file writing fails
    """
    if not repo_root or not os.path.isdir(repo_root):
        raise OSError(f"Invalid repository root: {repo_root}")

    created = []

    # Create directories
    for dirname in ["cad", "previews", ".freecad-pdm"]:
        dirpath = os.path.join(repo_root, dirname)
        if not os.path.exists(dirpath):
            try:
                os.makedirs(dirpath, exist_ok=True)
                log.info(f"Created directory: {dirname}/")
                created.append(dirname)
            except OSError as e:
                log.error(f"Failed to create {dirname}: {e}")
                raise

    # Write .freecad-pdm/preset.json
    if write_preset:
        preset_path = os.path.join(repo_root, ".freecad-pdm", "preset.json")
        try:
            if not os.path.exists(preset_path):
                with open(preset_path, "w", encoding="utf-8") as f:
                    json.dump(_DEFAULT_PRESET, f, indent=2)
                log.info("Created .freecad-pdm/preset.json")
                created.append(".freecad-pdm/preset.json")
            else:
                log.debug(".freecad-pdm/preset.json already exists, skipping")
        except OSError as e:
            log.error(f"Failed to write preset.json: {e}")
            raise

    # Write .gitattributes (*.FCStd binary)
    try:
        _ensure_fcstd_gitattributes_line(repo_root)
        log.info("Applied .gitattributes (*.FCStd binary)")
        created.append(".gitattributes")
    except OSError as e:
        log.error(f"Failed to write .gitattributes: {e}")
        raise

    log.info(f"Scaffold applied successfully: {len(created)} items created/updated")
    return created
