# Changelog

All notable changes to GitPDM will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-04

### Sprint 7 - Polish & v1.0 Release

**Major consolidation release - Production ready!**

#### Added
- Comprehensive release notes (`RELEASE_NOTES_v1.0.0.md`)
- Updated README with v1.0.0 features and improvements
- Version history section in README

#### Changed
- Version bumped to 1.0.0 across all files:
  - `package.xml` - FreeCAD addon metadata
  - `metadata.txt` - Legacy metadata
  - `__init__.py` - Module version
- Enhanced package description with consolidation details
- Updated documentation references

## [Unreleased]

### Sprint 6 - Standardization (2026-01-04)

Standardized naming throughout codebase, removing legacy "GitCAD" references and adopting consistent "GitPDM" branding.

#### Renamed Files
- `ui/gitcad_config_dialog.py` → `ui/config_dialog.py`
- `ui/gitcad_lock.py` → `ui/lock_handler.py`
- `ui/gitcad_init_wizard.py` → `ui/init_wizard.py`
- `export/gitcad_integration.py` → `export/fcstd_export.py`

#### Renamed Classes & Functions
- `GitCADLockHandler` → `LockHandler`
- `gitcad_export_if_available()` → `export_if_available()`
- `gitcad_import_if_available()` → `import_if_available()`
- `check_gitcad_availability()` → `check_availability()`

#### Changed Variables
- `_gitcad_lock` → `_lock_handler` (throughout codebase)
- `_gitcad_available` → `_available`
- `_gitcad_group` → `_lock_group`
- `_update_gitcad_status()` → `_update_lock_status()`

#### Updated UI Text
- All UI strings changed from "GitCAD" → "GitPDM"
- Consistent branding throughout interface

### Sprint 5 - Remove Deprecated Wrapper Layer (2026-01-04)

#### Removed
- Removed entire `freecad/gitpdm/gitcad/` directory
- Removed `wrapper.py` (612 lines) - Legacy bash wrapper
- Removed `config.py` (271 lines) - Legacy config bridge
- Removed `detector.py` - Legacy detection utilities
- Removed GitCADWrapper class and bash dependencies
- Deprecated `test_wrapper_quick.py` - No longer functional

#### Changed
- UI components now use `core.*` modules directly:
  - `gitcad_config_dialog.py` - Simplified for native config (removed Python path, project path fields)
  - `gitcad_lock.py` - Uses `has_config()` instead of `is_gitcad_initialized()`
  - `new_repo_wizard.py` - Creates config with `FCStdConfig()` directly
  - `gitcad_init_wizard.py` - Creates config with native API
- All imports changed from `freecad.gitpdm.gitcad.*` to `freecad.gitpdm.core.*`
### Sprint 4 - Configuration Migration (2026-01-04)

#### Removed
- Removed `FreeCAD_Automation/` directory (bash scripts and legacy structure)
- Removed bash dependency for configuration

#### Added
- New configuration location: `.gitpdm/config.json` (native Python format)
- `core/config_migration.py` - Automatic configuration migration utility
- `docs/LEGACY_GITCAD_REPOS.md` - Comprehensive guide for legacy repository support
- Auto-migration on config load (transparent to users)
- Migration marker files for debugging

#### Changed
- Configuration now uses simpler Python dict format (not nested GitCAD format)
- `config_manager.py` checks both old and new locations (backward compatible)
- All config paths updated: `FreeCAD_Automation/config.json` → `.gitpdm/config.json`
- UI components updated to show new config location
- Test suite updated for new config paths

### Sprint 3 - GitCAD-main Consolidation (2026-01-04)

#### Removed
- Removed nested `GitCAD-main/` directory (legacy standalone project)
- Removed `install_gitcad.py` script (obsolete after Sprint 1)
- Deleted example files (`AssemblyExample.FCStd`, `BIMExample.FCStd`)
- Removed redundant git configuration files from GitCAD-main

#### Added
- Created `docs/GITCAD_HISTORY.md` documenting project origins and consolidation
- Added History section to main README acknowledging GitCAD origins

#### Changed
- Updated all code references to remove GitCAD-main path lookups
- Updated UI components to use bundled FreeCAD_Automation (deprecated, will be removed in Sprint 4)
- Consolidated project structure - single unified codebase

## [0.2.0] - 2026-01-04

### Sprint 1-2 - FreeCAD 1.2 Migration & Native Python Core

#### Added
- FreeCAD 1.2.0+ support with new module structure
- Native Python implementation of core operations (replaces bash wrapper):
  - `core/fcstd_tool.py` - FCStd compression/decompression
  - `core/lock_manager.py` - File locking with Git LFS
  - `core/config_manager.py` - Configuration management
- Comprehensive test suite (50+ tests, 80%+ coverage for core modules)
- `USE_NATIVE_CORE` feature flag (defaults to True)

#### Changed
- Restructured to follow FreeCAD 1.2 addon standards
- Module structure: `freecad_gitpdm` → `freecad.gitpdm`
- Entry points: `Init.py`/`InitGui.py` → `__init__.py`/`init_gui.py`
- Qt6/PySide6 only (removed PySide2 compatibility)
- Python 3.10+ required (removed Python 2 legacy code)
- Deprecated bash wrapper layer (`freecad/gitpdm/gitcad/wrapper.py`)

#### Removed
- Removed PySide2 fallback code
- Removed Python 2 encoding declarations
- Removed unnecessary UTF-8 comments

### Breaking Changes
- Requires FreeCAD 1.2.0 or newer
- Import paths changed (old code needs updating)
- No longer supports FreeCAD 0.20, 0.21, or 1.0 (use v0.1.x from `legacy-pre-1.2` branch)

## [0.1.x] - Legacy

For changes in the v0.1.x series (FreeCAD 0.20/0.21/1.0 support), see the `legacy-pre-1.2` branch.

---

## Version Numbering

- **0.x.x**: Pre-1.0 development versions
- **1.0.0**: First consolidated production release (planned after Sprint 7)
- **Major.Minor.Patch**: Following semantic versioning

## Sprint Roadmap

- ✅ **Sprint 1**: Native Python core (complete)
- ✅ **Sprint 2**: FreeCAD 1.2 migration (complete)
- ✅ **Sprint 3**: Remove GitCAD-main directory (complete)
- ✅ **Sprint 4**: Remove FreeCAD_Automation & config migration (complete)
- ✅ **Sprint 5**: Remove deprecated wrapper layer (complete)
- ✅ **Sprint 6**: Standardize configuration & naming (complete)
- ✅ **Sprint 7**: Polish & release v1.0.0 (complete)

**🎉 All sprints complete! v1.0.0 released!**

---

## Attribution

GitPDM incorporates innovations from the GitCAD project by Michael Marais. See [docs/GITCAD_HISTORY.md](docs/GITCAD_HISTORY.md) for full history and attribution.
