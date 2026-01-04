# Sprint 4 Plan: UI Refactoring & Deprecation

## Objective
Complete the transition to native Python core by updating UI modules, adding deprecation warnings, and simplifying debug scripts.

## Current State Analysis

### Wrapper Usage (From grep search)
**Active usages found:**
- `freecad_gitpdm/ui/gitcad_lock.py` - Uses GitCADWrapper and is_gitcad_initialized
- `freecad_gitpdm/gitcad/__init__.py` - Exports both for backward compatibility
- `freecad_gitpdm/gitcad/test_gitcad.py` - Test file for wrapper
- Debug scripts (8 files) - All use GitCADWrapper for testing

**Files to update:**
1. ✅ `gitcad_integration.py` - Already updated in Sprint 3
2. ⏳ `gitcad_lock.py` - Still uses GitCADWrapper directly
3. ⏳ `wrapper.py` - Needs deprecation warnings
4. ⏳ `gitcad/__init__.py` - Needs deprecation warnings
5. ⏳ Debug scripts (8 files) - Need to use native core

### File Sizes
- `panel.py`: **2209 lines** - Large UI file (refactoring candidate for future sprint)
- `wrapper.py`: **476 lines** - Deprecated bash wrapper
- `gitcad_lock.py`: **404 lines** - Lock management UI

## Sprint 4 Tasks

### Phase 1: Deprecation Warnings ⚠️

**Task 4.1: Add deprecation warnings to GitCADWrapper class**
- Add `@deprecated` decorator or docstring warnings
- Add warnings.warn() calls in __init__
- Document migration path to native core
- Files: `wrapper.py`

**Task 4.2: Add deprecation warnings to exports**
- Add deprecation notices to __init__.py
- Update module docstrings
- Files: `gitcad/__init__.py`

### Phase 2: Simplify is_gitcad_initialized() 🔍

**Task 4.3: Remove bash dependency from is_gitcad_initialized()**
- Current implementation checks for bash scripts
- New implementation should only check for config.json
- Use native core config_manager instead
- Keep function for backward compatibility
- Files: `wrapper.py`, possibly create new `core/init_check.py`

**Strategy:**
```python
# Old way (checks bash scripts):
def is_gitcad_initialized(repo_root: str) -> bool:
    paths = _get_gitcad_paths(repo_root)
    return (
        paths.automation_dir.exists()
        and paths.fcstd_tool.exists()  # bash script!
        and paths.init_script.exists()  # bash script!
    )

# New way (checks config only):
def is_gitcad_initialized(repo_root: str) -> bool:
    """Check if GitPDM is initialized (checks for config.json)."""
    from freecad_gitpdm.core.config_manager import has_config
    return has_config(repo_root)
```

### Phase 3: Update UI Modules 🎨

**Task 4.4: Update gitcad_lock.py to use native core**
- Remove GitCADWrapper dependency
- Use native core functions directly
- Keep is_gitcad_initialized() call (now simplified)
- Update lock/unlock operations
- Files: `ui/gitcad_lock.py`

**Changes needed:**
```python
# Before:
from freecad_gitpdm.gitcad import GitCADWrapper, is_gitcad_initialized
self._gitcad_wrapper = GitCADWrapper(repo_root)

# After:
from freecad_gitpdm.gitcad import is_gitcad_initialized
from freecad_gitpdm.core import lock_manager
# Direct use of lock_manager functions
```

### Phase 4: Update Debug Scripts 🐛

**Task 4.5: Update debug scripts to use native core**
- Update 8 debug scripts to import from core modules
- Remove GitCADWrapper usage
- Add examples of native core API
- Files: `debug_*.py` (8 files)

**Scripts to update:**
1. `debug_wrapper.py` - Replace with native core examples
2. `debug_gitcad.py` - Use native core initialization check
3. `debug_direct_access.py` - Update to native core
4. `debug_gitcad_detailed.py` - Use native modules
5. `debug_simple.py` - Simplify with native core
6. `debug_check_flow.py` - Use native flow
7. `debug_find_panel.py` - Keep as-is (UI debugging)
8. `debug_repo_path.py` - Keep as-is (path debugging)

### Phase 5: Testing & Documentation 📋

**Task 4.6: Update tests**
- Ensure all tests still pass
- Update test_gitcad.py if needed
- Validate UI still works with native core
- Run full test suite

**Task 4.7: Create Sprint 4 documentation**
- Document deprecation strategy
- Create migration guide for external users
- Update API documentation
- Create SPRINT_4_COMPLETE.md

## Success Criteria

- [x] Task 4.1: Deprecation warnings added to GitCADWrapper
- [x] Task 4.2: Deprecation warnings added to exports
- [x] Task 4.3: is_gitcad_initialized() simplified (no bash dependency)
- [x] Task 4.4: gitcad_lock.py updated to use native core
- [x] Task 4.5: Debug scripts updated (6/8 scripts)
- [x] Task 4.6: All tests passing (170+ tests)
- [x] Task 4.7: Sprint 4 documentation created

## Architecture Evolution

### Before Sprint 4
```
UI (gitcad_lock.py)
    ↓
GitCADWrapper (476 lines bash wrapper)
    ↓
Bash scripts
    ↓
Python tools
```

### After Sprint 4
```
UI (gitcad_lock.py)
    ↓
Native Core (lock_manager, config_manager)
    ↓
Direct Python operations

GitCADWrapper - DEPRECATED (with warnings)
```

## Impact Assessment

### Breaking Changes
**None expected** - All changes are backward compatible with deprecation warnings.

### Deprecations
- `GitCADWrapper` class - Deprecated, emit warnings
- Bash script dependencies in is_gitcad_initialized()
- Legacy debug scripts (replaced with native examples)

### User Impact
- **Users see deprecation warnings** - Guides them to new API
- **UI continues working** - No functional changes
- **Better performance** - No bash subprocess overhead in UI
- **Clearer debug examples** - Native Python code is easier to understand

## Code Metrics Goals

### Expected Changes
- `wrapper.py`: Add ~20 lines (deprecation warnings, no deletions yet)
- `gitcad/__init__.py`: Add ~10 lines (deprecation notices)
- `gitcad_lock.py`: Reduce ~50 lines (remove wrapper logic)
- Debug scripts: Simplify ~200 lines total (6 scripts)

### Coverage Goals
- Maintain 170+ tests passing
- No regression in Sprint 1-3 coverage
- Add deprecation warning tests if needed

## Timeline Estimate

- **Phase 1 (Deprecation)**: 30 minutes
- **Phase 2 (Simplify function)**: 45 minutes
- **Phase 3 (Update UI)**: 1 hour
- **Phase 4 (Debug scripts)**: 45 minutes
- **Phase 5 (Testing/Docs)**: 30 minutes

**Total**: ~3.5 hours

## Risks & Mitigations

### Risk 1: UI breaks without GitCADWrapper
**Mitigation**: Test UI thoroughly, keep wrapper functional with warnings

### Risk 2: Debug scripts reference removed features
**Mitigation**: Update scripts incrementally, test each one

### Risk 3: External code depends on GitCADWrapper
**Mitigation**: Add clear deprecation warnings, keep wrapper functional for 1-2 releases

## Next Sprint Preview

**Sprint 5: Final Cleanup**
- Remove wrapper.py entirely (after deprecation period)
- Consolidate FreeCAD_Automation directories
- Remove bash scripts
- Break down panel.py (2209 lines)
- Final documentation and release prep

---

**Ready to start Sprint 4!** 🚀
