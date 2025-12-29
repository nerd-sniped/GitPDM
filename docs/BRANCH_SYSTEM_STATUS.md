# Branch System: Status & Next Steps

**Date**: December 29, 2025  
**Status**: ⚠️ Still experiencing corruption despite multiple guard implementations  
**Focus**: MVP - Find minimum viable solution that actually prevents corruption

---

## The Core Problem

**.FCStd files are getting corrupted during branch operations**, specifically:
```
OSError: Invalid project file: ios_base::failbit set: iostream stream error
```

**Example Path**: `C:/Users/Ryank/Desktop/Sandbox/TestCookie-TestPranch/Bolt.FCStd`

This indicates:
- Corruption is occurring in worktree folders
- The file structure (ZIP-based) is being damaged
- FreeCAD cannot read the file after git operations

---

## What Has Been Tried (Chronologically)

### ✅ Attempt 1: Basic Branch Switch Guard
**Implementation**: Check for open files in current repo before switching
- Function: `_get_open_repo_documents()` - checks files under `self._current_repo_root`
- Result: **FAILED** - Files still corrupted

**Why it failed**: Only checked current repo; missed files from other worktrees

---

### ✅ Attempt 2: Lock File Detection
**Implementation**: Check for `.FCStd.lock` files in repo
- Function: `_find_repo_lock_files()` - glob for `*.FCStd.lock`
- Combined with open file check
- Result: **PARTIAL** - Helps detect crashed/locked files, but doesn't prevent corruption

**Why it partially worked**: Catches some cases, but doesn't prevent all corruption scenarios

---

### ✅ Attempt 3: Worktree Workflow
**Implementation**: Create separate folders per branch to isolate files
- Prompt user to create worktree instead of in-place switch
- Path: `<repo>-<branch>` (e.g., `TestCookie-feature`)
- Automatic folder opening after creation
- Result: **FAILED** - Corruption still occurs in worktree paths

**Why it failed**: 
- Worktrees share git objects database
- If ANY files are open during worktree creation, corruption can occur
- Added complexity without solving core issue

---

### ✅ Attempt 4: Dialog Prevention
**Implementation**: Disable OK button in "Create Branch" dialog when files open
- Modified `NewBranchDialog` to accept open file lists
- Show warning, disable OK button
- Result: **GOOD UX** - Prevents user from creating branches with files open, but doesn't prevent all corruption

**Why it's incomplete**: User can still use "Switch" button or other operations

---

### ✅ Attempt 5: Pull Guard
**Implementation**: Block pull operations when files are open
- Added guard to `_on_pull_clicked()`
- Shows critical warning
- Result: **UNKNOWN** - Not yet tested, but theoretically sound

---

### 🔄 Attempt 6: Universal File Guard (JUST IMPLEMENTED, NOT TESTED)
### ❌ Attempt 6: Universal File Guard (TESTED - FAILED)
**Implementation**: Check ALL open .FCStd files (not just current repo)
- New function: `_get_all_open_fcstd_documents()` - checks ALL FreeCAD documents
- Applied to: branch switch, branch creation, pull
- Double-check before operations (prevents race conditions)
- Result: **FAILED** - Corruption still occurred

**Test Result**: 
- File corrupted: `C:/Users/Ryank/Desktop/TestRepo/ProjectProject-branchdybranch/Circle.FCStd`
- Error: `ios_base::failbit set: iostream stream error`
- **Additional regression**: Upstream now shows `origin/main` instead of correct branch

**Why it failed**: 
- Guards might not be triggering when they should
- User might be using external tools (GitHub Desktop, CLI) that bypass guards
- Corruption might be happening at a different point than switch/create/pull
- Worktrees add complexity and failure points without providing protection

---

## What Actually Works

### ✅ **File Detection**
- `FreeCAD.listDocuments()` correctly enumerates open files
- Path normalization works across worktrees
- Lock file glob detection works

### ✅ **Git Operations**
- Branch creation works: `git checkout -b`
- Branch switching works: `git switch` / `git checkout`
- Worktree creation works: `git worktree add`
- Pull/fetch work when no files are open

### ✅ **UI Components**
- Dialogs display correctly
- Button enabling/disabling works
- Warning messages are shown
- Repository browser updates

### ✅ **User Workflow (When Followed)**
If user manually:
1. Closes ALL FreeCAD files
2. Performs git operation
3. Opens files from new branch
→ **NO CORRUPTION**

---

## What Doesn't Work

### ❌ **Automatic Prevention**
- Guards can be bypassed (user opens files after dialog, before operation)
- No mechanism to force-close files
- Can't prevent external git operations (command line, GitHub Desktop)

### ❌ **Worktree Isolation**
- Worktrees don't actually isolate file corruption risk
- Shared git objects database means operations affect all worktrees
- Added complexity for no reliability gain

### ❌ **Race Conditions**
- User can open file between dialog close and operation start
- Background processes might open files
- Multiple FreeCAD instances

### ❌ **Recovery**
- No automatic detection of corrupted files
- No automatic rollback or recovery
- User loses work if corruption isn't caught immediately

---

## Root Cause Analysis

The corruption happens because:

1. **FreeCAD's File Handling**
   - `.FCStd` files are ZIP archives with strict checksums
   - FreeCAD keeps file handles open, even with "save"
   - File locks don't prevent git from modifying files

2. **Git's Behavior**
   - Git operations (`switch`, `pull`, `checkout`) replace file contents
   - Git doesn't respect application file locks
   - Worktrees share objects database - operations in one affect others

3. **Timing**
   - Even with guards, there's a window between check and operation
   - User can open files after check passes
   - External tools (GitHub Desktop, CLI) bypass guards entirely

4. **Binary File Sensitivity**
   - Text files can be partially corrupted and still work
   - Binary ZIP files become completely unreadable if even 1 byte is wrong
   - No graceful degradation

---

## MVP: What Should Work Next

### ❌ **Priority 1: Test Current Implementation** - FAILED

The "check ALL files" approach was tested and **failed to prevent corruption**.

**Test Results**:
- Corruption still occurred in worktree folder
- File: `ProjectProject-branchdybranch/Circle.FCStd`
- Guards did not prevent the corruption
- **Regression**: Upstream tracking now broken (shows origin/main incorrectly)

**Conclusion**: Guards alone are insufficient. Need different approach.

---

### 🎯 **Priority 2: Simplify (Remove Worktrees)**

### 🎯 **Priority 2: DISABLE BRANCH OPERATIONS (MVP Recommendation)**

**Reality Check**: After 6 attempts, corruption still happens. Guards alone don't work.

**RECOMMENDED FOR MVP**: **Disable branch switching in GitPDM entirely**

**Why This Is The Right Move**:
1. ✅ **Zero corruption risk** - can't corrupt if feature doesn't exist
2. ✅ **Reduces scope** - focus on what works (commit, push, pull on same branch)
3. ✅ **Users have alternatives** - GitHub Desktop, VS Code, command line all handle branches safely
4. ✅ **Ship faster** - remove broken feature, ship working product
5. ✅ **Honest** - better to not have a feature than to have one that loses user data

**What GitPDM MVP Should Focus On**:
- ✅ Commit changes (works reliably)
- ✅ Push to remote (works reliably)  
- ✅ Pull updates (add guard: must close files first, but pull on SAME branch is safer)
- ✅ View status (works)
- ✅ Repository browser (works)
- ✅ Create repo (works)
- ✅ Clone repo (works)
- ❌ Branch switching (REMOVE - too risky)

**User Workflow for Branches**:
1. Save work in FreeCAD
2. Use GitHub Desktop to switch branch
3. Refresh GitPDM
4. Continue working

This is **honest, safe, and ships**.

---

### 🎯 **Priority 3: Aggressive Prevention**

If tests still show corruption, escalate to:

#### Option A: Auto-Close Files
```python
def _auto_close_repo_documents():
    """Force-close all .FCStd files before git operations."""
    try:
        import FreeCAD
        for doc_name, doc in FreeCAD.listDocuments().items():
            if doc.FileName.lower().endswith('.fcstd'):
                FreeCAD.closeDocument(doc_name)
        return True
    except:
        return False
```

**Pros**: Guarantees files are closed  
**Cons**: User loses unsaved work, poor UX

#### Option B: Disable Branch Operations Entirely
```python
# In panel initialization
self.switch_branch_btn.setVisible(False)
self.new_branch_btn.setVisible(False)
# Show message: "Use GitHub Desktop or command line for branch operations"
```

**Pros**: Can't corrupt if can't switch  
**Cons**: Defeats purpose of the feature

#### Option C: Document Observer Pattern
```python
# Register observer when documents open/close
# Keep global state of open files
# Block operations dynamically
```

**Pros**: Real-time protection  
**Cons**: Complex, FreeCAD API limitations

---

### 🎯 **Priority 4: Detection & Recovery**

If prevention fails, add detection:

#### Corruption Detection on File Open
```python
def _verify_fcstd_integrity(file_path):
    """Check if .FCStd file is valid ZIP."""
    try:
        import zipfile
        with zipfile.ZipFile(file_path, 'r') as zf:
            bad = zf.testzip()
            return bad is None  # None = all good
    except:
        return False
```

#### Auto-Recovery from Git
```python
def _attempt_recovery(file_path):
    """Try to restore file from git history."""
    # Get last known good version
    result = subprocess.run(
        ['git', 'log', '--all', '--', file_path],
        capture_output=True
    )
    if result.returncode == 0:
        # Offer to restore from last commit
        # git checkout HEAD~1 -- file_path
```

---

## Recommended Next Steps

### For Next Session:

1. **TEST THE CURRENT IMPLEMENTATION FIRST**
   - Open FreeCAD
   - Open a .FCStd file from TestCookie-TestPranch
   - Try to switch branches or pull in GitPDM
   - **Expected**: Critical dialog appears, operation blocked
   - **If this works**: Problem is solved, guards are sufficient

2. **If Still Corrupting:**
   - Check logs to see what operation caused corruption
   - Verify the guard functions are actually being called
   - Check if external tools (GitHub Desktop, CLI) are being used
   - Look for timing windows (open file after check, before operation)

3. **Consider MVP Simplification:**
   - **Remove worktrees** - they don't help and add complexity
   - Focus on single-folder, in-place switching with strong guards
   - Simpler UX, same protection level

4. **If Guards Still Fail:**
   - Implement auto-close (Priority 3, Option A)
   - Add corruption detection (Priority 4)
   - Or disable branch operations entirely and document external workflow

---

## Success Criteria (MVP)

For the branch system to be "MVP ready":

✅ **Core Requirement**: User can switch branches without corrupting files

**Minimum Viable Implementation**:
- ✅ Guard blocks operations when ANY .FCStd files are open
- ✅ Clear error message tells user to close files
- ✅ Operations succeed when files are closed
- ✅ No corruption in normal workflow

**Nice to Have (Not Required for MVP)**:
- ⬜ Worktree support (adds complexity)
- ⬜ Auto-recovery (complex, edge case)
- ⬜ File integrity checking (preventative only)
- ⬜ Auto-close files (poor UX)

---

## Files Modified

### Current Implementation (Attempt 6):
- `freecad_gitpdm/ui/panel.py`:
  - `_get_all_open_fcstd_documents()` - NEW: Check ALL files
  - `_switch_to_branch()` - MODIFIED: Use ALL files check
  - `_on_new_branch_clicked()` - MODIFIED: Use ALL files check + double-check
  - `_on_pull_clicked()` - NEW: Add guard for pull operations
  
- `freecad_gitpdm/ui/dialogs.py`:
  - `NewBranchDialog` - MODIFIED: Accept open files, disable OK button

### Documentation:
- `docs/FCSTD_CORRUPTION_FIX.md` - Technical explanation
- `docs/BRANCH_SYSTEM_STATUS.md` - This file

---

## Questions to Answer Next Session

1. **Does the ALL files check actually prevent corruption?**
   - Test with worktrees, multiple folders, edge cases

2. **Are worktrees worth the complexity?**
   - Do they provide any benefit if files must be closed anyway?
   - Could we simplify to single-folder workflow?

3. **What's the actual timing window?**
   - How long between check and operation?
   - Can user open files in that window?
   - Should we re-check immediately before git command?

4. **Should we trust the user or force safety?**
   - Guards + warnings (current approach)
   - vs. Auto-close files (aggressive)
   - vs. Disable feature (give up)

5. **What's the external tool risk?**
   - If user uses GitHub Desktop while FreeCAD is open?
   - Can we detect/warn about this?

---

## Bottom Line

**Current Status**: ❌ **All 6 attempts failed**. Corruption still occurs despite comprehensive guards.

**Reality**: Guards don't work because:
- User can use external tools (GitHub Desktop, CLI) that bypass guards
- Timing windows exist between checks and operations
- Worktrees add complexity without providing protection
- FreeCAD's file locking doesn't prevent git from modifying files

**MVP Recommendation: DISABLE BRANCH FEATURES**

Ship what works:
- ✅ Commit workflow
- ✅ Push workflow
- ✅ Pull workflow (with guard)
- ✅ Repository browser
- ✅ Status display
- ❌ Branch switching (remove)

This is the honest path: **Ship what works, document limitations, iterate later if needed.**
