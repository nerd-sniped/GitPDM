"""
Path helpers for GitPDM.

Safe joins and repo-relative conversions using pathlib.
"""

import os
from pathlib import Path
from typing import Optional
from freecad.gitpdm.core import log


def normalize(path: str) -> str:
    return os.path.normpath(path or "")


def is_inside_repo(abs_path: str, repo_root: str) -> bool:
    try:
        if not abs_path or not repo_root:
            return False
        ap = Path(abs_path).resolve()
        rr = Path(repo_root).resolve()
        return rr in ap.parents or ap == rr
    except Exception:
        return False


def to_repo_rel(abs_path: str, repo_root: str) -> Optional[str]:
    try:
        ap = Path(abs_path).resolve()
        rr = Path(repo_root).resolve()
        rel = ap.relative_to(rr)
        # Use POSIX-style separators for git-friendly paths
        return rel.as_posix()
    except Exception as e:
        log.warning(f"to_repo_rel failed: {e}")
        return None


def safe_join_repo(repo_root: str, rel_path: str) -> Optional[Path]:
    try:
        rr = Path(repo_root).resolve()
        joined = (rr / rel_path).resolve()
        if rr not in joined.parents and joined != rr:
            # Prevent path escape
            return None
        return joined
    except Exception as e:
        log.warning(f"safe_join_repo failed: {e}")
        return None
