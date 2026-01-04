# Sprint 3: Wrapper Elimination

**Duration:** 3-4 days  
**Goal:** Remove the GitCAD wrapper layer entirely, replacing all subprocess calls with direct Python implementations

---

## Overview

With Sprint 1 (core migration) and Sprint 2 (hooks) complete, the `freecad_gitpdm/gitcad/wrapper.py` module is obsolete. This sprint removes it completely and updates all code to use direct Python implementations.

## Objectives

✅ Remove `freecad_gitpdm/gitcad/wrapper.py` (564 lines)  
✅ Update all callers to use new core modules  
✅ Remove bash script dependencies  
✅ Simplify `export/gitcad_integration.py`  
✅ Update UI code to use direct APIs  
✅ Deprecate `FreeCAD_Automation/` bash scripts

---

## Task Breakdown

### Task 3.1: Identify Wrapper Usage
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P0 (Blocking)

**Description:**
Find all code that imports or uses the GitCAD wrapper:

```bash
# Search for wrapper usage
grep -r "from.*gitcad.*wrapper" freecad_gitpdm/
grep -r "GitCADWrapper" freecad_gitpdm/
grep -r "gitcad_integration" freecad_gitpdm/
```

**Expected Locations:**
- `export/gitcad_integration.py` - Export/import integration
- `ui/gitcad_*.py` - UI dialogs for GitCAD features
- `ui/panel.py` - Lock status, export buttons

**Deliverables:**
- [ ] Complete list of wrapper call sites
- [ ] Dependency graph
- [ ] Refactoring checklist

**Acceptance Criteria:**
- All wrapper usage identified
- No hidden dependencies

---

### Task 3.2: Refactor Export Integration
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P0 (Blocking)

**Description:**
Replace `export/gitcad_integration.py` with direct core module usage:

**Before (wrapper-based):**
```python
# freecad_gitpdm/export/gitcad_integration.py

def gitcad_export_if_available(repo_root, file_path, gitcad_wrapper=None):
    """Export using GitCAD wrapper."""
    if gitcad_wrapper is None:
        from freecad_gitpdm.gitcad import is_gitcad_initialized
        if not is_gitcad_initialized(repo_root):
            return True
        gitcad_wrapper = GitCADWrapper(repo_root)
    
    result = gitcad_wrapper.export_fcstd(file_path)
    return result.ok
```

**After (direct core usage):**
```python
# freecad_gitpdm/export/fcstd_handler.py (renamed & simplified)

from pathlib import Path
from freecad_gitpdm.core import fcstd_tool, config_manager, log
from freecad_gitpdm.core.result import Result

def export_fcstd_if_configured(
    repo_root: Path,
    fcstd_path: Path
) -> Result:
    """
    Export .FCStd file to uncompressed directory if configured.
    
    This is called after saving a FreeCAD document to keep the
    uncompressed representation in sync.
    
    Args:
        repo_root: Repository root path
        fcstd_path: Path to .FCStd file
        
    Returns:
        Result indicating success/failure
    """
    # Check if FCStd export is configured
    try:
        config = config_manager.load_config(repo_root)
    except Exception as e:
        log.debug(f"No GitPDM config found: {e}")
        return Result.success("Export not configured")
    
    # Export the file
    log.info(f"Exporting {fcstd_path} after save")
    return fcstd_tool.export_fcstd(fcstd_path, config=config)

def import_fcstd_if_available(
    repo_root: Path,
    fcstd_path: Path
) -> Result:
    """
    Import .FCStd file from uncompressed directory if available.
    
    This is called before opening a FreeCAD document to ensure
    the .FCStd file is up-to-date with its uncompressed version.
    
    Args:
        repo_root: Repository root path
        fcstd_path: Path to .FCStd file
        
    Returns:
        Result indicating success/failure
    """
    try:
        config = config_manager.load_config(repo_root)
    except Exception:
        return Result.success("Import not configured")
    
    # Check if uncompressed dir exists
    uncompressed_dir = config_manager.get_uncompressed_dir(
        repo_root,
        str(fcstd_path.relative_to(repo_root)),
        config
    )
    
    if not uncompressed_dir.exists():
        log.debug(f"No uncompressed dir for {fcstd_path}")
        return Result.success("No uncompressed version")
    
    # Import the file
    log.info(f"Importing {fcstd_path} before open")
    return fcstd_tool.import_fcstd(
        uncompressed_dir,
        fcstd_path,
        config=config
    )
```

**Deliverables:**
- [ ] Rename `gitcad_integration.py` → `fcstd_handler.py`
- [ ] Remove wrapper dependency
- [ ] Simplify function signatures
- [ ] Update all callers

**Acceptance Criteria:**
- No wrapper imports
- All export/import paths working
- Tests updated and passing

---

### Task 3.3: Refactor Lock UI
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P0 (Blocking)

**Description:**
Update lock-related UI code to use `core/lock_manager.py` directly:

**Files to Update:**
- `ui/gitcad_lock.py` - Lock/unlock dialogs
- `ui/panel.py` - Lock status display

**Before:**
```python
# ui/gitcad_lock.py

from freecad_gitpdm.gitcad import GitCADWrapper

def lock_file(repo_root, fcstd_path):
    wrapper = GitCADWrapper(repo_root)
    return wrapper.lock_file(fcstd_path)
```

**After:**
```python
# ui/lock_dialog.py (renamed & refactored)

from pathlib import Path
from freecad_gitpdm.core.lock_manager import LockManager
from freecad_gitpdm.core import log

class LockDialog(QtWidgets.QDialog):
    """Dialog for locking/unlocking FCStd files."""
    
    def __init__(self, repo_root: Path, fcstd_path: str, parent=None):
        super().__init__(parent)
        self.repo_root = repo_root
        self.fcstd_path = fcstd_path
        self.lock_manager = LockManager(repo_root)
        self._setup_ui()
    
    def lock_file(self):
        """Lock the file."""
        force = self.force_checkbox.isChecked()
        result = self.lock_manager.lock_file(self.fcstd_path, force=force)
        
        if result.ok:
            QtWidgets.QMessageBox.information(
                self,
                "Locked",
                f"Successfully locked {self.fcstd_path}"
            )
            self.accept()
        else:
            QtWidgets.QMessageBox.critical(
                self,
                "Lock Failed",
                result.error.message
            )
```

**Deliverables:**
- [ ] Refactor `gitcad_lock.py` → `lock_dialog.py`
- [ ] Use LockManager directly
- [ ] Update panel lock status display
- [ ] Remove wrapper dependencies

**Acceptance Criteria:**
- Lock/unlock from UI works
- Lock status displays correctly
- No wrapper imports

---

### Task 3.4: Refactor GitCAD Config UI
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P1

**Description:**
Update `ui/gitcad_config_dialog.py` to use new config system:

**Changes:**
- Use `core/config_manager.py` instead of wrapper
- Remove subprocess calls
- Simplify config loading/saving

**Deliverables:**
- [ ] Update config dialog
- [ ] Use config_manager directly
- [ ] Remove wrapper dependency

**Acceptance Criteria:**
- Config dialog works
- Can save/load config.json
- No wrapper imports

---

### Task 3.5: Remove Wrapper Module
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P0 (Blocking)

**Description:**
Delete the wrapper module and clean up:

**Files to Remove:**
- `freecad_gitpdm/gitcad/wrapper.py` (564 lines)
- `freecad_gitpdm/gitcad/test_gitcad.py` (if wrapper-specific)
- `debug_wrapper.py` (root level debug script)
- `test_wrapper_quick.py` (root level test script)

**Files to Update:**
- `freecad_gitpdm/gitcad/__init__.py` - Remove wrapper exports
- `TESTING_GUIDE.md` - Remove wrapper testing sections

**Before (`gitcad/__init__.py`):**
```python
from .wrapper import (
    GitCADWrapper,
    lock_file,
    unlock_file,
    # ...
)
```

**After (`gitcad/__init__.py`):**
```python
# This module is DEPRECATED
# Use freecad_gitpdm.core.fcstd_tool and freecad_gitpdm.core.lock_manager instead

import warnings

warnings.warn(
    "freecad_gitpdm.gitcad is deprecated. "
    "Use freecad_gitpdm.core.fcstd_tool and freecad_gitpdm.core.lock_manager instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility (temporary)
from freecad_gitpdm.core.lock_manager import (
    LockManager as GitCADWrapper,  # Alias for compatibility
    lock_file,
    unlock_file,
    get_locks,
)
from freecad_gitpdm.core import fcstd_tool
```

**Deliverables:**
- [ ] Delete wrapper.py
- [ ] Delete wrapper test scripts
- [ ] Update __init__.py with deprecation
- [ ] Update documentation

**Acceptance Criteria:**
- Wrapper module deleted
- Deprecation warnings in place
- No import errors
- Tests still pass

---

### Task 3.6: Deprecate Bash Scripts
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P1

**Description:**
Mark bash scripts as deprecated since Python hooks replace them:

**Files to Update:**
- `FreeCAD_Automation/git_aliases/lock.sh` - Add deprecation notice
- `FreeCAD_Automation/git_aliases/unlock.sh` - Add deprecation notice
- `FreeCAD_Automation/hooks/*` - Add deprecation notices

**Example:**
```bash
#!/bin/bash
# DEPRECATED: This bash script is replaced by Python hooks
# Use GitPDM UI or freecad_gitpdm.core.lock_manager instead
echo "WARNING: This bash script is deprecated"
echo "Please use GitPDM workbench for locking operations"
exit 1
```

**Deliverables:**
- [ ] Deprecation notices in bash scripts
- [ ] Updated README in FreeCAD_Automation/
- [ ] Migration guide for bash users

**Acceptance Criteria:**
- Bash scripts marked deprecated
- Clear migration path documented
- Scripts exit with warning

---

### Task 3.7: Update Tests
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P0 (Blocking)

**Description:**
Update all tests to use new core modules instead of wrapper:

**Test Files to Update:**
- `tests/test_git_client.py` - May reference wrapper
- Any integration tests using wrapper

**New Tests to Add:**
- Integration tests for fcstd_handler
- Integration tests for lock_dialog
- End-to-end workflow tests

**Deliverables:**
- [ ] All tests updated
- [ ] No wrapper dependencies in tests
- [ ] New integration tests added
- [ ] All tests passing

**Acceptance Criteria:**
- Test suite passes
- No wrapper imports in tests
- Coverage maintained >80%

---

### Task 3.8: Performance Validation
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P1

**Description:**
Validate that removing the wrapper improves performance:

**Benchmarks:**
1. **Export FCStd** - Time to export a 10MB .FCStd file
2. **Import FCStd** - Time to import from uncompressed dir
3. **Lock file** - Time to acquire lock
4. **Get locks** - Time to query all locks

**Expected Results:**
- Export: 20-30% faster (no subprocess overhead)
- Import: 20-30% faster
- Lock: 10-20% faster
- Get locks: 10-20% faster

**Deliverables:**
- [ ] Performance test script
- [ ] Before/after benchmarks
- [ ] Performance report

**Acceptance Criteria:**
- Performance improved or neutral
- No regressions
- Report documented

---

### Task 3.9: Documentation Updates
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P1

**Description:**
Update all documentation to reflect wrapper removal:

**Files to Update:**
- `ARCHITECTURE_ASSESSMENT.md` - Update with Sprint 3 progress
- `freecad_gitpdm/gitcad/README.md` - Mark as deprecated
- `TESTING_GUIDE.md` - Remove wrapper testing sections
- API documentation

**New Documentation:**
- Migration guide from wrapper to core modules
- Developer guide for core modules
- Updated user guide

**Deliverables:**
- [ ] All docs updated
- [ ] Migration guide created
- [ ] Deprecation notices added

**Acceptance Criteria:**
- Documentation accurate
- No wrapper references (except deprecation)
- Migration path clear

---

## Definition of Done (Sprint 3)

- [x] Wrapper module deleted
- [x] All callers updated to use core modules
- [x] Bash scripts deprecated
- [x] Tests updated and passing
- [x] Performance validated
- [x] Documentation complete
- [x] No regressions

---

## Risks & Mitigations

**Risk:** Breaking changes for external users of wrapper  
**Mitigation:** Deprecation warnings, compatibility shims, migration guide

**Risk:** Missed wrapper dependencies  
**Mitigation:** Comprehensive code search, test coverage

**Risk:** Performance regression  
**Mitigation:** Benchmarking, profiling, optimization

---

## Dependencies

- Sprint 1 completed (core modules)
- Sprint 2 completed (Python hooks)
- All tests passing

---

## Success Metrics

- ✅ Zero subprocess calls to bash scripts
- ✅ 500+ lines of code removed (wrapper.py)
- ✅ Performance improved by 20%+
- ✅ All tests passing
- ✅ Documentation complete

---

**Next Sprint:** Sprint 4 - UI Refactoring (split panel.py, polish UX)
