# -*- coding: utf-8 -*-
"""
Preview manifest JSON generation for GitPDM.

Creates deterministic JSON manifests with metadata about exported parts
including source information, export settings, statistics, and artifacts.
"""

import hashlib
from pathlib import Path
from typing import Optional
from freecad_gitpdm.core import log


def freecad_version_string() -> str:
    """Get FreeCAD version as a string."""
    try:
        import FreeCAD

        v = getattr(FreeCAD, "Version", None)
        if callable(v):
            ver = v()
            # FreeCAD.Version() may return a tuple or dict-like
            try:
                return str(ver)
            except Exception:
                pass
        return f"{getattr(FreeCAD, 'Version', 'unknown')}"
    except Exception:
        return "unknown"


def sha256_file(path: Path) -> Optional[str]:
    """Compute SHA256 hash of a file."""
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        log.warning(f"SHA256 failed: {e}")
        return None
