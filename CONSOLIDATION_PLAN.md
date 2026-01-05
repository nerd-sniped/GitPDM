# GitCAD-GitPDM Consolidation Plan
**Senior Architect Assessment & Roadmap**  
**Date:** January 4, 2026  
**Architect:** Senior FreeCAD 1.2 Developer

---

## Executive Summary

Two interns developed parallel Git integration solutions for FreeCAD without coordination:
- **GitCAD**: Strong core logic (bash-based file operations, compression, locking) but no GUI
- **GitPDM**: Excellent UX/GUI (Qt6-based panels, wizards, dialogs) but questionable backend logic

They attempted a merge by wrapping GitCAD's bash scripts with GitPDM's Python interface, creating a messy subprocess-based architecture. **Sprint 1 partially addressed this**, porting bash logic to pure Python, but significant consolidation work remains.

**Consolidation Goal:** Single, maintainable FreeCAD 1.2 addon with:
- GitPDM's GUI excellence as the primary interface
- GitCAD's proven logic (now ported to native Python)
- Proper FreeCAD 1.2 addon architecture (following reference template)
- No standalone GitCAD-main repo - fully integrated

---

## Current State Assessment

### Architecture Issues

#### 1. **GitCAD-main as Standalone Repo** 🔴 CRITICAL
**Location:** `/GitCAD-main/` (entire subdirectory)
- Contains:
  - `FreeCAD_Automation/` - Bash scripts, hooks, git aliases
  - `README.md`, `LICENSE`, `template.md`, `how-to-contribute.md`
  - `.FCStd` example files (`AssemblyExample.FCStd`, `BIMExample.FCStd`)
  - Duplicate `.gitignore`, `.gitattributes`

**Problem:** 
- GitCAD exists as a nested repository
- Install script (`install_gitcad.py`) copies `FreeCAD_Automation/` to project root
- Creates confusion about source of truth
- Unnecessary duplication of files

**Status:** Sprint 1 reduced dependency but did NOT remove GitCAD-main

#### 2. **Duplicate FreeCAD_Automation Directory** 🔴 CRITICAL
**Locations:**
- `/FreeCAD_Automation/` (copied from GitCAD-main)
- `/GitCAD-main/FreeCAD_Automation/` (original)

**Contains:**
- `FCStdFileTool.py` (598 lines) - **OBSOLETE** (replaced by `core/fcstd_tool.py`)
- Bash scripts: `FCStd-clean-filter.sh`, `python.sh`, `utils.sh`, `bash.ps1`, `git.ps1`
- Git hooks: `hooks/` directory
- Git aliases: `git_aliases/` directory
- `config.json` - Configuration file (still referenced)
- User scripts: `user_scripts/`
- Tests: `tests/`

**Problem:**
- Sprint 1 ported `FCStdFileTool.py` logic → `core/fcstd_tool.py` ✅
- Bash wrapper layer (`wrapper.py`) marked deprecated ✅
- But bash scripts and hooks still exist and are referenced
- Config file still expected at `FreeCAD_Automation/config.json`

#### 3. **Wrapper Layer Still Partially Active** 🟡 PARTIALLY RESOLVED
**Location:** `/freecad/gitpdm/gitcad/`
- `wrapper.py` (612 lines) - Marked DEPRECATED but not removed
- `config.py` (271 lines) - Bridge to GitCAD's config.json format
- `detector.py` (218 lines) - Detects GitCAD installations
- `__init__.py` (93 lines) - Exports deprecated API

**Status:**
- Core operations ported to native Python (Sprint 1) ✅
- `USE_NATIVE_CORE` flag defaults to True ✅
- Legacy wrapper still imported in several UI components ⚠️
- Not all UI code migrated to new core modules ⚠️

#### 4. **Config Architecture Confusion** 🟡
**Two parallel config systems:**
1. **GitCAD style:** `FreeCAD_Automation/config.json`
   - Complex nested structure
   - Used by detector, wrapper, config bridge
2. **Native style:** `core/config_manager.py` with `FCStdConfig` dataclass
   - Clean Python dataclass
   - Converts to/from GitCAD format

**Problem:** Code references both, unclear which is canonical

#### 5. **Git Hooks & Scripts** 🟡
**Location:** `/FreeCAD_Automation/hooks/`, `/FreeCAD_Automation/git_aliases/`
- Git clean filter (`FCStd-clean-filter.sh`)
- Git hooks (pre-commit, post-merge, etc.)
- Git aliases (lock, unlock)

**Status:** 
- Some operations ported to Python (lock_manager.py) ✅
- Bash scripts still exist and may be used by repos initialized with GitCAD ⚠️
- Need strategy for backward compatibility vs clean break

#### 6. **FreeCAD 1.2 Compliance** 🟢 MOSTLY GOOD
**Reference:** `/reference/Addon-Template-Latest/`

**Current Structure:**
```
freecad/
  gitpdm/
    __init__.py ✅
    init_gui.py ✅
    workbench.py ✅
    commands.py ✅
    ui/ ✅
    core/ ✅
    git/ ✅
    github/ ✅
    export/ ✅
```

**Good:**
- Follows `freecad/[addon_name]/` structure ✅
- Has `init_gui.py` instead of `InitGui.py` ✅
- Uses PySide6 exclusively (FreeCAD 1.2) ✅
- Python 3.10+ requirement ✅

**Needs Work:**
- Compatibility shim at root (`InitGui.py`) should be removed after full migration
- `gitcad/` subdirectory creates confusion - should be absorbed

---

## Dependency Analysis

### UI Components Referencing GitCAD Wrapper

1. **`ui/gitcad_lock.py`** - Uses `freecad.gitpdm.gitcad` imports
2. **`ui/panel.py`** - Imports `GitCADLockHandler`, `gitcad_export_if_available`
3. **`ui/new_repo_wizard.py`** - Uses `create_default_config` from gitcad
4. **`ui/gitcad_init_wizard.py`** - Uses `create_default_config` from gitcad
5. **`ui/gitcad_config_dialog.py`** - Uses `load_gitcad_config`, `save_gitcad_config`, `GitCADConfig`

### Export Layer
- **`export/gitcad_integration.py`** - Abstraction layer with feature flag
  - `USE_NATIVE_CORE = True` (native Python)
  - Has fallback to deprecated wrapper

### Core Modules (Native Python) ✅
- `core/fcstd_tool.py` - Replaces `FCStdFileTool.py` and bash scripts
- `core/lock_manager.py` - Replaces bash lock/unlock scripts
- `core/config_manager.py` - Replaces GitCAD config parsing

---

## Consolidation Strategy

### Phase 1: Remove GitCAD-main Directory ✅ SPRINT 3
**Goal:** Eliminate nested repo, extract useful components

**Actions:**
1. Extract documentation worth keeping
2. Delete example `.FCStd` files (or move to separate examples repo)
3. Delete duplicate bash scripts
4. Remove `install_gitcad.py` (no longer needed)
5. Delete `GitCAD-main/` directory entirely

### Phase 2: Eliminate Bash Dependencies ✅ SPRINT 4
**Goal:** Remove `FreeCAD_Automation/` directory

**Actions:**
1. Migrate config.json references to native Python config
2. Remove bash wrapper detection logic
3. Update all code expecting `FreeCAD_Automation/config.json`
4. Document migration path for existing GitCAD users
5. Delete `FreeCAD_Automation/` directory

### Phase 3: Remove Deprecated Wrapper Layer ✅ SPRINT 5
**Goal:** Delete `freecad/gitpdm/gitcad/` directory

**Actions:**
1. Audit all imports of `freecad.gitpdm.gitcad`
2. Migrate UI components to use `core.*` modules directly
3. Remove compatibility shims in `export/gitcad_integration.py`
4. Delete `gitcad/` subdirectory
5. Update tests

### Phase 4: Standardize Configuration ✅ SPRINT 6
**Goal:** Single, clean configuration system

**Actions:**
1. Define canonical config location (`.gitpdm/config.json` or similar)
2. Migration utility for old `FreeCAD_Automation/config.json` files
3. Update all config references
4. Remove GitCAD format conversion code

### Phase 5: Polish & Documentation ✅ SPRINT 7
**Goal:** Production-ready consolidated addon

**Actions:**
1. Update all documentation
2. Clean up debug scripts
3. Remove root-level compatibility shims (`InitGui.py`)
4. Final architecture review
5. Performance optimization
6. Release v1.0.0

---

## Sprint Breakdown

### Sprint 3: Extract & Remove GitCAD-main 🎯 CURRENT
**Duration:** 1 session  
**Priority:** CRITICAL

#### Tasks
1. **Extract Useful Documentation** (30 min)
   - Review `GitCAD-main/README.md` for unique content
   - Merge useful sections into main `README.md`
   - Review `template.md`, `how-to-contribute.md`
   - Create `docs/GITCAD_MIGRATION.md` for historical reference

2. **Audit Example Files** (15 min)
   - Assess `AssemblyExample.FCStd`, `BIMExample.FCStd`
   - Decision: Delete or move to examples branch/repo
   - Not needed for addon operation

3. **Delete Redundant Files** (10 min)
   - `GitCAD-main/.gitignore`
   - `GitCAD-main/.gitattributes`
   - `GitCAD-main/LICENSE` (already have LICENSE at root)

4. **Remove Install Script** (5 min)
   - Delete `install_gitcad.py` (obsolete after Sprint 1)
   - Remove from any documentation

5. **Delete GitCAD-main Directory** (5 min)
   - `rm -rf GitCAD-main/`
   - Verify no broken imports

6. **Clean Up References** (20 min)
   - Search for "GitCAD-main" in codebase
   - Update file paths in debug scripts
   - Update documentation

7. **Test & Verify** (15 min)
   - Run test suite
   - Verify addon loads in FreeCAD
   - Check that no functionality broken

**Deliverables:**
- ✅ No `GitCAD-main/` directory
- ✅ `docs/GITCAD_MIGRATION.md` created
- ✅ All references updated
- ✅ Tests passing

---

### Sprint 4: Remove FreeCAD_Automation Directory
**Duration:** 2 sessions  
**Priority:** CRITICAL  
**Dependencies:** Sprint 3 complete

#### Tasks

##### Session 1: Config Migration (90 min)
1. **Define New Config Location** (20 min)
   - Decide: `.gitpdm/config.json` vs repo root
   - Update `core/config_manager.py` to use new location
   - Add migration detection logic

2. **Create Migration Utility** (40 min)
   - New file: `core/config_migration.py`
   - Function: `migrate_gitcad_config(repo_root)`
   - Detect old `FreeCAD_Automation/config.json`
   - Convert to new format/location
   - Leave breadcrumb file for future detection

3. **Update All Config References** (30 min)
   - Search codebase for "FreeCAD_Automation/config.json"
   - Update to use new path
   - Files to update:
     - `gitcad/config.py` (or remove)
     - `gitcad/detector.py`
     - `core/config_manager.py`
     - UI dialogs referencing config

##### Session 2: Remove Bash Dependencies (90 min)
4. **Audit Git Hooks Usage** (30 min)
   - Review `hooks/` directory
   - Identify which hooks are critical
   - Determine if repos using GitCAD hooks will break
   - Strategy: Keep in docs for legacy users, but don't ship

5. **Document Legacy Support** (30 min)
   - Create `docs/LEGACY_GITCAD_REPOS.md`
   - Instructions for repos initialized with bash GitCAD
   - Migration path to pure Python GitPDM
   - Backward compatibility notes

6. **Remove FreeCAD_Automation Directory** (10 min)
   - Delete `/FreeCAD_Automation/`
   - Update `.gitignore` if needed

7. **Clean Up References** (10 min)
   - Search for "FreeCAD_Automation" in code
   - Update/remove references
   - Update tests

8. **Test & Verify** (10 min)
   - Test suite
   - Manual testing with fresh repo
   - Test config migration utility

**Deliverables:**
- ✅ No `FreeCAD_Automation/` directory
- ✅ New config location: `.gitpdm/config.json`
- ✅ Migration utility: `core/config_migration.py`
- ✅ Legacy docs: `docs/LEGACY_GITCAD_REPOS.md`
- ✅ All tests passing

---

### Sprint 5: Remove Deprecated Wrapper Layer
**Duration:** 2 sessions  
**Priority:** HIGH  
**Dependencies:** Sprint 4 complete

#### Tasks

##### Session 1: UI Migration (90 min)
1. **Audit Wrapper Imports** (20 min)
   - Generate full list of files importing `freecad.gitpdm.gitcad`
   - Identify what functions/classes are used
   - Map to new core module equivalents

2. **Migrate UI Components** (60 min)
   - **Priority files:**
     - `ui/gitcad_lock.py` → Rename to `ui/lock_panel.py`
     - `ui/gitcad_init_wizard.py` → Rename to `ui/init_wizard.py`
     - `ui/gitcad_config_dialog.py` → Rename to `ui/config_dialog.py`
   
   - **Update imports:**
     ```python
     # OLD
     from freecad.gitpdm.gitcad import lock_file, unlock_file
     
     # NEW
     from freecad.gitpdm.core.lock_manager import LockManager
     ```
   
   - **Update instantiation:**
     ```python
     # OLD
     lock_file(repo_root, file_path)
     
     # NEW
     lock_mgr = LockManager(repo_root)
     lock_mgr.lock_file(file_path)
     ```

3. **Update panel.py References** (10 min)
   - Update imports in main panel
   - Test panel loading

##### Session 2: Remove Wrapper Code (90 min)
4. **Clean Export Integration** (30 min)
   - Remove `USE_NATIVE_CORE` feature flag (always native now)
   - Simplify `export/gitcad_integration.py`
   - Or delete and inline into callers
   - Rename functions: `gitcad_export_if_available` → `export_fcstd_if_enabled`

5. **Delete Deprecated gitcad/ Directory** (10 min)
   - Delete `/freecad/gitpdm/gitcad/`
   - Verify no broken imports

6. **Update Tests** (30 min)
   - Remove tests for deprecated wrapper
   - Update integration tests to use core modules
   - Verify 100% of functionality works via core modules

7. **Final Verification** (20 min)
   - Full test suite
   - Load addon in FreeCAD
   - Test all major workflows (init repo, lock/unlock, commit, push)

**Deliverables:**
- ✅ No `freecad/gitpdm/gitcad/` directory
- ✅ UI components renamed (remove "gitcad" from names)
- ✅ All imports use `core.*` modules
- ✅ Simplified export integration
- ✅ Tests updated and passing

---

### Sprint 6: Standardize Configuration & Naming
**Duration:** 1 session  
**Priority:** MEDIUM  
**Dependencies:** Sprint 5 complete

#### Tasks
1. **Audit Naming Conventions** (20 min)
   - Identify remaining "gitcad" references in code
   - Create rename mapping
   - Functions, classes, variables, comments

2. **Rename Variables & Functions** (40 min)
   - Global find/replace (carefully)
   - Examples:
     - `gitcad_export_if_available` → `export_fcstd_if_enabled`
     - `is_gitcad_initialized` → `is_git_initialized`
     - `GitCADConfig` → `RepoConfig` (if still exists)
   - Update docstrings

3. **Consolidate Settings** (30 min)
   - Review `core/settings.py`
   - Ensure all addon preferences centralized
   - Clean up any duplicate settings

4. **Update All Documentation** (30 min)
   - Search docs for "GitCAD"
   - Replace with "GitPDM" or generic terms
   - Update terminology consistently
   - Update diagrams/architecture docs

**Deliverables:**
- ✅ Consistent naming (no "gitcad" in code except docs)
- ✅ Single config location and format
- ✅ Documentation updated
- ✅ Clean, professional codebase

---

### Sprint 7: Polish & Release v1.0.0
**Duration:** 1 session  
**Priority:** MEDIUM  
**Dependencies:** Sprint 6 complete

#### Tasks
1. **Clean Debug Scripts** (20 min)
   - Review root-level `debug_*.py` scripts
   - Delete obsolete ones
   - Move remaining to `tools/` or `dev/`
   - Create `tools/README.md`

2. **Remove Compatibility Shims** (15 min)
   - Delete root `InitGui.py` (compatibility shim)
   - Update installation docs
   - FreeCAD 1.2+ doesn't need it

3. **Architecture Documentation** (45 min)
   - Create `docs/ARCHITECTURE.md`
   - Document module structure
   - Explain design decisions
   - Include diagrams (text-based is fine)

4. **Performance Review** (30 min)
   - Profile critical operations
   - Optimize if needed
   - Document any known performance considerations

5. **Final Test Suite** (30 min)
   - Achieve >80% code coverage
   - Integration tests for all workflows
   - UI tests (if possible)
   - Manual testing checklist

6. **Release Preparation** (30 min)
   - Update `package.xml` to v1.0.0
   - Write comprehensive `CHANGELOG.md`
   - Update README with v1.0 features
   - Create release notes

**Deliverables:**
- ✅ Clean project root
- ✅ Comprehensive documentation
- ✅ >80% test coverage
- ✅ Release v1.0.0 ready
- ✅ Production-ready addon

---

## Architecture Targets

### Final Directory Structure
```
GitPDM/                          # Root
├── package.xml                  # FreeCAD addon metadata
├── pyproject.toml               # Python project config
├── README.md                    # User documentation
├── LICENSE                      # MIT license
├── CHANGELOG.md                 # Version history
│
├── freecad/                     # FreeCAD namespace
│   └── gitpdm/                  # Addon namespace
│       ├── __init__.py          # Package init
│       ├── init_gui.py          # Workbench registration
│       ├── workbench.py         # Workbench class
│       ├── commands.py          # FreeCAD commands
│       │
│       ├── core/                # Core functionality
│       │   ├── __init__.py
│       │   ├── fcstd_tool.py    # FCStd compression/decompression
│       │   ├── lock_manager.py  # File locking (git-lfs)
│       │   ├── config_manager.py # Configuration
│       │   ├── config_migration.py # OLD config migration
│       │   ├── paths.py         # Path utilities
│       │   ├── log.py           # Logging
│       │   ├── result.py        # Result type
│       │   └── ...
│       │
│       ├── git/                 # Git operations
│       │   ├── client.py        # Git client wrapper
│       │   ├── hooks.py         # Git hooks
│       │   └── hooks_manager.py
│       │
│       ├── github/              # GitHub integration
│       │   ├── api_client.py    # GitHub API
│       │   ├── repos.py         # Repository ops
│       │   └── ...
│       │
│       ├── ui/                  # User interface
│       │   ├── panel.py         # Main panel
│       │   ├── lock_panel.py    # Lock UI (renamed)
│       │   ├── init_wizard.py   # Init wizard (renamed)
│       │   ├── config_dialog.py # Config UI (renamed)
│       │   ├── new_repo_wizard.py
│       │   └── ...
│       │
│       ├── export/              # Export functionality
│       │   ├── exporter.py      # Main exporter
│       │   ├── stl_converter.py
│       │   ├── thumbnail.py
│       │   └── ...
│       │
│       ├── auth/                # Authentication
│       │   └── ...
│       │
│       └── Resources/           # Resources
│           └── Icons/
│
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md          # NEW: Architecture overview
│   ├── GITCAD_MIGRATION.md      # NEW: GitCAD history
│   ├── LEGACY_GITCAD_REPOS.md   # NEW: Legacy support
│   └── ...
│
├── tests/                       # Test suite
│   ├── core/
│   ├── ui/
│   └── integration/
│
└── tools/                       # NEW: Dev tools
    ├── README.md
    └── debug scripts (moved here)
```

### Removed/Consolidated
- ❌ `GitCAD-main/` (entire directory)
- ❌ `FreeCAD_Automation/` (entire directory)
- ❌ `freecad/gitpdm/gitcad/` (wrapper layer)
- ❌ `InitGui.py` (root compatibility shim)
- ❌ `install_gitcad.py` (obsolete install script)
- ❌ Most `debug_*.py` scripts (moved to tools/)

---

## Testing Strategy

### Test Coverage Goals
- **Core modules:** 90%+ (critical path)
- **UI components:** 60%+ (Qt testing is hard)
- **Integration:** 80%+ (workflow tests)
- **Overall:** 80%+

### Test Types
1. **Unit Tests**
   - Every core module function
   - Mock external dependencies (git, file system where possible)

2. **Integration Tests**
   - Full workflows (init → commit → push)
   - Config migration
   - Lock operations

3. **UI Tests** (limited)
   - Widget creation doesn't crash
   - Basic interactions
   - Full E2E testing may require manual QA

4. **Regression Tests**
   - Test backward compatibility scenarios
   - Config migration
   - Repos initialized with old GitCAD

---

## Risk Assessment

### High Risk
1. **Breaking existing GitCAD repos** 🔴
   - **Mitigation:** Config migration utility, legacy documentation
   - **Plan:** Detect old format, migrate automatically

2. **UI regressions** 🔴
   - **Mitigation:** Thorough testing, incremental changes
   - **Plan:** Test each sprint deliverable before moving on

### Medium Risk
3. **Performance degradation** 🟡
   - **Mitigation:** Profile before/after, benchmarks
   - **Plan:** Sprint 7 performance review

4. **Missing functionality** 🟡
   - **Mitigation:** Audit wrapper functions, ensure all ported
   - **Plan:** Comprehensive integration tests

### Low Risk
5. **Documentation gaps** 🟢
   - **Mitigation:** Review each sprint, update docs in parallel

---

## Success Metrics

### Technical
- ✅ Zero bash subprocess calls (except git/git-lfs)
- ✅ Single directory structure (no nested repos)
- ✅ <5% code duplication
- ✅ 80%+ test coverage
- ✅ No deprecated warnings in code

### User Experience
- ✅ Same or better performance vs current
- ✅ All existing features work
- ✅ Smooth migration path for GitCAD users
- ✅ Clear, comprehensive documentation

### Maintainability
- ✅ Single responsibility per module
- ✅ Clear dependency graph
- ✅ Consistent naming conventions
- ✅ Comprehensive inline documentation

---

## Intern Task Assignments

### Sprint 3 (GitCAD-main Removal)
- **Intern A:** Documentation extraction & merge
- **Intern B:** File deletion & reference cleanup
- **Both:** Testing & verification

### Sprint 4 (FreeCAD_Automation Removal)
- **Intern A:** Config migration utility
- **Intern B:** Legacy documentation
- **Both:** Testing & verification

### Sprint 5 (Wrapper Removal)
- **Intern A:** UI component migration (lock_panel, init_wizard)
- **Intern B:** Export integration cleanup & config_dialog
- **Both:** Testing & verification

### Sprint 6 (Standardization)
- **Intern A:** Naming convention cleanup
- **Intern B:** Documentation updates
- **Both:** Code review

### Sprint 7 (Polish & Release)
- **Intern A:** Debug scripts cleanup, architecture docs
- **Intern B:** Testing & coverage improvements
- **Both:** Release preparation

---

## Timeline Estimate

- **Sprint 3:** 2 hours
- **Sprint 4:** 3 hours (2 sessions)
- **Sprint 5:** 3 hours (2 sessions)
- **Sprint 6:** 1.5 hours
- **Sprint 7:** 2.5 hours

**Total:** ~12 hours of work (6 work sessions)

**Calendar:** 2-3 days with focused work

---

## Notes for Interns

### What You Did Right ✅
- **GitPDM Team:** Excellent UI/UX design, clean Qt6 implementation
- **GitCAD Team:** Solid core logic, good file compression strategy
- **Sprint 1:** Great start on native Python port, good test coverage

### What Went Wrong ❌
- **No communication:** Could have saved months of duplicate work
- **Wrapper approach:** Added complexity instead of true integration
- **Nested repo:** GitCAD-main should never have been a subdirectory
- **Bash dependency:** Made cross-platform support harder

### Lessons Learned 📚
1. **Communication is critical** - Regular sync meetings prevent duplication
2. **Architecture first** - Should have designed unified structure before coding
3. **Incremental integration** - Wrap-and-pray doesn't work, need true merge
4. **Technical debt** - Quick fixes (wrapper) create long-term problems

### Your Redemption Arc 🎯
This consolidation plan is your chance to:
- Learn proper software architecture
- Practice refactoring at scale
- Build something truly production-ready
- Ship a v1.0 you'll be proud of

**You can do this!** Follow the sprints, communicate often, test thoroughly.

---

## Appendix A: Module Dependency Graph

### Current (Sprint 2)
```
UI Components
    ↓ (imports)
gitcad/wrapper.py ← DEPRECATED
    ↓ (subprocess)
bash scripts ← TO BE REMOVED
    ↓
FCStdFileTool.py ← OBSOLETE
```

### Target (Sprint 7)
```
UI Components
    ↓ (direct imports)
core/fcstd_tool.py
core/lock_manager.py
core/config_manager.py
    ↓
Python standard library + git/git-lfs
```

### Migration Path
```
Sprint 3: Remove GitCAD-main source
Sprint 4: Remove FreeCAD_Automation (bash layer)
Sprint 5: Remove gitcad/ wrapper
Sprint 6: Standardize & polish
Sprint 7: Release v1.0
```

---

## Appendix B: File Deletion Checklist

### Sprint 3 Deletions
- [ ] `GitCAD-main/` (entire directory)
- [ ] `install_gitcad.py`

### Sprint 4 Deletions
- [ ] `FreeCAD_Automation/` (entire directory)

### Sprint 5 Deletions
- [ ] `freecad/gitpdm/gitcad/` (entire directory)

### Sprint 7 Deletions
- [ ] `InitGui.py` (root compatibility shim)
- [ ] Obsolete `debug_*.py` scripts

---

## Appendix C: References

- **FreeCAD 1.2 Template:** `/reference/Addon-Template-Latest/`
- **Sprint 1 Report:** `/docs/SPRINT_1_COMPLETE.md`
- **Migration Plan:** `/FREECAD_1_2_MIGRATION_PLAN.md`
- **GitCAD Original:** `/GitCAD-main/README.md`
- **GitPDM README:** `/README.md`

---

## Questions for Review

Before proceeding with Sprint 3:

1. **Config location:** Should we use `.gitpdm/config.json` or project root?
2. **Git hooks:** Do we ship hooks for new repos, or document only?
3. **Legacy repos:** How aggressive should migration utility be?
4. **Version bump:** v1.0 or v2.0 for consolidated release?
5. **Documentation:** Keep GitCAD docs for history, or just migration guide?

---

**READY TO PROCEED WITH SPRINT 3** ✅

