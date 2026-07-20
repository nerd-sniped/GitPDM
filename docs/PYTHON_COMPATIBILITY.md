# Python Version Compatibility

## Supported Python Versions

GitPDM supports **Python 3.11+**:

- **Python 3.11** - minimum; matches what FreeCAD 0.21+ (including 1.0)
  bundles in its official Windows/macOS/AppImage builds
- **Python 3.12** - latest FreeCAD builds

Python 3.10 support was dropped 2026-07-20: no official FreeCAD release
still bundles it, so supporting it bought no real-world compatibility,
only extra CI matrix surface (see `CLAUDE.md`'s CI section for the actual
bug that surfaced from testing it).

## Design Decisions

### Why Python 3.11+?
FreeCAD bundles its own Python interpreter, and different FreeCAD versions
ship with different Python versions. GitPDM targets the oldest Python
version any currently-official FreeCAD build still ships, so its own
minimum tracks FreeCAD's rather than an arbitrary older floor.

### Modern Syntax Support
The codebase uses `from __future__ import annotations`, so union-type
syntax (`str | None` instead of `Optional[str]`) is available even though
it isn't required at this Python floor.

## Testing

The CI/CD pipeline (`.github/workflows/ci.yml`) tests against 3.11 and
3.12 on:
- Linux (Ubuntu)
- Windows
- macOS

## Installation

### Within FreeCAD
GitPDM automatically uses FreeCAD's bundled Python (no installation needed).

### For Development
```bash
# Verify your Python version
python --version

# Should be 3.11 or higher
pip install -e ".[dev]"
```

### Testing Against Specific Python Version
```bash
# Using pyenv or conda to test different versions
pyenv local 3.11.0
python -m pytest

pyenv local 3.12.0
python -m pytest
```

## FreeCAD Priority

**FreeCAD compatibility is the top priority.** If a Python feature breaks
compatibility with FreeCAD's bundled Python, we don't use it, even if it's
available in newer Python versions.
