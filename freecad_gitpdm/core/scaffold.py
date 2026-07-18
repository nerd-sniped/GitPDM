# -*- coding: utf-8 -*-
"""
GitPDM Repository Scaffolding
Sprint OAUTH-4: Create CAD-friendly folder structure and config files
Phase G3: storage mode (delta/lfs) now drives .gitattributes + config.json

Creates:
  - cad/ (for FreeCAD models)
  - previews/ (for rendered thumbnails)
  - .freecad-pdm/preset.json (export configuration)
  - .freecad-pdm/config.json + .gitattributes (storage mode; see core/storage_mode.py)
"""

import os
import json
from typing import List
from pathlib import Path

from freecad_gitpdm.core import log, storage_mode


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


def apply_scaffold(
    repo_root: str,
    mode: str = storage_mode.DEFAULT_MODE,
    write_preset: bool = True,
) -> List[str]:
    """
    Create CAD-friendly scaffolding in a repository.

    Creates:
      - cad/ directory
      - previews/ directory
      - .freecad-pdm/ directory
      - .freecad-pdm/preset.json (if write_preset)
      - .freecad-pdm/config.json + .gitattributes (storage mode: "delta" or
        "lfs" -- see core/storage_mode.py for what each writes)

    Args:
        repo_root: Repository root path (must exist)
        mode: "delta" (default, free) or "lfs" (opt-in, for teams)
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

    # Write .gitattributes + .freecad-pdm/config.json for the storage mode
    result = storage_mode.apply_storage_mode(repo_root, mode)
    if result.ok:
        log.info(f"Applied storage mode '{mode}' (.gitattributes, config.json)")
        created.append(".gitattributes")
        created.append(".freecad-pdm/config.json")
    else:
        log.error(f"Failed to apply storage mode '{mode}': {result.message}")
        raise OSError(result.message)

    log.info(f"Scaffold applied successfully: {len(created)} items created/updated")
    return created
