# GitPDM Worktree Integration - Complete Summary

## Changes Made

### 1. **Automatic Worktree Creation on Branch Switch**
- When clicking "Switch Branch", user is prompted to create a per-branch worktree
- Creates `<repo>-<branch>/` folder using `git worktree add`
- Updates repo root to the new worktree automatically
- Shows success dialog with "Open Folder" button

**Files Modified:**
- `freecad_gitpdm/ui/panel.py`:
  - `_switch_to_branch()` - Added worktree prompt
  - `_compute_worktree_path_for_branch()` - Calculates worktree path
  - `_create_and_open_worktree()` - Creates worktree asynchronously
  - `_on_worktree_created()` - Completion handler
  - `_show_worktree_success_dialog()` - Success UI with folder opening
  - `_open_folder_in_explorer()` - Cross-platform folder opening

### 2. **Repository Browser Worktree Integration**
- Browser always shows files from `self._current_repo_root` (current worktree)
- Visual indicator shows: `📂 <folder>  •  🌿 <branch>`
- Automatically refreshes when switching worktrees
- Enhanced logging for file operations
- Opening files uses correct worktree path

**Files Modified:**
- `freecad_gitpdm/ui/panel.py`:
  - `_create_browser_content()` - Added branch/worktree indicator label
  - `_refresh_repo_browser_files()` - Updates indicator, logs current root
  - `_open_repo_file()` - Enhanced logging of paths
  - `_clear_repo_browser()` - Resets indicator

### 3. **Branch Switch Guards**
- Blocks branch switching when FreeCAD documents from repo are open
- Checks for `.FCStd.lock` files (indicates file is open)
- Shows detailed warning with list of open documents/locks
- User must close files before switching

**Files Modified:**
- `freecad_gitpdm/ui/panel.py`:
  - `_switch_to_branch()` - Guard check before switch
  - `_get_open_repo_documents()` - Lists open FreeCAD docs in repo
  - `_find_repo_lock_files()` - Finds `.FCStd.lock` files

### 4. **Wrong Folder Detection**
- On startup, checks if FreeCAD documents are open from wrong folder
- Warns if documents are from different folder than current repo root
- Helps prevent silent corruption from folder mismatch

**Files Modified:**
- `freecad_gitpdm/ui/panel.py`:
  - `_deferred_initialization()` - Schedules wrong folder check
  - `_check_for_wrong_folder_editing()` - Detects and warns about mismatches

### 5. **Worktree Help Button**
- Added "Worktree Help" button in branch section
- Shows example `git worktree` commands
- Explains per-branch folder concept

**Files Modified:**
- `freecad_gitpdm/ui/panel.py`:
  - `_on_worktree_help_clicked()` - Shows help dialog

## Tests Created

### 1. `test_worktree_corruption.py`
Simulates:
- In-place branch switch with lock files
- Worktree isolation (switching main doesn't affect worktree)
- Lock file detection

### 2. `test_worktree_folder_mismatch.py`
Demonstrates:
- Wrong folder editing scenario (root cause of corruption)
- How to detect folder from FreeCAD document path
- Recommended safe workflow

### 3. `test_repo_browser_worktree.py`
Verifies:
- Browser lists correct files per branch/worktree
- File content differs between main and worktree
- Absolute paths resolve to correct worktree

## Documentation Created

### 1. `CORRUPTION_PREVENTION_GUIDE.md`
- Root cause analysis
- Solutions implemented
- Best practices (DO/DON'T)
- Folder structure examples
- Troubleshooting guide
- Manual verification checklist

### 2. `REPO_BROWSER_WORKTREE.md`
- Browser integration details
- Expected behavior per scenario
- How files are listed and opened
- Testing procedures
- Code changes summary
- Troubleshooting browser-specific issues

## User Workflow

### Safe Branch Switching:

1. **User clicks "Switch to feature-a"**
   - GitPDM shows prompt: "Create per-branch worktree? (Recommended)"
   
2. **User accepts worktree creation**
   - GitPDM runs: `git worktree add C:\Projects\MyProject-feature-a feature-a`
   - Updates repo root to: `C:\Projects\MyProject-feature-a\`
   - Repository Browser automatically refreshes
   
3. **Success dialog appears**
   - Shows worktree path
   - Warning: "Open files from this new worktree folder"
   - "Open Folder" button → opens `MyProject-feature-a` in Explorer
   
4. **User opens files from worktree folder**
   - In FreeCAD: File → Open → Navigate to `MyProject-feature-a\`
   - Opens `circle.FCStd` from worktree (feature-a version)
   - Repository Browser shows: `📂 MyProject-feature-a  •  🌿 feature-a`
   
5. **User edits and saves**
   - Changes saved to: `C:\Projects\MyProject-feature-a\circle.FCStd`
   - Main repo file untouched: `C:\Projects\MyProject\circle.FCStd`
   - No corruption!

### If User Has Files Open:

1. **User clicks "Switch to feature-b" with files open**
   - Guard detects open documents/locks
   - Shows warning dialog:
     ```
     ⚠️ Cannot switch branches while FreeCAD documents are open
     
     Open documents from this repo:
       • C:\Projects\MyProject-feature-a\circle.FCStd
     
     Lock files detected:
       • C:\Projects\MyProject-feature-a\circle.FCStd.lock
     
     Close all FreeCAD documents before switching branches.
     ```
   
2. **User closes documents**
   - Branch switch now allowed
   - Proceeds with worktree creation

### If User Opens Wrong Folder:

1. **User created worktree but opened main repo folder in FreeCAD**
   - GitPDM detects mismatch on next UI interaction
   - Shows warning:
     ```
     ⚠️ WRONG FOLDER DETECTED
     
     You have FreeCAD documents open from a different folder:
       • C:\Projects\MyProject\circle.FCStd
     
     Current GitPDM repo: C:\Projects\MyProject-feature-a
     
     This can cause corruption! Close these documents and
     open files from the current worktree folder.
     ```

## Key Technical Points

### Repo Root is Everything
- `self._current_repo_root` is the **single source of truth**
- All git operations use `-C self._current_repo_root`
- All file paths resolved against `self._current_repo_root`
- Browser, status, commits, pushes - all use current root

### Worktree Isolation
- Each worktree has its own `.git` file (not directory)
- `.git` file points to main repo's `.git` directory
- Working directory is completely separate
- Checking out different branches in main repo doesn't affect worktrees
- Worktrees can be on different branches simultaneously

### FreeCAD Integration
- `App.listDocuments()` → all open documents
- `doc.FileName` → absolute path of document
- `.FCStd.lock` files → indicates file is currently open
- Must use absolute paths to detect which repo documents belong to

### Cross-Platform Support
- `os.startfile()` for Windows (opens Explorer)
- `open` command for macOS (opens Finder)
- `xdg-open` for Linux (opens file manager)
- Path normalization using `os.path.normpath()`

## Benefits

### For Users:
- ✅ No more file corruption from branch switching
- ✅ Clear visual indication of which branch/worktree is active
- ✅ Automatic worktree setup with guided workflow
- ✅ Prevention of accidental wrong-folder editing
- ✅ Enhanced safety guards and warnings

### For Developers:
- ✅ Comprehensive test coverage
- ✅ Detailed documentation
- ✅ Enhanced logging for debugging
- ✅ Clear separation of concerns
- ✅ Extensible worktree infrastructure

## Next Steps (Optional Future Enhancements)

1. **Auto-Close Documents Before Switch**
   - Programmatically close FreeCAD documents
   - Save before closing (with user prompt)
   - Reopen from new worktree after switch

2. **Worktree List View**
   - Show all worktrees with branches
   - Quick-switch between existing worktrees
   - Delete/prune unused worktrees

3. **Worktree Status Indicators**
   - Show which worktrees have uncommitted changes
   - Indicate which branch is checked out in each worktree
   - Warn about conflicts across worktrees

4. **Branch Comparison**
   - Visual diff between branches/worktrees
   - File-by-file comparison
   - Preview changes before switching

## Conclusion

The worktree integration provides a **robust, user-friendly solution** to FreeCAD file corruption during branch switching. By:
- Creating isolated per-branch directories
- Providing clear visual indicators
- Implementing safety guards
- Detecting and warning about wrong-folder editing

Users can now safely work on multiple branches without fear of corruption, while the Repository Browser ensures they're always viewing and editing the correct version of their files.
