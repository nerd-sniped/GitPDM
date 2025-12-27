# -*- coding: utf-8 -*-
"""
Preview staging demo (CLI)

Usage:
  python tests/preview_staging_demo.py <repo_root> <preview_rel_dir>

Example:
  python tests/preview_staging_demo.py \
    C:\path\to\repo \
    previews/cad/parts/BRK-001/BRK-001/

This uses GitClient to stage preview.png and preview.json.
If PySide is available, uses GitJobRunner (QProcess) to keep UI responsive.
"""

import sys
import os
from pathlib import Path

from freecad_gitpdm.core import log
from freecad_gitpdm.git.client import GitClient

# Optional: try job runner
try:
    from freecad_gitpdm.core.jobs import get_job_runner
except Exception:
    get_job_runner = None


def main():
    if len(sys.argv) < 3:
        print("Usage: preview_staging_demo.py <repo_root> <preview_rel_dir>")
        return 2
    repo_root = sys.argv[1]
    rel_dir = sys.argv[2]

    git = GitClient()
    if not git.is_git_available():
        print("Git not available")
        return 1

    png_rel = rel_dir + "preview.png"
    json_rel = rel_dir + "preview.json"

    # Verify files exist
    png_abs = Path(repo_root).joinpath(png_rel)
    json_abs = Path(repo_root).joinpath(json_rel)
    missing = []
    if not png_abs.is_file():
        missing.append(str(png_abs))
    if not json_abs.is_file():
        missing.append(str(json_abs))
    if missing:
        print("Missing files:\n" + "\n".join(missing))
        return 3

    print("Staging:")
    print("  ", png_rel)
    print("  ", json_rel)

    if get_job_runner:
        # Use background job runner
        jr = get_job_runner()
        git_cmd = git._get_git_command()
        args = [git_cmd, "-C", repo_root, "add", "--", png_rel, json_rel]

        def _done(job):
            res = job.get("result", {})
            ok = res.get("success", False)
            if ok:
                print("Staged via JobRunner")
            else:
                print("Staging failed:", res.get("stderr", ""))

        jr.run_job("stage_previews_cli", args, callback=_done)
        print("Job started; waiting…")
        # Minimal event loop wait if Qt available
        try:
            from PySide6 import QtCore
        except Exception:
            try:
                from PySide2 import QtCore
            except Exception:
                QtCore = None
        if QtCore:
            loop = QtCore.QEventLoop()
            # Poll runner busy state
            def _check():
                if not jr.is_busy():
                    loop.quit()
            timer = QtCore.QTimer()
            timer.timeout.connect(_check)
            timer.start(100)
            loop.exec_()
        else:
            # Simple sleep loop fallback
            import time
            for _ in range(100):
                time.sleep(0.1)
                if not jr.is_busy():
                    break
        return 0

    # Fallback: direct staging via GitClient
    res = git.stage_paths(repo_root, [png_rel, json_rel])
    if res.ok:
        print("Staged via GitClient")
        return 0
    print("Staging failed:", res.stderr)
    return 4


if __name__ == "__main__":
    sys.exit(main())
