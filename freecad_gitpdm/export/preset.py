# -*- coding: utf-8 -*-
"""
Preset loader for GitPDM preview export (v1)

Reads .freecad-pdm/preset.json from the repository root.
Provides safe defaults and clamps values to reasonable bounds.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from pathlib import Path
from freecad_gitpdm.core import log


_PRESET_REL_PATH = Path(".freecad-pdm/preset.json")

# Bounds for thumbnail size
_MIN_THUMB = 128
_MAX_THUMB = 2048


_DEFAULT_PRESET: Dict[str, Any] = {
    "presetVersion": 1,
    "thumbnail": {
        "size": [512, 512],
        "projection": "orthographic",
        "view": "isometric",
        "background": "transparent",
        "showEdges": False,
    },
    "stats": {"precision": 2},
    "mesh": {
        "linearDeflection": 0.1,
        "angularDeflectionDeg": 15,
        "relative": False,
    },
}


@dataclass
class PresetResult:
    preset: Dict[str, Any]
    from_file: bool
    error: Optional[str]


def _clamp_size(size: Any) -> Tuple[int, int]:
    try:
        if not isinstance(size, (list, tuple)):
            return (512, 512)
        w = int(size[0])
        h = int(size[1])
    except Exception:
        return (512, 512)
    w = max(_MIN_THUMB, min(_MAX_THUMB, w))
    h = max(_MIN_THUMB, min(_MAX_THUMB, h))
    return (w, h)


def _sanitize_preset(data: Dict[str, Any]) -> Dict[str, Any]:
    # Start from defaults and overwrite known keys
    result = json.loads(json.dumps(_DEFAULT_PRESET))

    # Version (fixed at 1 for now)
    try:
        ver = int(data.get("presetVersion", 1))
        result["presetVersion"] = 1 if ver != 1 else ver
    except Exception:
        result["presetVersion"] = 1

    # Thumbnail section
    t_in = data.get("thumbnail", {}) or {}
    t_out = result["thumbnail"]
    size = _clamp_size(t_in.get("size", t_out.get("size")))
    t_out["size"] = [size[0], size[1]]

    proj = str(t_in.get("projection", t_out.get("projection", "orthographic"))).lower()
    if proj not in ("orthographic", "perspective"):
        proj = "orthographic"
    t_out["projection"] = proj

    view = str(t_in.get("view", t_out.get("view", "isometric"))).lower()
    if view not in ("isometric", "front", "top", "right"):
        view = "isometric"
    t_out["view"] = view

    bg = str(t_in.get("background", t_out.get("background", "transparent"))).strip().lower()
    # Allow transparent, hex colors, or none
    if bg in ("transparent", "none", ""):
        bg = "transparent"
    elif not bg.startswith("#") or len(bg) not in (4, 7):
        bg = "transparent"
    t_out["background"] = bg

    show_edges = bool(t_in.get("showEdges", t_out.get("showEdges", False)))
    t_out["showEdges"] = show_edges

    # Determinism: always use configured view (no useCurrentView flag)

    # Stats
    s_in = data.get("stats", {}) or {}
    s_out = result["stats"]
    try:
        prec = int(s_in.get("precision", s_out.get("precision", 2)))
    except Exception:
        prec = 2
    prec = max(0, min(6, prec))
    s_out["precision"] = prec

    # Mesh settings (Sprint 7)
    m_in = data.get("mesh", {}) or {}
    m_out = result["mesh"]
    try:
        lin_def = float(m_in.get(
            "linearDeflection", m_out["linearDeflection"]
        ))
    except Exception:
        lin_def = 0.1
    lin_def = max(0.001, min(10.0, lin_def))
    m_out["linearDeflection"] = lin_def

    try:
        ang_def = float(m_in.get(
            "angularDeflectionDeg", m_out["angularDeflectionDeg"]
        ))
    except Exception:
        ang_def = 15
    ang_def = max(1, min(90, ang_def))
    m_out["angularDeflectionDeg"] = ang_def

    rel = bool(m_in.get("relative", m_out["relative"]))
    m_out["relative"] = rel

    return result


def load_preset(repo_root: Path) -> PresetResult:
    """
    Load preset JSON from repo.
    If missing or malformed, return defaults and an error message.
    """
    try:
        if not repo_root:
            raise ValueError("Missing repo_root")
        preset_path = (repo_root / _PRESET_REL_PATH).resolve()
        if not preset_path.is_file():
            log.info("Preset file missing; using defaults")
            return PresetResult(
                preset=json.loads(json.dumps(_DEFAULT_PRESET)),
                from_file=False,
                error=None,
            )
        try:
            raw = preset_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception as e:
            log.warning(f"Preset parse failed: {e}")
            return PresetResult(
                preset=json.loads(json.dumps(_DEFAULT_PRESET)),
                from_file=True,
                error="Preset parse failure; using defaults",
            )
        sanitized = _sanitize_preset(data)
        return PresetResult(
            preset=sanitized,
            from_file=True,
            error=None,
        )
    except Exception as e:
        log.warning(f"Preset load error: {e}")
        return PresetResult(
            preset=json.loads(json.dumps(_DEFAULT_PRESET)),
            from_file=False,
            error="Preset load error; using defaults",
        )
