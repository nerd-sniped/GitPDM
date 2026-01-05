"""
GitPDM Repository Scaffolding
Sprint OAUTH-4: Create CAD-friendly folder structure and config files

Creates:
  - cad/ (for FreeCAD models)
  - previews/ (for rendered thumbnails)
  - .freecad-pdm/preset.json (export configuration)
  - .gitattributes (optional, for Git LFS tracking)
"""

import os
import json
from typing import List, Optional
from pathlib import Path

from freecad.gitpdm.core import log


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
}

# Recommended .gitattributes for LFS
_LFS_GITATTRIBUTES = """\
# Git LFS (Large File Storage) configuration for CAD and asset files
*.FCStd filter=lfs diff=lfs merge=lfs -text
*.glb filter=lfs diff=lfs merge=lfs -text
"""


def apply_scaffold(
    repo_root: str,
    enable_lfs: bool = True,
    write_preset: bool = True,
) -> List[str]:
    """
    Create CAD-friendly scaffolding in a repository.

    Creates:
      - cad/ directory
      - previews/ directory
      - .freecad-pdm/ directory
      - .freecad-pdm/preset.json (if write_preset)
      - .gitattributes (if enable_lfs)

    Args:
        repo_root: Repository root path (must exist)
        enable_lfs: If True, create .gitattributes with LFS config
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

    # Write .gitattributes for LFS
    if enable_lfs:
        gitattr_path = os.path.join(repo_root, ".gitattributes")
        try:
            if os.path.exists(gitattr_path):
                # Append if file exists and doesn't already have LFS entries
                with open(gitattr_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "*.FCStd filter=lfs" not in content:
                    with open(gitattr_path, "a", encoding="utf-8") as f:
                        f.write("\n" + _LFS_GITATTRIBUTES)
                    log.info("Updated .gitattributes with LFS config")
                    created.append(".gitattributes")
                else:
                    log.debug(".gitattributes already has LFS entries")
            else:
                with open(gitattr_path, "w", encoding="utf-8") as f:
                    f.write(_LFS_GITATTRIBUTES)
                log.info("Created .gitattributes with LFS config")
                created.append(".gitattributes")
        except OSError as e:
            log.error(f"Failed to write .gitattributes: {e}")
            raise

    log.info(f"Scaffold applied successfully: {len(created)} items created/updated")
    return created
