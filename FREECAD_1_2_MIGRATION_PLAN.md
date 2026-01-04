# FreeCAD 1.2.0+ Migration Plan

## Overview
Migration plan to align GitPDM addon with FreeCAD 1.2.0+ standards based on feedback from the FreeCAD addon integration coordinator.

## Key Requirements

### 1. **FreeCAD Version Support**
- Set minimum FreeCAD version to 1.2.0+
- Drop support for older Qt versions (pre-1.2.0)
- This simplifies Qt version handling significantly

### 2. **Python 2 Support Removal**
- Remove all `# -*- coding: utf-8 -*-` encoding declarations
- Python 3 is default since FreeCAD 0.19+
- UTF-8 is default encoding in Python 3

### 3. **New Module Structure**
- Restructure addon to follow the 'new' FreeCAD addon format
- All addon files must be inside `freecad/` folder structure
- Entry points change from `Init.py` & `InitGui.py` to `__init__.py` & `init_gui.py`
- Benefits: Better namespace isolation and cleaner addon loading

## Current State Assessment

### ✅ What's Already Good
- Python version requirement: `>=3.10` (well above Python 3 requirement)
- Modern package structure in `freecad_gitpdm/` folder
- Using pyproject.toml for configuration

### ⚠️ Issues Found

#### 1. Entry Point Files (High Priority)
**Current:**
- `Init.py` (root level)
- `InitGui.py` (root level)

**Issue:** Old naming convention, not following new module structure

#### 2. Qt Version Support (High Priority)
**Found 20+ files with PySide2/PySide6 fallback logic:**
```python
try:
    from PySide6 import QtCore
except ImportError:
    from PySide2 import QtCore
```

**Files affected:**
- `InitGui.py` (lines 44-46, 59-61)
- `freecad_gitpdm/ui/panel.py`
- `freecad_gitpdm/ui/gitcad_lock.py`
- `freecad_gitpdm/ui/gitcad_init_wizard.py`
- `freecad_gitpdm/ui/gitcad_config_dialog.py`
- `freecad_gitpdm/ui/fetch_pull.py`
- `freecad_gitpdm/ui/file_browser.py`
- `freecad_gitpdm/ui/new_repo_wizard.py`
- `freecad_gitpdm/ui/github_auth.py`
- `freecad_gitpdm/ui/repo_picker.py`
- `freecad_gitpdm/ui/commit_push.py`
- `freecad_gitpdm/ui/branch_ops.py`
- `freecad_gitpdm/ui/dialogs.py`
- `freecad_gitpdm/ui/repo_validator.py`
- `freecad_gitpdm/export/thumbnail.py`
- `tests/test_ui_components.py`

**Impact:** With FreeCAD 1.2.0+, only PySide6 is needed

#### 3. Python 2 Encoding Declarations (Medium Priority)
**Found in 20+ files** (shown in grep results)

**Files affected:**
- `Init.py`
- `InitGui.py`
- All files in `freecad_gitpdm/` modules
- All test files in `tests/`
- Various debug scripts

**Impact:** Clutter and unnecessary legacy code

#### 4. Module Structure (High Priority)
**Current structure:**
```
GitPDM/
├── Init.py                    # Old entry point
├── InitGui.py                 # Old entry point
├── freecad_gitpdm/           # Main package
│   ├── __init__.py
│   ├── workbench.py
│   ├── commands.py
│   └── ...
```

**Required structure for FreeCAD 1.2.0+:**
```
GitPDM/
├── freecad/
│   └── gitpdm/               # All addon code here
│       ├── __init__.py       # New entry point (was Init.py)
│       ├── init_gui.py       # New entry point (was InitGui.py)
│       ├── workbench.py
│       ├── commands.py
│       └── ...
```

## Migration Strategy

### Phase 1: Preparation & Documentation ✓ (Current)
- [x] Assess current codebase
- [x] Identify all affected files
- [x] Create migration plan
- [ ] Create backup branch
- [ ] Update README with new structure info

### Phase 2: Module Structure Refactoring (Breaking Change)
**Priority: HIGH - Required for FreeCAD 1.2.0+ compatibility**

#### Step 2.1: Create New Directory Structure
```bash
mkdir -p freecad/gitpdm
```

#### Step 2.2: Move and Rename Entry Points
- Move `Init.py` → `freecad/gitpdm/__init__.py`
- Move `InitGui.py` → `freecad/gitpdm/init_gui.py`
- Update imports in both files

#### Step 2.3: Migrate Module Code
- Move `freecad_gitpdm/*` → `freecad/gitpdm/`
- Update all internal imports from `freecad_gitpdm` to `freecad.gitpdm`
- Update pyproject.toml package name

#### Step 2.4: Update Import Paths
Files to update (examples):
- All UI components importing from `freecad_gitpdm.*`
- Test files importing from `freecad_gitpdm.*`
- Command registrations
- Workbench initialization

**Import Change Pattern:**
```python
# OLD
from freecad_gitpdm.core import log
from freecad_gitpdm import commands

# NEW
from freecad.gitpdm.core import log
from freecad.gitpdm import commands
```

### Phase 3: Qt Version Cleanup (Breaking Change)
**Priority: HIGH - Simplifies maintenance**

#### Step 3.1: Remove PySide2 Fallback Logic
Update all files with Qt imports to use only PySide6:

**Pattern to replace:**
```python
# OLD
try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets
    # Error handling...

# NEW
from PySide6 import QtCore, QtWidgets
```

#### Step 3.2: Update Test Fixtures
- Remove PySide2 imports from `tests/test_ui_components.py`
- Update any Qt-related test mocks

### Phase 4: Python 2 Legacy Cleanup (Non-Breaking)
**Priority: MEDIUM - Code cleanup**

#### Step 4.1: Remove Encoding Declarations
Remove the first line from all Python files:
```python
# -*- coding: utf-8 -*-
```

**Affected files:** ~30+ files across:
- `freecad/gitpdm/` (after migration)
- `tests/`
- Debug scripts
- Entry points

**Script approach:**
```bash
# Can use automated script to remove from all .py files
find . -name "*.py" -exec sed -i '1{/# -*- coding: utf-8 -*-/d}' {} \;
```

### Phase 5: Metadata & Documentation Updates
**Priority: MEDIUM**

#### Step 5.1: Create package.xml
FreeCAD 1.2.0+ may use package.xml for addon metadata:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<package format="2">
  <name>GitPDM</name>
  <version>0.2.0</version>
  <date>2026-01-04</date>
  <maintainer email="contact@nerd-sniped.com">Nerd-Sniped</maintainer>
  <license>MIT</license>
  <url type="repository">https://github.com/nerd-sniped/GitPDM</url>
  <description>Git-based Product Data Management for FreeCAD</description>
  <depend version_gte="1.2.0">FreeCAD</depend>
  <pythonmin>3.10</pythonmin>
</package>
```

#### Step 5.2: Update pyproject.toml
```toml
[project]
name = "freecad-gitpdm"
version = "0.2.0"  # Bump version for breaking changes
requires-python = ">=3.10"
# Add FreeCAD version constraint if possible
```

#### Step 5.3: Update Documentation
Files to update:
- `README.md` - Add FreeCAD 1.2.0+ requirement
- `IMPLEMENTATION_QUICKSTART.md` - Update import examples
- `TESTING_GUIDE.md` - Update test setup instructions
- `PLATFORM_SUPPORT.md` - Update Python/Qt requirements

### Phase 6: Testing & Validation
**Priority: CRITICAL**

#### Step 6.1: Unit Tests
- [ ] Run full test suite with new imports
- [ ] Update all test fixtures using old import paths
- [ ] Verify all Qt components work with PySide6 only

#### Step 6.2: Integration Testing
- [ ] Test addon installation in FreeCAD 1.2.0+
- [ ] Verify workbench registration
- [ ] Test all UI panels and dialogs
- [ ] Verify Git operations still work
- [ ] Test GitHub authentication flows

#### Step 6.3: Manual Testing Checklist
- [ ] Install addon from new structure
- [ ] Activate GitPDM workbench
- [ ] Open GitPDM panel
- [ ] Initialize new repository
- [ ] Clone existing repository
- [ ] Commit and push changes
- [ ] Create and switch branches
- [ ] Test lock/unlock functionality
- [ ] Verify thumbnail generation

## Risk Assessment

### High Risk Items
1. **Module structure change** - All imports will break
2. **Entry point renaming** - FreeCAD must load addon correctly
3. **Namespace isolation** - May expose hidden import issues

### Medium Risk Items
1. **Qt version change** - PySide6 API differences (minimal in our usage)
2. **Test suite compatibility** - Import path updates needed

### Low Risk Items
1. **Encoding declaration removal** - Purely cosmetic, no functional impact
2. **Documentation updates** - No code changes

## Rollback Strategy

### If Issues Occur Post-Migration:
1. Keep old structure in separate branch: `legacy-pre-1.2`
2. Tag current version before migration: `v0.1.0-legacy`
3. New structure becomes: `v0.2.0-freecad-1.2+`
4. Users on older FreeCAD can use legacy branch

### Compatibility Matrix:
| FreeCAD Version | GitPDM Version | Branch |
|----------------|----------------|---------|
| < 1.2.0 | v0.1.x | `legacy-pre-1.2` |
| >= 1.2.0 | v0.2.x+ | `main` |

## Implementation Timeline

### Week 1: Structure Migration (Phase 2)
- Days 1-2: Create new directory structure and move files
- Days 3-4: Update all imports throughout codebase
- Day 5: Initial testing and bug fixes

### Week 2: Qt Cleanup & Testing (Phases 3-4)
- Days 1-2: Remove PySide2 fallback code
- Day 3: Remove encoding declarations
- Days 4-5: Comprehensive testing

### Week 3: Documentation & Release (Phases 5-6)
- Days 1-2: Update all documentation
- Days 3-4: Final integration testing
- Day 5: Release preparation and announcement

## Success Criteria

### Must Have (Blocking)
- [ ] Addon loads correctly in FreeCAD 1.2.0+
- [ ] All workbench commands function properly
- [ ] UI panels display and operate correctly
- [ ] Git operations work without errors
- [ ] All tests pass with new structure
- [ ] No PySide2 imports remain
- [ ] Documentation reflects new structure

### Should Have (Non-Blocking)
- [ ] All encoding declarations removed
- [ ] package.xml created
- [ ] Migration guide for users
- [ ] Changelog documenting breaking changes

### Nice to Have
- [ ] Automated migration script for users
- [ ] Performance benchmarks vs old structure
- [ ] Comparison documentation

## Breaking Changes Announcement

When releasing v0.2.0, clearly communicate:

### For Users:
- **Requires FreeCAD 1.2.0 or newer**
- Older FreeCAD versions must use GitPDM v0.1.x (legacy branch)
- Addon installation location may change
- No action needed if using FreeCAD 1.2.0+

### For Contributors:
- All imports changed from `freecad_gitpdm` to `freecad.gitpdm`
- Entry points renamed: `Init.py` → `__init__.py`, `InitGui.py` → `init_gui.py`
- Only PySide6 supported (no PySide2 fallback)
- Python 2 compatibility code removed

## Questions for FreeCAD Coordinator

Before starting migration, clarify:

1. **Module structure specifics:**
   - Should it be `freecad/gitpdm/` or `freecad/GitPDM/`? (case sensitivity)
   - Any other structural requirements we should know?

2. **Metadata files:**
   - Is package.xml required for 1.2.0+?
   - What other metadata files are needed?

3. **Testing:**
   - How can we test addon loading before release?
   - Any pre-release testing environment available?

4. **Migration support:**
   - Will addon manager handle the structural change?
   - Do users need to reinstall, or is it seamless?

## Next Steps

1. ✅ Review this plan with team
2. ⬜ Get answers to open questions from FreeCAD coordinator
3. ⬜ Create backup branch: `legacy-pre-1.2`
4. ⬜ Create feature branch: `feature/freecad-1.2-migration`
5. ⬜ Begin Phase 2: Module Structure Refactoring
6. ⬜ Proceed with remaining phases systematically

## Notes

- This is a **major breaking change** - version should go from 0.1.x → 0.2.0 (or even 1.0.0)
- Consider this as "GitPDM 2.0" internally - complete restructuring
- Excellent opportunity to clean up any other technical debt
- The namespace isolation benefits will help with future FreeCAD addon ecosystem growth

## References

- FreeCAD 1.2.0 Release Notes (pending)
- FreeCAD Addon Guidelines: https://wiki.freecad.org/Addon
- PySide6 Documentation: https://doc.qt.io/qtforpython-6/
