# -*- coding: utf-8 -*-
"""
Thumbnail reading for GitPDM previews.

GitPDM used to render its own thumbnail on every save (zoom-to-fit +
viewport screenshot, run synchronously on the main thread), which blocked
FreeCAD's UI and duplicated a snapshot FreeCAD already takes itself at save
time. That custom render path is gone; the exported, committed preview.png
(export/exporter.py) reads the same embedded thumbnail below. (The
in-app "Repository Browser" dock that used to also read this for a local
click-to-preview was removed entirely -- redundant with the OS's own file
explorer, which already shows this exact embedded thumbnail.)
"""

import zipfile
from pathlib import Path
from typing import Optional


def read_embedded_thumbnail(fcstd_path: Path) -> Optional[bytes]:
    """
    Read the thumbnail FreeCAD embeds in a .FCStd file at save time (when
    "Create new thumbnail when saving the document" is enabled in FreeCAD's
    preferences -- the default).

    .FCStd files are plain zip archives; the embedded thumbnail lives as a
    PNG under a "thumbnails/" folder inside. Matched case-insensitively by
    folder+extension rather than one hardcoded path, since exact casing has
    varied across FreeCAD versions and this needs to keep working without a
    matching release-by-release update.

    Returns the PNG bytes, or None if the file isn't a valid zip or has no
    embedded thumbnail (e.g. the preference was off when it was last saved).
    """
    try:
        with zipfile.ZipFile(fcstd_path) as zf:
            for name in zf.namelist():
                parts = name.replace("\\", "/").split("/")
                if len(parts) < 2:
                    continue
                if parts[-2].lower() != "thumbnails":
                    continue
                if not parts[-1].lower().endswith(".png"):
                    continue
                return zf.read(name)
    except (zipfile.BadZipFile, OSError, KeyError):
        return None
    return None
