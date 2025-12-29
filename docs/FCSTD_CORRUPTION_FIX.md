# FreeCAD .FCStd File Corruption Prevention

## The Problem

FreeCAD `.FCStd` files are **ZIP-based binary files** that are extremely sensitive to corruption when git operations occur while they're open. The corruption manifests as:

```
OSError: Invalid project file: ios_base::failbit set: iostream stream error
```

This error means the file's internal structure has been corrupted and FreeCAD can no longer read it.

## Root Cause

The corruption occurs due to a combination of factors:

1. **Binary File Sensitivity**: `.FCStd` files use ZIP compression with specific headers and checksums. Any modification to the file while it's open corrupts these structures.

2. **Git Operations Modify Files**: Git operations like `switch`, `checkout`, `pull`, and `merge` modify files in the working tree by replacing their contents.

3. **File Locks Are Insufficient**: Windows `.FCStd.lock` files don't prevent git from modifying the underlying `.FCStd` file.

4. **Worktree Cross-Contamination**: Even when using git worktrees (separate folders per branch), git operations in one worktree can affect files in other worktrees if:
   - The git objects database is shared (normal worktree behavior)
   - File handles are open across worktrees
   - Background processes sync changes

## The Fix: Universal File-Closed Guards

GitPDM now implements **comprehensive guards** that block ALL git operations when ANY `.FCStd` files are open in FreeCAD:

### Protected Operations

1. **Branch Switching** (`_switch_to_branch`)
   - Checks ALL open `.FCStd` files (not just current repo)
   - Shows CRITICAL warning dialog
   - Blocks operation completely

2. **Branch Creation** (`_on_new_branch_clicked`)
   - Checks before showing dialog (disables OK button)
   - Double-checks after dialog closes (prevents race condition)
   - Blocks branch creation AND subsequent switch

3. **Pull Operations** (`_on_pull_clicked`)
   - Checks before starting pull
   - Pull modifies working tree files
   - Shows CRITICAL warning with file list

4. **Worktree Creation** (`_create_and_open_worktree`)
   - Inherits protection from `_switch_to_branch`
   - Worktrees share git database, can cause cross-contamination

### Implementation Details

#### Key Functions

**`_get_all_open_fcstd_documents()`**
```python
def _get_all_open_fcstd_documents(self):
    """
    Return list of ALL open .FCStd files in FreeCAD, regardless of location.
    
    This is used for worktree safety - we need to ensure NO FreeCAD files are open
    when performing any git operations, since git worktree operations can affect
    files in other worktrees indirectly.
    """
```

This function:
- Queries FreeCAD for all open documents
- Filters for `.FCStd` files only
- Returns absolute paths
- Works across ALL worktrees and folders

**Guard Pattern**
```python
# CRITICAL Guard: block ALL branch operations while ANY FreeCAD files are open
open_docs = self._get_all_open_fcstd_documents()
if open_docs:
    QtWidgets.QMessageBox.critical(
        self,
        "Close ALL Files First",
        "⚠️ CRITICAL: Close ALL FreeCAD documents before any branch operations!\n\n"
        "Git operations can corrupt .FCStd files that are currently open..."
    )
    log.warning("Operation blocked - open FreeCAD documents detected")
    return
```

### User Experience

When a user tries to perform a protected operation with files open:

1. **Proactive Prevention**: Dialog OK buttons are disabled when files are open
2. **Critical Warnings**: Operations show CRITICAL severity message boxes
3. **Clear Instructions**: "Close ALL FreeCAD documents (File → Close All)"
4. **File Listings**: Shows which files are open (up to 10, with "...and N more")

## Best Practices for Users

### Workflow

1. **Save your work** in FreeCAD
2. **Close ALL documents** (File → Close All)
3. **Verify**: Check that no documents appear in FreeCAD's window list
4. **Then perform git operations**: switch branches, pull, create branches, etc.
5. **Open files** in the new branch/worktree

### Using Worktrees

Worktrees are still recommended for isolation, but you MUST close files first:

```bash
# Each worktree has its own folder
C:\Projects\MyProject\         # main branch worktree
C:\Projects\MyProject-feature\ # feature branch worktree
```

**Important**: Even with separate worktrees:
- Git operations in one can affect others (shared object database)
- **ALWAYS close ALL FreeCAD files before ANY git operation**

### What NOT To Do

❌ **Don't**: Keep files open while switching branches
❌ **Don't**: Pull changes while working on a file
❌ **Don't**: Switch worktrees without closing files from the old worktree
❌ **Don't**: Have multiple FreeCAD instances with files from different worktrees open

✅ **Do**: Close everything, perform git operations, then open what you need

## Technical Notes

### Why Check ALL Files, Not Just Current Repo?

Git worktrees share the `.git` objects database. Operations like:
- `git worktree prune`
- `git gc`
- `git repack`
- Background maintenance

...can affect files across ALL worktrees. By checking ALL open `.FCStd` files regardless of location, we prevent:
- Cross-worktree contamination
- Corruption from background git processes
- Race conditions during file handle operations

### Why CRITICAL Severity?

File corruption is:
- **Permanent**: Corrupted files cannot be recovered without git history
- **Silent**: Corruption may not be immediately noticed
- **Data Loss**: Hours of CAD work can be lost

Using `QMessageBox.critical()` ensures:
- Red warning icon
- Cannot be dismissed accidentally
- User understands severity

### Lock Files

GitPDM also checks for `.FCStd.lock` files, which indicate:
- FreeCAD crashed while a file was open
- Another FreeCAD instance has the file open
- File handles may still be held by the OS

These are treated the same as open files - operations are blocked.

## Testing

To verify the fix:

1. Open any `.FCStd` file in FreeCAD
2. Try to switch branches in GitPDM
3. Expected: CRITICAL dialog appears, operation blocked
4. Close the file in FreeCAD
5. Try again
6. Expected: Operation succeeds

## Recovery from Corruption

If a file is already corrupted:

1. **Don't save over it**: Close FreeCAD immediately
2. **Check git history**: `git log --all -- path/to/file.FCStd`
3. **Restore from last good commit**:
   ```bash
   git checkout HEAD~1 -- path/to/file.FCStd
   ```
4. **Or restore from specific commit**:
   ```bash
   git checkout <commit-hash> -- path/to/file.FCStd
   ```
5. **Test the restored file**: Open in FreeCAD
6. **Commit the restored version** if it works

## Summary

The corruption issue is now prevented by:
- ✅ Checking ALL open `.FCStd` files before ANY git operation
- ✅ Blocking operations with CRITICAL warnings
- ✅ Disabling dialog buttons when files are open
- ✅ Double-checking before operations (prevents race conditions)
- ✅ Clear user guidance and file listings

Users must **close ALL FreeCAD documents** before performing ANY git operations to ensure file safety.
