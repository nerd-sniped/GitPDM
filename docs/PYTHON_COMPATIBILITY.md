# Python Version Compatibility

## Supported Python Versions

GitPDM supports **Python 3.8+** to ensure compatibility with all FreeCAD versions:

- **Python 3.8** - FreeCAD 0.19+
- **Python 3.9** - FreeCAD 0.20
- **Python 3.10** - FreeCAD 0.21 (most common)
- **Python 3.11** - FreeCAD 0.21+
- **Python 3.12** - Latest FreeCAD builds

## Design Decisions

### Why Python 3.8+?
FreeCAD bundles its own Python interpreter, and different FreeCAD versions ship with different Python versions. To ensure GitPDM works across all supported FreeCAD releases, we target Python 3.8 as the minimum version.

### Modern Syntax Support
Despite targeting Python 3.8, the codebase uses modern Python syntax through `from __future__ import annotations`:

- **Union types**: `str | None` instead of `Optional[str]`
- **Type hints**: Full type annotation support
- **Dataclasses**: Modern data structures

This gives us the best of both worlds: modern, readable code that runs on older Python versions.

## Testing

The CI/CD pipeline tests against all supported Python versions (3.8-3.12) on:
- Linux (Ubuntu)
- Windows
- macOS

This ensures compatibility across all platforms and Python versions that FreeCAD might use.

## Installation

### Within FreeCAD
GitPDM automatically uses FreeCAD's bundled Python (no installation needed).

### For Development
```bash
# Verify your Python version
python --version

# Should be 3.8 or higher
pip install -e ".[dev]"
```

### Testing Against Specific Python Version
```bash
# Using pyenv or conda to test different versions
pyenv local 3.8.0
python -m pytest

pyenv local 3.10.0
python -m pytest
```

## Known Limitations

- Requires `from __future__ import annotations` for union type syntax
- Some type checking features (like `Self` type) require Python 3.11+, but we avoid these
- Pattern matching (`match`/`case`) requires Python 3.10+, so we use if/elif instead

## FreeCAD Priority

**FreeCAD compatibility is the top priority.** If a Python feature breaks compatibility with FreeCAD's bundled Python, we don't use it, even if it's available in newer Python versions.
