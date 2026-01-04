# Sprint 2: Hook Modernization

**Duration:** 3-5 days  
**Goal:** Convert GitCAD's bash-based git hooks to Python for better maintainability and cross-platform support

---

## Overview

GitCAD uses bash scripts as git hooks to automatically import/export FCStd files during git operations. While effective, bash hooks have limitations:
- Requires bash on Windows (Git Bash dependency)
- Hard to test and debug
- Platform-specific issues
- Duplicates logic from FCStdFileTool.py

This sprint converts all hooks to Python, leveraging the new `fcstd_tool` module from Sprint 1.

## Objectives

✅ Convert all bash hooks to Python  
✅ Create `hooks_manager.py` for installation/configuration  
✅ Use new `core/fcstd_tool.py` directly (no subprocess)  
✅ Test hooks on Windows, Linux, macOS  
✅ Maintain backward compatibility with existing repos

---

## Current Hook Architecture

### Existing Bash Hooks (GitCAD)

```
FreeCAD_Automation/hooks/
├── pre-commit          # Export FCStd to uncompressed before commit
├── post-checkout       # Import FCStd from uncompressed after checkout
├── post-merge          # Import FCStd after merge
├── post-rewrite        # Import FCStd after rebase
└── pre-push            # Validate locks before push
```

**Hook Flow (Current):**
```
Git Operation → Bash Hook → FCStdFileTool.py (via subprocess) → FCStd I/O
```

**Hook Flow (Target):**
```
Git Operation → Python Hook → core/fcstd_tool.py (direct) → FCStd I/O
```

---

## Task Breakdown

### Task 2.1: Analyze Existing Hook Behavior
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P0 (Blocking)

**Description:**
Document the exact behavior of each bash hook:

**Hooks to Analyze:**
1. `pre-commit` - What files does it process? When does it skip?
2. `post-checkout` - How does it detect changed FCStd files?
3. `post-merge` - Conflict handling?
4. `post-rewrite` - Rebase handling?
5. `pre-push` - Lock validation logic?

**Deliverables:**
- [ ] Behavior document for each hook
- [ ] Edge cases identified
- [ ] Environment variables used
- [ ] Exit code meanings

**Acceptance Criteria:**
- All hook behaviors documented
- Edge cases cataloged
- Team reviews and approves

---

### Task 2.2: Create Python Hook Framework
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P0 (Blocking)

**Description:**
Create a reusable framework for Python-based git hooks:

```python
# freecad_gitpdm/automation/hook_base.py

import sys
from pathlib import Path
from abc import ABC, abstractmethod
from freecad_gitpdm.core import log, config_manager
from freecad_gitpdm.core.result import Result

class GitHook(ABC):
    """Base class for git hooks."""
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.config = config_manager.load_config(repo_root)
        
    @abstractmethod
    def run(self, *args) -> Result:
        """Execute the hook logic."""
        pass
        
    def execute(self, *args) -> int:
        """
        Execute hook and return git-compatible exit code.
        
        Returns:
            0 on success, 1 on failure
        """
        try:
            result = self.run(*args)
            if result.ok:
                log.info(f"{self.__class__.__name__} completed successfully")
                return 0
            else:
                log.error(f"{self.__class__.__name__} failed: {result.error.message}")
                return 1
        except Exception as e:
            log.error(f"{self.__class__.__name__} crashed: {e}")
            return 1

def find_repo_root() -> Path:
    """Find git repository root from current directory."""
    from freecad_gitpdm.git.client import GitClient
    client = GitClient()
    result = client.get_repo_root(Path.cwd())
    if not result.ok:
        raise RuntimeError("Not in a git repository")
    return Path(result.value)
```

**Deliverables:**
- [ ] `hook_base.py` with GitHook ABC
- [ ] Repository root detection
- [ ] Logging infrastructure
- [ ] Exit code handling

**Acceptance Criteria:**
- Base class is reusable
- Logging works from hook context
- Exit codes match git expectations

---

### Task 2.3: Implement Pre-Commit Hook
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P0 (Blocking)

**Description:**
Convert `pre-commit` bash hook to Python:

**Behavior (Current):**
- Runs before commit
- Exports staged .FCStd files to uncompressed directories
- Stages the uncompressed directories
- Aborts if export fails

**Python Implementation:**
```python
# freecad_gitpdm/automation/hooks/pre_commit.py

from pathlib import Path
from freecad_gitpdm.automation.hook_base import GitHook, find_repo_root
from freecad_gitpdm.core import fcstd_tool, log
from freecad_gitpdm.core.result import Result
from freecad_gitpdm.git.client import GitClient

class PreCommitHook(GitHook):
    """Export FCStd files to uncompressed before commit."""
    
    def __init__(self, repo_root: Path):
        super().__init__(repo_root)
        self.git_client = GitClient()
        
    def run(self) -> Result:
        """Execute pre-commit hook logic."""
        # Get list of staged .FCStd files
        staged_files = self._get_staged_fcstd_files()
        
        if not staged_files:
            log.debug("No FCStd files staged, skipping")
            return Result.success("No FCStd files to process")
            
        log.info(f"Processing {len(staged_files)} staged FCStd files")
        
        # Export each file
        for fcstd_file in staged_files:
            log.info(f"Exporting {fcstd_file}")
            
            result = fcstd_tool.export_fcstd(
                self.repo_root / fcstd_file,
                config=self.config
            )
            
            if not result.ok:
                return Result.failure(
                    "EXPORT_ERROR",
                    f"Failed to export {fcstd_file}: {result.error.message}"
                )
                
            # Stage the uncompressed directory
            uncompressed_dir = Path(result.value)
            relative_dir = uncompressed_dir.relative_to(self.repo_root)
            
            add_result = self.git_client.run_command(
                self.repo_root,
                ["add", str(relative_dir)]
            )
            
            if not add_result.ok:
                return Result.failure(
                    "GIT_ERROR",
                    f"Failed to stage {relative_dir}"
                )
                
        return Result.success(f"Exported {len(staged_files)} files")
        
    def _get_staged_fcstd_files(self) -> list[str]:
        """Get list of staged .FCStd files."""
        result = self.git_client.run_command(
            self.repo_root,
            ["diff", "--cached", "--name-only", "--diff-filter=ACM"]
        )
        
        if not result.ok:
            return []
            
        files = result.value.strip().split('\n')
        return [f for f in files if f.lower().endswith('.fcstd')]

def main():
    """Entry point for pre-commit hook."""
    repo_root = find_repo_root()
    hook = PreCommitHook(repo_root)
    return hook.execute()

if __name__ == "__main__":
    sys.exit(main())
```

**Hook Script (installed to .git/hooks/pre-commit):**
```python
#!/usr/bin/env python3
# Git pre-commit hook - managed by GitPDM
# Do not edit manually

import sys
from pathlib import Path

# Add freecad_gitpdm to path
# (Assume it's installed or in PYTHONPATH)
try:
    from freecad_gitpdm.automation.hooks.pre_commit import main
    sys.exit(main())
except ImportError as e:
    print(f"GitPDM hooks not found: {e}")
    print("Run 'git config core.hooksPath' to check hook configuration")
    sys.exit(1)
```

**Deliverables:**
- [ ] `pre_commit.py` with PreCommitHook class
- [ ] Staged file detection
- [ ] Export and staging logic
- [ ] Hook script template

**Acceptance Criteria:**
- Exports staged FCStd files
- Stages uncompressed directories
- Aborts commit on failure
- Matches bash behavior exactly

---

### Task 2.4: Implement Post-Checkout Hook
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P0 (Blocking)

**Description:**
Convert `post-checkout` bash hook to Python:

**Behavior:**
- Runs after checkout (branch switch, file restore)
- Imports changed .FCStd files from uncompressed directories
- Skips if no uncompressed dir exists

**Python Implementation:**
```python
# freecad_gitpdm/automation/hooks/post_checkout.py

from pathlib import Path
from freecad_gitpdm.automation.hook_base import GitHook, find_repo_root
from freecad_gitpdm.core import fcstd_tool, log
from freecad_gitpdm.core.result import Result

class PostCheckoutHook(GitHook):
    """Import FCStd files from uncompressed after checkout."""
    
    def run(self, prev_head: str, new_head: str, branch_flag: str) -> Result:
        """
        Execute post-checkout hook.
        
        Args:
            prev_head: Previous HEAD commit
            new_head: New HEAD commit
            branch_flag: '1' if checking out branch, '0' if file
        """
        # Get list of changed .FCStd files
        changed_files = self._get_changed_fcstd_files(prev_head, new_head)
        
        if not changed_files:
            return Result.success("No FCStd files changed")
            
        log.info(f"Importing {len(changed_files)} FCStd files")
        
        for fcstd_file in changed_files:
            # Check if uncompressed dir exists
            uncompressed_dir = self._get_uncompressed_dir(fcstd_file)
            if not uncompressed_dir.exists():
                log.debug(f"No uncompressed dir for {fcstd_file}, skipping")
                continue
                
            log.info(f"Importing {fcstd_file}")
            
            result = fcstd_tool.import_fcstd(
                uncompressed_dir,
                self.repo_root / fcstd_file,
                config=self.config
            )
            
            if not result.ok:
                log.warning(f"Import failed for {fcstd_file}: {result.error.message}")
                # Don't abort checkout, just warn
                
        return Result.success(f"Imported {len(changed_files)} files")
```

**Deliverables:**
- [ ] `post_checkout.py` with PostCheckoutHook class
- [ ] Changed file detection
- [ ] Import logic
- [ ] Hook script template

**Acceptance Criteria:**
- Imports after branch switch
- Handles missing uncompressed dirs gracefully
- Doesn't abort on import failure (just warns)

---

### Task 2.5: Implement Post-Merge Hook
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P1

**Description:**
Convert `post-merge` bash hook to Python. Similar to post-checkout but runs after merge operations.

**Deliverables:**
- [ ] `post_merge.py` with PostMergeHook class
- [ ] Merge conflict detection
- [ ] Hook script template

---

### Task 2.6: Implement Pre-Push Hook (Lock Validation)
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P1

**Description:**
Convert `pre-push` bash hook to validate file locks before push:

**Behavior:**
- Runs before push
- Checks if any committed .FCStd files are locked by others
- Aborts push if user doesn't own locks

**Python Implementation:**
```python
# freecad_gitpdm/automation/hooks/pre_push.py

from freecad_gitpdm.automation.hook_base import GitHook, find_repo_root
from freecad_gitpdm.core import log
from freecad_gitpdm.core.lock_manager import LockManager
from freecad_gitpdm.core.result import Result

class PrePushHook(GitHook):
    """Validate file locks before push."""
    
    def __init__(self, repo_root):
        super().__init__(repo_root)
        self.lock_manager = LockManager(repo_root)
        
    def run(self, remote: str, url: str) -> Result:
        """
        Execute pre-push validation.
        
        Args:
            remote: Remote name (e.g., 'origin')
            url: Remote URL
        """
        if not self.config.require_lock:
            log.debug("Lock validation disabled in config")
            return Result.success("Lock validation skipped")
            
        # Get list of FCStd files being pushed
        fcstd_files = self._get_pushed_fcstd_files()
        
        if not fcstd_files:
            return Result.success("No FCStd files in push")
            
        # Check locks
        locks = self.lock_manager.get_locks()
        current_user = self._get_git_user()
        
        violations = []
        for fcstd_file in fcstd_files:
            lock = self._find_lock_for_file(fcstd_file, locks)
            if lock and lock.owner != current_user:
                violations.append((fcstd_file, lock.owner))
                
        if violations:
            msg = "Cannot push: Files locked by others:\\n"
            for file, owner in violations:
                msg += f"  {file} (locked by {owner})\\n"
            msg += "\\nUnlock files or have owner push changes."
            return Result.failure("LOCK_VIOLATION", msg)
            
        return Result.success("All locks validated")
```

**Deliverables:**
- [ ] `pre_push.py` with PrePushHook class
- [ ] Lock validation logic
- [ ] Integration with LockManager (Sprint 1)
- [ ] Hook script template

**Acceptance Criteria:**
- Validates locks before push
- Aborts push if locked by others
- Clear error messages

---

### Task 2.7: Create Hooks Manager
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P0 (Blocking)

**Description:**
Create a manager for installing/updating Python hooks in repositories:

```python
# freecad_gitpdm/core/hooks_manager.py

from pathlib import Path
from typing import List
import shutil
from freecad_gitpdm.core import log
from freecad_gitpdm.core.result import Result

class HooksManager:
    """Manages git hook installation and configuration."""
    
    HOOKS = [
        "pre-commit",
        "post-checkout",
        "post-merge",
        "post-rewrite",
        "pre-push",
    ]
    
    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root)
        self.hooks_dir = self.repo_root / ".git" / "hooks"
        
    def install_hooks(self) -> Result:
        """Install all Python hooks to .git/hooks/."""
        if not self.hooks_dir.exists():
            return Result.failure("GIT_ERROR", "Not a git repository")
            
        log.info(f"Installing hooks to {self.hooks_dir}")
        
        for hook_name in self.HOOKS:
            result = self._install_hook(hook_name)
            if not result.ok:
                return result
                
        return Result.success(f"Installed {len(self.HOOKS)} hooks")
        
    def _install_hook(self, hook_name: str) -> Result:
        """Install a single hook."""
        hook_path = self.hooks_dir / hook_name
        
        # Backup existing hook
        if hook_path.exists():
            backup_path = hook_path.with_suffix(".backup")
            log.info(f"Backing up existing {hook_name} to {backup_path}")
            shutil.copy(hook_path, backup_path)
            
        # Write Python hook script
        hook_script = self._generate_hook_script(hook_name)
        hook_path.write_text(hook_script)
        hook_path.chmod(0o755)  # Make executable
        
        log.info(f"Installed {hook_name}")
        return Result.success(f"Installed {hook_name}")
        
    def _generate_hook_script(self, hook_name: str) -> str:
        """Generate Python hook script."""
        hook_module = hook_name.replace("-", "_")
        
        return f"""#!/usr/bin/env python3
# Git {hook_name} hook - managed by GitPDM
# Auto-generated - do not edit manually

import sys
from pathlib import Path

try:
    from freecad_gitpdm.automation.hooks.{hook_module} import main
    sys.exit(main())
except ImportError as e:
    print(f"GitPDM hooks not available: {{e}}")
    print("Ensure freecad_gitpdm is installed")
    sys.exit(0)  # Don't block git operations
except Exception as e:
    print(f"Hook error: {{e}}")
    sys.exit(1)
"""
    
    def uninstall_hooks(self) -> Result:
        """Remove all GitPDM hooks."""
        for hook_name in self.HOOKS:
            hook_path = self.hooks_dir / hook_name
            if hook_path.exists():
                # Check if it's our hook
                content = hook_path.read_text()
                if "managed by GitPDM" in content:
                    hook_path.unlink()
                    log.info(f"Removed {hook_name}")
                    
        return Result.success("Hooks uninstalled")
        
    def validate_hooks(self) -> Result:
        """Check if hooks are properly installed."""
        missing = []
        for hook_name in self.HOOKS:
            hook_path = self.hooks_dir / hook_name
            if not hook_path.exists():
                missing.append(hook_name)
                
        if missing:
            return Result.failure(
                "HOOKS_MISSING",
                f"Missing hooks: {', '.join(missing)}"
            )
            
        return Result.success("All hooks installed")
```

**Deliverables:**
- [ ] `hooks_manager.py` with HooksManager class
- [ ] Install/uninstall functionality
- [ ] Validation checking
- [ ] Backup of existing hooks

**Acceptance Criteria:**
- Can install all hooks with one call
- Backs up existing hooks
- Generates correct Python hook scripts
- Makes hooks executable

---

### Task 2.8: UI Integration
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P1

**Description:**
Add hook management to GitPDM UI:

**UI Changes:**
1. Add "Install Hooks" button to panel
2. Show hook status (installed/missing)
3. Settings dialog: Enable/disable hooks

**Implementation:**
```python
# freecad_gitpdm/ui/panel.py (add method)

def _install_hooks(self):
    """Install git hooks to current repository."""
    if not self._current_repo_root:
        dialogs.show_error("No Repository", "Please select a repository first")
        return
        
    from freecad_gitpdm.core.hooks_manager import HooksManager
    
    manager = HooksManager(self._current_repo_root)
    result = manager.install_hooks()
    
    if result.ok:
        dialogs.show_info("Hooks Installed", "Git hooks installed successfully")
        self._refresh_hook_status()
    else:
        dialogs.show_error("Installation Failed", result.error.message)
```

**Deliverables:**
- [ ] UI button for hook installation
- [ ] Status indicator in panel
- [ ] Settings integration

**Acceptance Criteria:**
- One-click hook installation from UI
- Visual feedback on hook status
- Error handling

---

### Task 2.9: Testing & Validation
**Owner:** [Assign]  
**Estimate:** 1 day  
**Priority:** P0 (Blocking)

**Description:**
Comprehensive testing of Python hooks:

**Test Scenarios:**
1. **Pre-commit:**
   - Stage .FCStd file → commit → verify export
   - Stage non-FCStd file → commit → no export
   - Export failure → commit aborted

2. **Post-checkout:**
   - Checkout branch with FCStd changes → verify import
   - Checkout without FCStd changes → no import
   - Missing uncompressed dir → graceful skip

3. **Pre-push:**
   - Push with locks owned by user → success
   - Push with locks owned by others → abort
   - Push with lock validation disabled → success

**Platform Testing:**
- Windows 10/11
- Ubuntu Linux
- macOS

**Test Fixture:**
```bash
# Create test repository
git init test-repo
cd test-repo

# Install hooks
python -c "from freecad_gitpdm.core.hooks_manager import HooksManager; HooksManager('.').install_hooks()"

# Test commit
cp sample.FCStd test.FCStd
git add test.FCStd
git commit -m "Test commit"  # Should trigger pre-commit hook
```

**Deliverables:**
- [ ] Automated test suite for hooks
- [ ] Manual test checklist
- [ ] Platform test report (Win/Linux/Mac)
- [ ] Performance benchmarks

**Acceptance Criteria:**
- All hook scenarios tested
- Behavior matches bash hooks
- Works on all platforms
- No performance regression

---

### Task 2.10: Documentation & Migration Guide
**Owner:** [Assign]  
**Estimate:** 0.5 days  
**Priority:** P1

**Description:**
Document the new Python hooks system:

**Documentation Needed:**
1. User guide: Installing hooks
2. Developer guide: Creating custom hooks
3. Migration guide: Bash → Python hooks
4. Troubleshooting guide

**Migration Guide:**
```markdown
# Migrating from Bash to Python Hooks

## For Existing GitCAD Users

If you have an existing repository with GitCAD bash hooks:

1. **Backup existing hooks:**
   ```bash
   cp -r .git/hooks .git/hooks.backup
   ```

2. **Install Python hooks:**
   - Open FreeCAD
   - Activate GitPDM workbench
   - Open repository in panel
   - Click "Install Hooks"

3. **Verify installation:**
   ```bash
   git config --get core.hooksPath  # Should be empty (using .git/hooks)
   ls -la .git/hooks/pre-commit      # Should show Python script
   ```

4. **Test:**
   - Make a change to .FCStd file
   - Commit → verify export happens
   - Checkout different branch → verify import happens

## Differences from Bash Hooks

- **Better error messages**: Python hooks provide clearer errors
- **Cross-platform**: No Git Bash required on Windows
- **Faster**: No subprocess overhead
- **Testable**: Can unit test hook logic
```

**Deliverables:**
- [ ] User documentation
- [ ] Developer API docs
- [ ] Migration guide
- [ ] Troubleshooting section

**Acceptance Criteria:**
- All documentation complete
- Migration guide tested
- Examples included

---

## Definition of Done (Sprint 2)

- [x] All bash hooks converted to Python
- [x] HooksManager for installation
- [x] UI integration complete
- [x] Tests pass on Windows/Linux/macOS
- [x] Documentation complete
- [x] No regressions vs. bash hooks
- [x] Code review approved

---

## Risks & Mitigations

**Risk:** Python not available in git hook context  
**Mitigation:** Test in various environments, fallback to bash if needed

**Risk:** Subtle differences in hook execution  
**Mitigation:** Extensive testing, side-by-side comparison with bash

**Risk:** Performance issues with Python startup  
**Mitigation:** Profile hook execution, optimize imports

---

## Dependencies

- Sprint 1 completed (`core/fcstd_tool`, `core/lock_manager`)
- Git installed and configured
- Git LFS installed
- Python 3.8+ available in PATH

---

## Success Metrics

- ✅ Zero bash dependencies for hooks
- ✅ Hooks install with one click from UI
- ✅ Performance within 20% of bash hooks
- ✅ Works on Windows/Linux/macOS
- ✅ All existing hook behaviors preserved

---

**Next Sprint:** Sprint 3 - Wrapper Elimination (remove gitcad/wrapper.py entirely)
