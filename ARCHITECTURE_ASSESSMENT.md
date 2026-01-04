# GitPDM + GitCAD Architecture Assessment & Consolidation Plan

**Date:** January 3, 2026  
**Status:** Architectural Refactoring Required  
**Prepared by:** Senior FreeCAD Developer

---

## Executive Summary

Two intern projects—**GitCAD** and **GitPDM**—were developed independently to solve similar problems: integrating Git workflows with FreeCAD. The result is a fragmented codebase with:

- **GitCAD**: Strong core logic for FCStd file handling, git hooks, and locking mechanisms (bash-based)
- **GitPDM**: Excellent UX/GUI using Qt, GitHub integration, and Python-based workflows

The interns attempted a quick merge by wrapping GitCAD with Python interfaces, resulting in:
- Duplication of the `FreeCAD_Automation` directory
- Unnecessary wrapper layer introducing complexity
- Mixed paradigms (bash scripts + Python)
- Unclear separation of concerns
- Technical debt from rushed integration

**Recommendation:** Consolidate into a single unified project that preserves GitCAD's proven file handling logic while leveraging GitPDM's superior UI/UX.

---

## Current Architecture Analysis

### Project Structure (As-Is)

```
GitPDM/
├── freecad_gitpdm/              # GitPDM Python package (UI/UX focused)
│   ├── ui/                       # Qt-based GUI (strong)
│   │   ├── panel.py             # Main dock panel (2592 lines!)
│   │   ├── github_auth.py       # OAuth device flow
│   │   ├── file_browser.py      # File browser widget
│   │   ├── gitcad_*.py          # GitCAD UI adapters (wrapper UI)
│   │   └── ...
│   ├── gitcad/                  # Wrapper around GitCAD bash scripts
│   │   ├── wrapper.py           # Subprocess executor for bash (564 lines)
│   │   ├── config.py            # Config parser
│   │   └── detector.py          # Status detection
│   ├── git/                     # Git operations (Python)
│   │   └── client.py            # Git command executor
│   ├── github/                  # GitHub API integration
│   ├── export/                  # Export/publish logic
│   │   ├── gitcad_integration.py # Bridge to GitCAD wrapper
│   │   └── ...
│   ├── auth/                    # Multi-platform token storage
│   └── core/                    # Logging, settings, jobs
│
├── FreeCAD_Automation/          # GitCAD bash scripts (COPY 1)
│   ├── FCStdFileTool.py         # Core FCStd handler (598 lines)
│   ├── hooks/                   # Git hooks (strong)
│   ├── git_aliases/             # Lock/unlock scripts
│   └── config.json
│
├── GitCAD-main/                 # Original GitCAD project (COPY 2)
│   ├── FreeCAD_Automation/      # DUPLICATE of above
│   │   ├── FCStdFileTool.py     # Same tool
│   │   ├── hooks/
│   │   └── ...
│   └── README.md                # GitCAD documentation
│
├── InitGui.py                   # FreeCAD workbench registration
└── pyproject.toml
```

### Key Issues Identified

#### 1. **Duplication (High Priority)**
- `FreeCAD_Automation/` exists in TWO places (root and `GitCAD-main/`)
- `FCStdFileTool.py` duplicated
- Git hooks duplicated
- Config files duplicated
- No clear "source of truth"

#### 2. **Wrapper Complexity (High Priority)**
- `freecad_gitpdm/gitcad/wrapper.py` is 564 lines of subprocess management
- Wraps bash scripts that call Python (`FCStdFileTool.py`)
- Python → Bash → Python call chain is inefficient
- Platform-specific bash detection adds fragility
- Error handling across process boundaries

#### 3. **Mixed Paradigms (Medium Priority)**
- GitCAD: Bash scripts + Git hooks + Python tool
- GitPDM: Pure Python with Qt GUI
- No unified language strategy
- Hard to test, debug, and maintain

#### 4. **Monolithic UI (Medium Priority)**
- `panel.py` is 2592 lines (should be <500)
- `git/client.py` is close to 2000 lines
- Violates single responsibility principle
- Hard to refactor or extend

#### 5. **Unclear Module Boundaries (Low Priority)**
- `export/gitcad_integration.py` bridges to wrapper
- UI has GitCAD-specific dialogs scattered around
- Core logic mixed with UI concerns

---

## Architectural Strengths to Preserve

### From GitCAD
✅ **FCStdFileTool.py** - Proven compression/decompression logic  
✅ **Git Hooks** - Automatic import/export on git operations  
✅ **Locking Mechanism** - LFS-based file locking (via lockfiles)  
✅ **Configuration System** - Flexible `config.json` structure  
✅ **Documentation** - Clear README with installation guide

### From GitPDM
✅ **Qt GUI** - Professional dock panel interface  
✅ **GitHub Integration** - OAuth device flow, API client  
✅ **Multi-platform Support** - Windows/Linux/macOS token stores  
✅ **Service Architecture** - Dependency injection pattern  
✅ **Job Runner** - Qt-based async task execution  
✅ **Git Client** - Python-based git operations  
✅ **Export System** - Manifest generation, STL conversion

---

## Consolidation Strategy

### Guiding Principles

1. **Python-First**: Eliminate bash wrapper, use Python directly
2. **Preserve GitCAD Logic**: Keep proven FCStd handling
3. **Keep GitPDM UX**: Maintain Qt GUI and workflows
4. **Modular Architecture**: Clear separation of concerns
5. **Single Source of Truth**: One `FreeCAD_Automation` location
6. **Testable**: Unit tests for core logic
7. **Incremental**: Phased rollout with validation gates

### Target Architecture (To-Be)

```
freecad_gitpdm/                   # Single unified package
├── ui/                           # GUI layer (keep from GitPDM)
│   ├── panel.py                 # Refactored <500 lines
│   ├── github_auth.py
│   ├── file_browser.py
│   ├── lock_manager.py          # NEW: Dedicated lock UI
│   └── settings_dialog.py       # NEW: Unified settings
│
├── core/                         # Business logic (Python-only)
│   ├── fcstd_tool.py            # MIGRATED from FCStdFileTool.py
│   ├── lock_manager.py          # NEW: Python lock implementation
│   ├── hooks_manager.py         # NEW: Git hooks installer
│   ├── git_client.py            # MOVED from git/client.py
│   ├── config.py                # Unified config management
│   ├── services.py              # Keep DI container
│   └── ...
│
├── github/                       # GitHub API (keep)
├── auth/                         # Token storage (keep)
├── export/                       # Export/publish (refactored)
│   └── exporter.py              # No more gitcad_integration.py
│
└── automation/                   # NEW: GitCAD hooks & scripts
    ├── hooks/                    # Git hooks (Python-ified)
    ├── config.json              # Default config template
    └── install.py               # Hook installer

FreeCAD_Automation/              # REMOVED (consolidated into package)
GitCAD-main/                     # REMOVED (documentation archived)
```

### Key Changes

1. **Eliminate Wrapper Layer**: Direct Python implementation of GitCAD logic
2. **Port FCStdFileTool.py**: Refactor into `core/fcstd_tool.py` module
3. **Python Git Hooks**: Convert bash hooks to Python (via `git config core.hooksPath`)
4. **Unified Config**: Single configuration system for all features
5. **Refactor panel.py**: Break into smaller, focused UI components
6. **Remove Duplication**: Single source for all GitCAD functionality

---

## Sprint Plan Overview

### Sprint 0: Foundation & Planning (2-3 days)
- Architecture review (this document)
- Team alignment on approach
- Set up feature flags for parallel work
- Create test suite for critical paths

### Sprint 1: Core Logic Migration (5-7 days)
- Port `FCStdFileTool.py` to Python module
- Extract lock logic from bash to Python
- Create `fcstd_tool.py` and `lock_manager.py`
- Unit tests for core functionality

### Sprint 2: Hook Modernization (3-5 days)
- Convert bash hooks to Python
- Create `hooks_manager.py`
- Install hooks via `git config`
- Test hook execution

### Sprint 3: Wrapper Elimination (3-4 days)
- Replace `gitcad/wrapper.py` calls with direct Python
- Update `export/` module to use new core
- Remove subprocess dependencies
- Integration testing

### Sprint 4: UI Refactoring (5-7 days)
- Split `panel.py` into components
- Create dedicated lock UI
- Update settings dialog
- Polish user experience

### Sprint 5: Cleanup & Documentation (3-4 days)
- Remove `GitCAD-main/` directory
- Consolidate `FreeCAD_Automation/`
- Update all documentation
- Final testing and validation

### Sprint 6: Polish & Release (2-3 days)
- Performance optimization
- User acceptance testing
- Release notes
- Community communication

---

## Risk Assessment

### High Risk
⚠️ **Breaking Existing Workflows**: Users may have GitCAD repos configured  
   *Mitigation*: Migration script, backward compatibility mode

⚠️ **FCStd Logic Bugs**: Porting Python tool could introduce regressions  
   *Mitigation*: Comprehensive test suite, parallel validation

### Medium Risk
⚠️ **Performance Degradation**: Python vs bash performance difference  
   *Mitigation*: Profile critical paths, optimize hot spots

⚠️ **Git Hook Compatibility**: Platform differences in hook execution  
   *Mitigation*: Test on Windows/Linux/macOS

### Low Risk
⚠️ **UI Breakage**: Refactoring panel could break workflows  
   *Mitigation*: Feature flags, gradual rollout

---

## Success Metrics

1. **Code Reduction**: Target 30% reduction in total LOC
2. **Test Coverage**: >80% coverage for core modules
3. **Performance**: No regression in FCStd operations (<10% variance)
4. **User Experience**: All existing GitPDM workflows still function
5. **Maintainability**: Single developer can understand any module in <30 minutes
6. **Documentation**: Every public API documented with examples

---

## Next Steps

1. **Review this assessment** with the team
2. **Approve consolidation strategy**
3. **Assign sprint leads**
4. **Begin Sprint 1** (Core Logic Migration)
5. **Daily standups** to track progress
6. **Weekly demos** to stakeholders

---

## Appendix: Detailed Module Responsibilities

### `core/fcstd_tool.py`
- Compress/decompress FCStd files
- Handle binary compression (brp files)
- Thumbnail extraction
- Configuration-driven behavior

### `core/lock_manager.py`
- Lock/unlock FCStd files via LFS
- Query lock status
- Handle force lock/unlock
- Integration with git client

### `core/hooks_manager.py`
- Install git hooks to repository
- Configure hook behavior
- Update hooks on config change
- Validate hook installation

### `ui/lock_manager.py`
- Display locked files
- Lock/unlock UI controls
- Visual lock indicators
- Conflict resolution UI

### `automation/hooks/`
- Python-based git hooks
- pre-commit: Export FCStd to uncompressed
- post-checkout: Import FCStd from uncompressed
- post-merge: Handle merge conflicts
- All hooks executable via Python

---

**End of Assessment**

*This document will be updated as the consolidation progresses.*
