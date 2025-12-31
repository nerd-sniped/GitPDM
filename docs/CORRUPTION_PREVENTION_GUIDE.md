# FreeCAD File Corruption Prevention Guide

## The Problem

When switching Git branches while FreeCAD `.FCStd` files are open, you may experience file corruption. This happens because:

1. **Binary files don't merge**: Unlike text files, `.FCStd` files cannot be automatically merged by Git
2. **File locking**: FreeCAD locks files while editing, but Git may swap file content underneath
3. **Wrong folder editing**: Creating a worktree but continuing to edit files from the main repo folder

## Root Cause Analysis

The automated tests (`test_worktree_folder_mismatch.py`) revealed the most likely cause:

```
SCENARIO:
1. User creates worktree for feature-a → MyProject-feature-a/
2. GitPDM updates to show worktree is active
3. BUT user still has FreeCAD documents open from MyProject/ (main repo)
4. User edits and saves files in MyProject/ folder
5. User switches branches in UI
6. Git operations affect MyProject-feature-a/ (correct worktree)
7. But changes were made to MyProject/ (wrong folder)
8. Result: User sees "corruption" (actually wrong folder mismatch)
```

## Solutions Implemented

### 1. **Automatic Worktree Creation** (RECOMMENDED)
When you click "Switch Branch", GitPDM now:
- Prompts to create a per-branch worktree folder
- Creates `<repo>-<branch>/` directory via `git worktree add`
- Updates GitPDM to point to the new worktree
- Shows success dialog with "Open Folder" button

**How to use:**
1. Click "Switch to feature-a"
2. Accept the worktree prompt (recommended)
3. Click "Open Folder" in success dialog
4. **Open your .FCStd files from the NEW folder in FreeCAD**

### 2. **Branch Switch Guard**
Before any branch switch, GitPDM checks:
- Are any FreeCAD documents from this repo open?
- Are any `.FCStd.lock` files present?

If yes → **Branch switch is blocked** with a warning listing:
- Open documents
- Lock files

**Action required:** Close all FreeCAD documents before switching branches.

### 3. **Wrong Folder Detection**
On startup, GitPDM checks if you have FreeCAD documents open from a **different folder** than the current repo root.

If detected → Shows warning dialog explaining the risk and current paths.

**Action required:** Close wrong-folder documents and reopen from correct worktree.

## Automated Testing

Two test scripts are provided to verify corruption scenarios:

### `test_worktree_corruption.py`
Tests:
- ✓ In-place branch switch with lock file present
- ✓ Worktree isolation (switching main repo doesn't affect worktree)
- ✓ Lock file detection

**Run:** `python test_worktree_corruption.py`

### `test_worktree_folder_mismatch.py`
Simulates and demonstrates:
- Wrong folder editing scenario
- How to detect open folder from FreeCAD
- Recommended safe workflow

**Run:** `python test_worktree_folder_mismatch.py`

## Best Practices

### ✅ DO:
1. **Accept worktree prompts** when switching branches
2. **Click "Open Folder"** after worktree creation
3. **Open files from the worktree folder** in FreeCAD
4. **Close all FreeCAD documents** before switching branches
5. **Use the Worktree Help button** to see your current worktrees

### ❌ DON'T:
1. Switch branches with files open in FreeCAD
2. Edit files from the main repo after creating a worktree
3. Force-override the branch switch guard
4. Have documents open from multiple branch folders simultaneously

## Folder Structure Example

**CORRECT per-branch worktree setup:**
```
C:\Projects\
├── MyProject\                  ← Main repo (main branch)
│   ├── .git\
│   ├── circle.FCStd
│   └── square.FCStd
├── MyProject-feature-a\        ← Worktree for feature-a
│   ├── circle.FCStd           (feature-a version)
│   └── square.FCStd
└── MyProject-feature-b\        ← Worktree for feature-b
    ├── circle.FCStd           (feature-b version)
    └── square.FCStd
```

**When editing feature-a:**
- Open files from `MyProject-feature-a\` in FreeCAD
- GitPDM repo root shows: `MyProject-feature-a`

**When editing feature-b:**
- Close all FreeCAD documents
- Switch to feature-b in GitPDM
- Accept worktree creation
- Open files from `MyProject-feature-b\` in FreeCAD

## Troubleshooting

### "I created a worktree but files are still corrupted"
➜ Check: Are you opening files from the correct worktree folder in FreeCAD?
- In FreeCAD, check document path: `App.ActiveDocument.FileName`
- It should match the worktree path shown in GitPDM

### "I can't switch branches"
➜ Check: Do you have FreeCAD documents open?
- Close all `.FCStd` files in FreeCAD
- Try switch again

### "Wrong Folder warning appears"
➜ Action:
1. Note the paths shown in the warning
2. Close documents from the wrong folder
3. Open documents from the correct worktree folder (shown in GitPDM)

### "How do I see my worktrees?"
➜ Options:
1. Click "Worktree Help" button in GitPDM
2. Run in terminal: `git worktree list`
3. Check parent folder of your main repo

## Technical Details

### Lock File Detection
- Checks for `*.FCStd.lock` files in repo root
- FreeCAD creates these when opening files
- Presence indicates file is currently open

### Open Document Detection
- Uses FreeCAD's `App.listDocuments()` API
- Checks each document's `FileName` absolute path
- Compares against current repo root
- Normalizes paths for cross-platform compatibility

### Worktree Creation
- Uses `git worktree add <path> <branch>`
- Updates GitPDM settings to new worktree path
- Validates new path and refreshes UI
- Opens folder in system file explorer

## UI Features

### Success Dialog
After worktree creation:
- Shows worktree path
- **Warning** to open files from new folder
- "Open Folder" button → opens worktree in Explorer
- "Close" button → continues without opening folder

### Status Messages
- "Opened worktree: MyProject-feature-a" (5 second timeout)
- Shown at bottom of GitPDM panel

### Worktree Help Button
- Shows example `git worktree` commands
- Explains per-branch folder concept
- Accessible from branch section

## For Developers

### New Methods Added

**Panel UI** (`freecad_gitpdm/ui/panel.py`):
- `_compute_worktree_path_for_branch(branch_name)` → suggested path
- `_create_and_open_worktree(branch_name, path)` → async worktree creation
- `_on_worktree_created(job, path, branch)` → completion handler
- `_show_worktree_success_dialog(path, branch)` → success UI
- `_open_folder_in_explorer(path)` → platform-specific folder opening
- `_check_for_wrong_folder_editing()` → startup validation
- `_get_open_repo_documents()` → lists open FreeCAD docs in repo
- `_find_repo_lock_files()` → glob for `*.FCStd.lock`

### Test Coverage
- In-place switch with lock (may corrupt)
- Worktree switch with lock (safe, isolated)
- Lock detection accuracy
- Wrong folder scenario simulation
- Folder mismatch detection

## Manual Verification Checklist

See `SPRINT_OAUTH-6_MANUAL_VERIFICATION.md` for comprehensive OAuth testing.

**Corruption Prevention Testing:**
1. ✓ Open FreeCAD document from repo
2. ✓ Attempt branch switch → blocked with warning
3. ✓ Close document → switch succeeds
4. ✓ Create worktree → "Open Folder" button works
5. ✓ Open file from worktree → no wrong folder warning
6. ✓ Open file from main repo → wrong folder warning appears
7. ✓ Switch branches with worktree → no corruption

## Summary

**The key to avoiding corruption:**
1. Use per-branch worktrees (automatic via UI)
2. Open files from the correct worktree folder in FreeCAD
3. Close all documents before switching branches
4. Trust the UI guards and warnings

**Why this works:**
- Each branch has its own physical folder
- No file swapping under FreeCAD's feet
- Clear separation between branch contexts
- Explicit folder-switching workflow
