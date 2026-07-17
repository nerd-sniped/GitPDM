# -*- coding: utf-8 -*-
"""
GitPDM storage-mode benchmark (Phase G3).

Saves a synthetic document 10x with a small change per save, once in each
storage mode ("delta" and "lfs"), and prints the repo's `git
count-objects` growth after every save, then the final packed size after
`git gc`. This is meant as practical, runnable evidence to go with R1.1
(why delta mode is expected to keep history smaller) and R1.4 (why the
gains are real but uneven) -- not a guarantee, per the caveat below.

Usage:
    python tools/storage_mode_benchmark.py

Caveat -- this is an approximation, not a real .FCStd/LFS round trip:
FreeCAD isn't pip-installable, so this script cannot drive real
App.Document saves outside the FreeCAD process. Instead it zips a
synthetic ~160 KB XML-like payload (standing in for Document.xml; real
BREP geometry data is not modeled at all) with ZIP_STORED for delta mode
(mirrors FreeCAD's compression=0) and ZIP_DEFLATED for lfs mode (mirrors
FreeCAD's restored default compression=3), mutating one element's
numeric values per save the way a small parametric edit would.

Empirically, this synthetic proxy does NOT reliably reproduce R1.1's
"deflate cascade" story at the small scale a quick local run uses --
generic zlib deflate over this kind of content still lets git's delta
compression find similarity across versions more often than not, so
this script's own printed numbers may show either mode "winning". Real
.FCStd files differ in exactly the ways R1.4 flags: genuine BREP binary
data, topological-naming churn on parametric edits, and file sizes much
larger than this toy example, all of which make the effect more
pronounced in practice than in this simulation. Treat this script's
output as a worked example of the *measurement technique* -- run it
against a real project via FreeCAD's CLI (e.g. `freecadcmd`, driving
actual `App.Document.save()` calls with `CompressionLevel` set per mode)
for a trustworthy verdict on that project's files.
"""

from __future__ import annotations

import random
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from freecad_gitpdm.core import storage_mode

SAVES_PER_MODE = 10
_RANDOM_SEED = 20260717
_ELEMENT_COUNT = 2500


def _run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _run_git(repo, "init", "-q")
    _run_git(repo, "config", "user.email", "benchmark@example.invalid")
    _run_git(repo, "config", "user.name", "GitPDM Benchmark")


def _make_lines(rng: random.Random) -> list:
    """
    Deterministic stand-in for a small model's Document.xml: repeated tag
    structure (compressible, like real XML) wrapped around per-element
    numeric literals (high enough entropy that a value can change length,
    like a real dimension edit) -- real BREP binary data is not modeled.
    """
    lines = []
    for i in range(_ELEMENT_COUNT):
        x, y, z = (rng.uniform(-500, 500) for _ in range(3))
        lines.append(f'<Vertex id="{i}" x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>')
    return lines


def _mutate(rng: random.Random, lines: list) -> None:
    """Simulate 'a small dimension change': rewrite one element's values."""
    idx = rng.randrange(len(lines))
    x, y, z = (rng.uniform(-500, 500) for _ in range(3))
    lines[idx] = f'<Vertex id="{idx}" x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>'


def _write_fake_fcstd(path: Path, payload: bytes, compress: bool) -> None:
    """
    Zip `payload` as a single member, the way .FCStd zips Document.xml.
    Stored (compress=False) approximates compression=0; deflated
    (compress=True) approximates FreeCAD's default compression=3.
    """
    mode = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    with zipfile.ZipFile(path, "w", compression=mode) as zf:
        zf.writestr("Document.xml", payload)


def _loose_size_kib(repo: Path) -> str:
    out = _run_git(repo, "count-objects", "-v")
    stats = dict(line.split(": ") for line in out.strip().splitlines())
    return stats.get("size", "?")


def _bench_mode(mode: str, base_dir: Path) -> str:
    repo = base_dir / mode
    _init_repo(repo)
    storage_mode.apply_storage_mode(str(repo), mode)
    _run_git(repo, "add", "-A")
    _run_git(repo, "commit", "-q", "-m", "Initial scaffold")

    rng = random.Random(_RANDOM_SEED)
    lines = _make_lines(rng)
    fcstd_path = repo / "model.FCStd"

    # lfs mode restores FreeCAD's normal (deflate) compression; delta mode
    # keeps entries stored/uncompressed -- see module docstring.
    compress = mode == storage_mode.MODE_LFS

    print(f"\n=== {mode} mode ({SAVES_PER_MODE} saves) ===")
    print("save  loose-objects-size(KiB)")
    for i in range(SAVES_PER_MODE):
        _mutate(rng, lines)
        payload = ("\n".join(lines)).encode("utf-8")
        _write_fake_fcstd(fcstd_path, payload, compress=compress)
        _run_git(repo, "add", "-A")
        _run_git(repo, "commit", "-q", "-m", f"Save {i + 1}")
        print(f"{i + 1:>4}  {_loose_size_kib(repo)}")

    _run_git(repo, "gc", "-q")
    packed = _run_git(repo, "count-objects", "-vH")
    print(f"\nAfter 'git gc' ({mode} mode):")
    print(packed)
    for line in packed.splitlines():
        if line.startswith("size-pack:"):
            return line.split(":", 1)[1].strip()
    return "?"


def main() -> int:
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except Exception:
        print("git is required on PATH to run this benchmark")
        return 1

    try:
        import FreeCAD  # noqa: F401

        print(
            "Note: FreeCAD is importable, but this script still uses the "
            "synthetic zip approximation described in its module docstring "
            "for both modes (it does not yet drive real App.Document saves)."
        )
    except ImportError:
        print(
            "FreeCAD not available -- using the synthetic zip approximation "
            "described in this script's module docstring, not a real .FCStd "
            "save. See that docstring for what this can and cannot prove."
        )

    packed_sizes = {}
    with tempfile.TemporaryDirectory(prefix="gitpdm-storage-bench-") as tmp:
        base_dir = Path(tmp)
        for mode in (storage_mode.MODE_DELTA, storage_mode.MODE_LFS):
            packed_sizes[mode] = _bench_mode(mode, base_dir)

    print("\n=== Summary (packed size after git gc) ===")
    for mode, size in packed_sizes.items():
        print(f"{mode}: {size}")
    print(
        "\nSee the module docstring's caveat before drawing conclusions from "
        "this synthetic run -- rerun via FreeCAD's CLI against a real "
        "project for a trustworthy comparison."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
