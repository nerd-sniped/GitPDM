# -*- coding: utf-8 -*-
"""
GitPDM Storage Mode Module (Phase G3)

Storage mode is a repo-scoped choice, persisted in
`.freecad-pdm/config.json` (mirrors the `export/preset.py` pattern for
`.freecad-pdm/preset.json`), between two mutually exclusive modes:

  - "delta" (default, free): FreeCAD compression 0, no LFS filter,
    `*.FCStd binary` in `.gitattributes`. Plain git can then delta-compress
    saves against each other.
  - "lfs" (opt-in, for teams): FreeCAD compression restored, `*.FCStd`
    tracked via the LFS filter, file locking available.

Compression=0 and Git LFS are mutually defeating (LFS stores each version
as a whole opaque object, so uncompressed files multiply LFS storage and
bandwidth for no benefit). This module is the single place that decides
the `*.FCStd` line in `.gitattributes` so the two forbidden combinations
(compression 0 + LFS, or `-delta`/LFS filter on `*.FCStd` in delta mode)
are unreachable by construction.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from freecad_gitpdm.core import log

MODE_DELTA = "delta"
MODE_LFS = "lfs"
VALID_MODES = (MODE_DELTA, MODE_LFS)
DEFAULT_MODE = MODE_DELTA

_CONFIG_REL_PATH = Path(".freecad-pdm/config.json")

_FCSTD_PATTERN = "*.FCStd"
_DELTA_ATTR_LINE = "*.FCStd binary"
_LFS_ATTR_LINE = "*.FCStd filter=lfs diff=lfs merge=lfs -text"


@dataclass
class StorageModeResult:
    ok: bool
    mode: str
    message: str = ""


def _config_path(repo_root) -> Path:
    return Path(repo_root) / _CONFIG_REL_PATH


def _gitattributes_path(repo_root) -> Path:
    return Path(repo_root) / ".gitattributes"


def load_repo_config(repo_root) -> dict:
    """Read `.freecad-pdm/config.json`; return {} if missing or malformed."""
    if not repo_root:
        return {}
    path = _config_path(repo_root)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        log.warning(f"Failed to read .freecad-pdm/config.json: {e}")
        return {}


def _write_repo_config(repo_root, data: dict) -> bool:
    path = _config_path(repo_root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return True
    except OSError as e:
        log.error(f"Failed to write .freecad-pdm/config.json: {e}")
        return False


def get_storage_mode(repo_root) -> str:
    """Read the repo's configured storage mode, defaulting to 'delta'."""
    cfg = load_repo_config(repo_root)
    mode = cfg.get("storageMode", DEFAULT_MODE)
    return mode if mode in VALID_MODES else DEFAULT_MODE


def _rewrite_fcstd_line(repo_root, mode: str) -> None:
    """
    Ensure exactly one `*.FCStd` line in `.gitattributes`, matching `mode`.

    All other lines (comments, other patterns) are preserved untouched.
    Never leaves a delta-mode and lfs-mode line coexisting, and never
    writes `-delta` for `*.FCStd`.
    """
    path = _gitattributes_path(repo_root)
    target_line = _DELTA_ATTR_LINE if mode == MODE_DELTA else _LFS_ATTR_LINE

    lines = []
    if path.is_file():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as e:
            log.error(f"Failed to read .gitattributes: {e}")
            raise

    kept = []
    for ln in lines:
        stripped = ln.strip()
        if not stripped or stripped.startswith("#"):
            kept.append(ln)
            continue
        first_token = stripped.split()[0]
        if first_token == _FCSTD_PATTERN:
            continue  # drop; replaced below with the mode-correct line
        kept.append(ln)

    kept.append(target_line)
    content = "\n".join(kept) + "\n"

    try:
        path.write_text(content, encoding="utf-8")
    except OSError as e:
        log.error(f"Failed to write .gitattributes: {e}")
        raise


def apply_storage_mode(repo_root, mode: str, git_client=None) -> StorageModeResult:
    """
    Apply `mode` to a repository: rewrite the `*.FCStd` line in
    `.gitattributes` and persist the choice in `.freecad-pdm/config.json`.

    Does not touch FreeCAD's compression preference -- that is scoped to
    the save operation itself (see `core.settings.enter_git_friendly_compression_scope`)
    rather than applied here, since this function may run with no
    FreeCAD document open (e.g. from the new-repo wizard).

    Args:
        repo_root: repository root path
        mode: "delta" or "lfs"
        git_client: optional GitClient; when given and mode is "lfs",
            runs `git lfs install` (best-effort, logged not raised)

    Returns:
        StorageModeResult
    """
    if mode not in VALID_MODES:
        return StorageModeResult(
            ok=False, mode=mode, message=f"Unknown storage mode: {mode}"
        )

    if not repo_root or not os.path.isdir(repo_root):
        return StorageModeResult(ok=False, mode=mode, message="Invalid repository root")

    try:
        _rewrite_fcstd_line(repo_root, mode)
    except OSError as e:
        return StorageModeResult(
            ok=False, mode=mode, message=f"Failed to write .gitattributes: {e}"
        )

    cfg = load_repo_config(repo_root)
    cfg["storageMode"] = mode
    if not _write_repo_config(repo_root, cfg):
        return StorageModeResult(
            ok=False, mode=mode, message="Failed to write .freecad-pdm/config.json"
        )

    if mode == MODE_LFS and git_client is not None:
        result = git_client.lfs_install()
        if not result.ok:
            log.warning(f"git lfs install reported an issue: {result.stderr}")

    log.info(f"Storage mode set to '{mode}' for repo: {repo_root}")
    return StorageModeResult(ok=True, mode=mode)


def describe_mode(mode: str) -> str:
    """One-line, user-facing description of a mode, for UI display."""
    if mode == MODE_LFS:
        return "LFS (opt-in): file locking, metered storage past 1 GiB"
    return "Delta (default): free, unmetered, no file locking"
