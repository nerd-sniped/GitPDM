# Sprint 1: Core Logic Migration

**Duration:** 5-7 days  
**Goal:** Port GitCAD's FCStdFileTool.py and locking logic from bash/subprocess to native Python modules

---

## Overview

This sprint eliminates the most critical technical debt: the subprocess-based wrapper around GitCAD's bash scripts. We'll extract and refactor the proven FCStd handling logic into clean, testable Python modules.

## Objectives

✅ Port `FCStdFileTool.py` to `freecad_gitpdm/core/fcstd_tool.py`  
✅ Extract lock/unlock logic into `freecad_gitpdm/core/lock_manager.py`  
✅ Create comprehensive unit tests  
✅ Validate no regressions in functionality  
✅ Maintain backward compatibility during transition

---

## Task Breakdown

### Task 1.1: Analyze FCStdFileTool.py Dependencies
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P0 (Blocking)

**Description:**
Thoroughly analyze the current `FreeCAD_Automation/FCStdFileTool.py` to understand:
- All dependencies (freecad.project_utility, zipfile, etc.)
- Configuration inputs from config.json
- Edge cases and error handling
- Platform-specific behaviors (Linux vs Windows)

**Deliverables:**
- [ ] Dependency map document
- [ ] List of all config.json keys used
- [ ] Edge case documentation
- [ ] Test data requirements

**Acceptance Criteria:**
- All imports documented
- All config keys mapped
- Known bugs/workarounds identified

---

### Task 1.2: Create Core Module Structure
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P0 (Blocking)

**Description:**
Set up the new module structure with proper Python packaging:

```python
freecad_gitpdm/core/
├── __init__.py              # Export public API
├── fcstd_tool.py            # FCStd compress/decompress
├── lock_manager.py          # File locking logic
├── config_manager.py        # Unified configuration
└── tests/
    ├── test_fcstd_tool.py
    ├── test_lock_manager.py
    └── fixtures/
```

**Deliverables:**
- [ ] Directory structure created
- [ ] Empty module files with docstrings
- [ ] Test directory with pytest setup
- [ ] Updated `__init__.py` exports

**Acceptance Criteria:**
- Modules importable: `from freecad_gitpdm.core import fcstd_tool`
- Pytest discovers test files
- No circular dependencies

---

### Task 1.3: Port FCStd Compression Logic
**Owner:** [Assign]  
**Estimate:** 2 days  
**Priority:** P0 (Blocking)

**Description:**
Refactor `FCStdFileTool.py` export/import functions into clean Python module:

**Key Functions to Port:**
1. `export_fcstd(fcstd_path, output_dir, config)` - Decompress FCStd to directory
2. `import_fcstd(input_dir, fcstd_path, config)` - Compress directory to FCStd
3. `compress_binaries(files, config)` - Handle .brp file compression
4. `extract_thumbnail(fcstd_path, output_path)` - Thumbnail extraction
5. `get_uncompressed_dir_path(fcstd_path, config)` - Calculate output directory

**Refactoring Guidelines:**
- Use pathlib.Path instead of string paths
- Replace global state with function parameters
- Extract config parsing to separate module
- Add type hints
- Improve error messages
- Add logging via `freecad_gitpdm.core.log`

**Before (FCStdFileTool.py style):**
```python
def export_fcstd_file(INPUT_FCSTD_FILE:str, OUTPUT_FCSTD_DIR:str, config:dict):
    # Global state, poor error handling
    ...
```

**After (fcstd_tool.py style):**
```python
from pathlib import Path
from typing import Optional
from freecad_gitpdm.core.result import Result
from freecad_gitpdm.core import log

def export_fcstd(
    fcstd_path: Path,
    output_dir: Optional[Path] = None,
    config: Optional[dict] = None
) -> Result:
    """
    Decompress a .FCStd file to an uncompressed directory structure.
    
    Args:
        fcstd_path: Path to the .FCStd file
        output_dir: Target directory (auto-calculated if None)
        config: Configuration dict (loads default if None)
        
    Returns:
        Result with output_dir path on success, error on failure
    """
    try:
        config = config or load_default_config()
        output_dir = output_dir or calculate_output_dir(fcstd_path, config)
        
        log.info(f"Exporting {fcstd_path} to {output_dir}")
        
        # Implementation...
        
        return Result.success(str(output_dir))
    except Exception as e:
        log.error(f"Export failed: {e}")
        return Result.failure("EXPORT_ERROR", str(e))
```

**Deliverables:**
- [ ] `fcstd_tool.py` with all core functions
- [ ] Type hints on all public functions
- [ ] Docstrings with examples
- [ ] Error handling via Result pattern
- [ ] Logging at appropriate levels

**Acceptance Criteria:**
- All functions ported and working
- No bash subprocess calls
- Passes manual testing with sample FCStd files
- Code review approved

---

### Task 1.4: Port Lock Management Logic
**Owner:** [Assign]  
**Estimate:** 1.5 days  
**Priority:** P0 (Blocking)

**Description:**
Extract file locking logic from bash scripts into Python module:

**Key Functions:**
1. `lock_file(repo_root, fcstd_path, force=False)` - Lock a file via LFS
2. `unlock_file(repo_root, fcstd_path, force=False)` - Unlock a file
3. `get_locks(repo_root)` - Query all locks in repository
4. `is_locked(repo_root, fcstd_path)` - Check if file is locked
5. `get_lock_owner(repo_root, fcstd_path)` - Get lock owner info

**Current Implementation (bash in lock.sh):**
```bash
#!/bin/bash
# Locks .lockfile in uncompressed directory
git lfs lock "$uncompressed_dir/.lockfile"
```

**New Implementation (Python):**
```python
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
from freecad_gitpdm.core.result import Result
from freecad_gitpdm.core import log
from freecad_gitpdm.git.client import GitClient

@dataclass
class LockInfo:
    """Information about a locked file."""
    fcstd_path: str
    lockfile_path: str
    owner: str
    lock_id: str
    locked_at: str

class LockManager:
    """Manages file locking using Git LFS."""
    
    def __init__(self, repo_root: Path, git_client: Optional[GitClient] = None):
        self.repo_root = Path(repo_root)
        self.git_client = git_client or GitClient()
        
    def lock_file(self, fcstd_path: str, force: bool = False) -> Result:
        """
        Lock a .FCStd file by locking its .lockfile.
        
        Args:
            fcstd_path: Relative path to .FCStd file
            force: Force lock (steal from other user)
            
        Returns:
            Result with lock info on success
        """
        try:
            # Calculate lockfile path
            lockfile = self._get_lockfile_path(fcstd_path)
            
            log.info(f"Locking {fcstd_path} via {lockfile}")
            
            # Call git lfs lock via git client
            args = ["lfs", "lock", str(lockfile)]
            if force:
                args.append("--force")
                
            result = self.git_client.run_command(self.repo_root, args)
            
            if result.ok:
                return Result.success(f"Locked: {fcstd_path}")
            else:
                return Result.failure("LOCK_ERROR", result.error.message)
                
        except Exception as e:
            log.error(f"Lock failed: {e}")
            return Result.failure("LOCK_ERROR", str(e))
    
    def _get_lockfile_path(self, fcstd_path: str) -> Path:
        """Calculate the .lockfile path for a .FCStd file."""
        # Load config and calculate uncompressed dir
        from freecad_gitpdm.core.config_manager import get_uncompressed_dir
        uncompressed_dir = get_uncompressed_dir(self.repo_root, fcstd_path)
        return uncompressed_dir / ".lockfile"
```

**Deliverables:**
- [ ] `lock_manager.py` with LockManager class
- [ ] Integration with existing GitClient
- [ ] Type-safe LockInfo dataclass
- [ ] Comprehensive error handling
- [ ] Logging

**Acceptance Criteria:**
- Can lock/unlock files via Python API
- No subprocess calls to bash scripts
- Works with GitPDM's git client
- Matches bash script behavior exactly

---

### Task 1.5: Configuration Management Refactor
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P1

**Description:**
Unify configuration management between GitCAD and GitPDM:

**Current State:**
- GitCAD: `FreeCAD_Automation/config.json`
- GitPDM: `freecad_gitpdm/core/settings.py` (Qt-based)
- GitPDM: `freecad_gitpdm/gitcad/config.py` (GitCAD parser)

**Goal:**
- Single configuration system that handles both
- Backward compatible with existing config.json
- Integrates with GitPDM settings storage

**Implementation:**
```python
# freecad_gitpdm/core/config_manager.py

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import json

@dataclass
class FCStdConfig:
    """Configuration for FCStd file handling."""
    uncompressed_suffix: str = "_uncompressed"
    uncompressed_prefix: str = ""
    subdirectory_mode: bool = False
    subdirectory_name: str = ".freecad_data"
    include_thumbnails: bool = False
    compress_binaries: bool = True
    binary_patterns: list = None
    compression_level: int = 6
    require_lock: bool = True
    
    def __post_init__(self):
        if self.binary_patterns is None:
            self.binary_patterns = ["*.brp", "*.Map.*", "no_extension/*"]

def load_config(repo_root: Path) -> FCStdConfig:
    """Load config from FreeCAD_Automation/config.json or defaults."""
    config_file = repo_root / "FreeCAD_Automation" / "config.json"
    
    if not config_file.exists():
        return FCStdConfig()  # Defaults
        
    with open(config_file) as f:
        data = json.load(f)
        
    # Parse GitCAD format to our format
    return FCStdConfig(
        uncompressed_suffix=data["uncompressed-directory-structure"]["uncompressed-directory-suffix"],
        # ... map all fields
    )

def get_uncompressed_dir(repo_root: Path, fcstd_path: str, config: Optional[FCStdConfig] = None) -> Path:
    """Calculate the uncompressed directory path for a .FCStd file."""
    config = config or load_config(repo_root)
    
    fcstd_path = Path(fcstd_path)
    base_name = fcstd_path.stem  # filename without .FCStd
    
    # Apply prefix/suffix
    dir_name = f"{config.uncompressed_prefix}{base_name}{config.uncompressed_suffix}"
    
    # Handle subdirectory mode
    if config.subdirectory_mode:
        return fcstd_path.parent / config.subdirectory_name / dir_name
    else:
        return fcstd_path.parent / dir_name
```

**Deliverables:**
- [ ] Unified `config_manager.py` module
- [ ] FCStdConfig dataclass
- [ ] Backward compatible with config.json
- [ ] Migration from gitcad/config.py

**Acceptance Criteria:**
- Existing config.json files load correctly
- Default config works without file
- Type-safe configuration access

---

### Task 1.6: Create Test Suite
**Owner:** [Assign]  
**Estimate:** 2 days  
**Priority:** P0 (Blocking)

**Description:**
Create comprehensive unit tests for new core modules:

**Test Files:**
- `test_fcstd_tool.py` - FCStd compression/decompression
- `test_lock_manager.py` - Locking operations
- `test_config_manager.py` - Configuration loading

**Test Coverage Requirements:**
- Export FCStd to directory
- Import directory to FCStd
- Binary file compression
- Thumbnail extraction
- Lock file (success)
- Lock file (already locked)
- Lock file (force)
- Unlock file
- Get all locks
- Config loading (with file)
- Config loading (defaults)
- Uncompressed dir calculation

**Test Fixtures:**
```
tests/fixtures/
├── sample.FCStd           # Small test file
├── sample_uncompressed/   # Expected output
├── config_minimal.json    # Minimal config
└── config_full.json       # Full config
```

**Example Test:**
```python
# tests/core/test_fcstd_tool.py

import pytest
from pathlib import Path
from freecad_gitpdm.core import fcstd_tool
from freecad_gitpdm.core.config_manager import FCStdConfig

def test_export_fcstd_creates_directory(tmp_path):
    """Test that export creates uncompressed directory."""
    # Setup
    fcstd_file = tmp_path / "test.FCStd"
    create_sample_fcstd(fcstd_file)  # Helper
    
    config = FCStdConfig()
    
    # Execute
    result = fcstd_tool.export_fcstd(fcstd_file, config=config)
    
    # Assert
    assert result.ok
    output_dir = Path(result.value)
    assert output_dir.exists()
    assert (output_dir / "Document.xml").exists()

def test_export_fcstd_handles_missing_file(tmp_path):
    """Test error handling for missing file."""
    fcstd_file = tmp_path / "missing.FCStd"
    
    result = fcstd_tool.export_fcstd(fcstd_file)
    
    assert not result.ok
    assert "not found" in result.error.message.lower()
```

**Deliverables:**
- [ ] Test suite with >80% coverage
- [ ] Test fixtures for FCStd files
- [ ] Test utilities for setup/teardown
- [ ] Integration with pytest
- [ ] CI-ready (can run in GitHub Actions)

**Acceptance Criteria:**
- All tests pass
- Coverage >80% on new modules
- Tests are fast (<30 seconds total)
- No external dependencies (git not required for unit tests)

---

### Task 1.7: Integration with Existing GitPDM
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P1

**Description:**
Wire up new core modules to existing GitPDM code paths (parallel to old wrapper):

**Integration Points:**
1. `export/exporter.py` - Use new fcstd_tool
2. `ui/panel.py` - Wire lock UI to new lock_manager
3. `core/services.py` - Provide lock_manager via DI

**Feature Flag Approach:**
```python
# freecad_gitpdm/core/feature_flags.py
USE_NATIVE_FCSTD_TOOL = True  # Toggle for gradual rollout

# freecad_gitpdm/export/exporter.py
from freecad_gitpdm.core import feature_flags

def export_document(doc, path):
    if feature_flags.USE_NATIVE_FCSTD_TOOL:
        # New path
        from freecad_gitpdm.core import fcstd_tool
        return fcstd_tool.export_fcstd(path)
    else:
        # Old wrapper path (fallback)
        from freecad_gitpdm.export import gitcad_integration
        return gitcad_integration.gitcad_export_if_available(repo, path)
```

**Deliverables:**
- [ ] Feature flag system
- [ ] Parallel code paths (old + new)
- [ ] Updated service container
- [ ] Integration tests

**Acceptance Criteria:**
- Both old and new paths work
- Can toggle via feature flag
- No breaking changes to existing code

---

### Task 1.8: Validation & Documentation
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P1

**Description:**
Validate the migration and document usage:

**Validation Checklist:**
- [ ] Manual test: Export a .FCStd file
- [ ] Manual test: Import a .FCStd file
- [ ] Manual test: Lock a file
- [ ] Manual test: Unlock a file
- [ ] Manual test: View locks
- [ ] Compare output with old wrapper
- [ ] Performance benchmarks

**Documentation:**
- API documentation in docstrings
- Migration guide for developers
- Update ARCHITECTURE_ASSESSMENT.md

**Deliverables:**
- [ ] Validation report
- [ ] API documentation
- [ ] Migration notes

**Acceptance Criteria:**
- All validation tests pass
- Documentation complete
- Performance within 10% of old wrapper

---

## Definition of Done (Sprint 1)

- [x] All tasks completed
- [x] Test coverage >80%
- [x] No regressions vs. wrapper
- [x] Code review approved
- [x] Documentation updated
- [x] Integration tests pass
- [x] Ready for Sprint 2 (hooks)

---

## Risks & Mitigations

**Risk:** Subtle differences in FCStd handling cause data corruption  
**Mitigation:** Extensive testing with real FCStd files, byte-level comparison of outputs

**Risk:** Performance regression in compression  
**Mitigation:** Benchmark against old tool, optimize hot paths

**Risk:** Platform-specific bugs (Windows vs Linux)  
**Mitigation:** Test on both platforms, use pathlib for cross-platform paths

---

## Dependencies

- pytest installed
- Sample FCStd files for testing
- Access to git repository with LFS configured

---

## Success Metrics

- ✅ Zero subprocess calls to bash scripts for core FCStd operations
- ✅ >80% test coverage on new modules
- ✅ Performance within 10% of original tool
- ✅ All existing GitPDM workflows continue to work
- ✅ Code review approval from senior dev

---

**Next Sprint:** Sprint 2 - Hook Modernization (convert bash hooks to Python)
