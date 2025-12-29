# Sprint OAUTH-5 Implementation Summary

## Overview
Implemented branch workflow UX and correct upstream-based ahead/behind calculation for GitPDM.

## Files Modified

### 1. `freecad_gitpdm/git/client.py`
**New Methods Added:**
- `list_local_branches(repo_root)` - Lists all local branches using `git branch --format=%(refname:short)`
- `list_remote_branches(repo_root, remote="origin")` - Lists remote branches, filters out HEAD pseudo-ref
- `create_branch(repo_root, name, start_point=None)` - Creates new branch with `git branch <name> [start_point]`
- `checkout_branch(repo_root, name)` - Switches branches using `git switch` (fallback to `git checkout`)
- `delete_local_branch(repo_root, name, force=False)` - Deletes local branch with `git branch -d/-D`
- `get_upstream_ref(repo_root)` - Gets tracking upstream with `git rev-parse --abbrev-ref --symbolic-full-name @{u}`
- `get_ahead_behind_with_upstream(repo_root)` - New method that uses tracking upstream if available, otherwise falls back to default

**Modified Methods:**
- `has_upstream(repo_root)` - Simplified to use `get_upstream_ref()` instead of duplicating logic

**Key Git Commands Used:**
```bash
# List local branches
git -C <repo> branch --format=%(refname:short)

# List remote branches
git -C <repo> branch -r --format=%(refname:short)

# Create branch
git -C <repo> branch <name> <start_point>

# Switch branch (modern)
git -C <repo> switch <name>

# Switch branch (fallback)
git -C <repo> checkout <name>

# Delete branch
git -C <repo> branch -d <name>  # safe delete
git -C <repo> branch -D <name>  # force delete

# Get tracking upstream
git rev-parse --abbrev-ref --symbolic-full-name @{u}

# Compare with tracking upstream
git rev-list --left-right --count HEAD...@{u}

# Push with upstream
git push -u origin HEAD
```

### 2. `freecad_gitpdm/ui/panel.py`
**New UI Components:**
- Branch section (QGroupBox) with:
  - Branch selector dropdown (QComboBox)
  - "New Branch…" button
  - "Switch" button  
  - "Delete…" button

**New State Variables:**
- `_is_switching_branch` - Tracks branch switch operations
- `_branch_combo_updating` - Prevents recursive combo change events
- `_local_branches` - Cached list of local branches

**New Methods:**
- `_build_branch_section(layout)` - Creates branch UI section
- `_refresh_branch_list()` - Updates branch combo with current branches
- `_update_branch_button_states()` - Enables/disables branch buttons based on state
- `_on_branch_combo_changed(index)` - Handles branch selection changes
- `_on_new_branch_clicked()` - Shows new branch dialog and creates branch
- `_validate_branch_name(name)` - Validates branch name against git rules
- `_on_switch_branch_clicked()` - Switches to selected branch
- `_switch_to_branch(branch_name)` - Performs branch switch with dirty check
- `_on_switch_branch_completed(job, branch_name)` - Callback after switch completes
- `_switch_to_branch_with_checkout(branch_name)` - Fallback to `git checkout` if `git switch` unavailable
- `_on_delete_branch_clicked()` - Deletes selected branch with confirmation
- `_refresh_after_branch_operation()` - Refreshes all UI after branch ops

**Modified Methods:**
- `_update_upstream_info(repo_root)` - Now uses `get_ahead_behind_with_upstream()` which prefers tracking upstream
- `_fetch_branch_and_status(repo_root)` - Added call to `_refresh_branch_list()`
- `_set_compact_mode(compact)` - Added branch section to compact mode handling
- `_update_button_states_fast()` - Added call to `_update_branch_button_states()`

**Upstream Logic Changes:**
```python
# OLD: Always used default upstream (origin/main or origin/master)
upstream_ref = self._git_client.default_upstream_ref(repo_root, self._remote_name)
ab_result = self._git_client.ahead_behind(repo_root, upstream_ref)

# NEW: Prefers tracking upstream, falls back to default
ab_result = self._git_client.get_ahead_behind_with_upstream(repo_root)
upstream_ref = ab_result.get("upstream")
# upstream_ref is now the actual tracking ref like "origin/feature-x"
# or the default "origin/main" if no tracking exists
```

### 3. `freecad_gitpdm/ui/dialogs.py`
**New Dialog:**
- `NewBranchDialog` - Dialog for creating new branches with:
  - Branch name input field with placeholder
  - Start point input field (default: origin/main or HEAD)
  - Input validation (OK button disabled until name entered)
  - Info text explaining start point

**Validation Rules:**
- No empty names
- No leading dash
- No spaces
- No special characters: `~^:?*[\..@{`

## Key Features Implemented

### 1. Branch Selector
- Dropdown showing all local branches
- Current branch is auto-selected
- Updates when branches are created/deleted/switched

### 2. Create New Branch
- Dialog prompts for branch name and start point
- Validates name according to git rules
- Creates branch and immediately switches to it
- Runs asynchronously to keep UI responsive

### 3. Switch Branch
- Select branch from dropdown and click "Switch"
- Checks for uncommitted changes first
- Shows warning dialog if dirty working tree
- User can proceed or cancel
- Async operation with fallback to `git checkout` for older git versions

### 4. Delete Branch
- Button disabled for current branch (can't delete what you're on)
- Shows confirmation dialog before deletion
- If branch not fully merged, offers force delete option
- Refreshes branch list after deletion

### 5. Upstream Tracking
- **Automatic upstream on push**: Uses `git push -u origin HEAD` when no upstream exists
- **Smart ahead/behind**: Compares HEAD...@{u} when tracking ref exists
- **Fallback**: Uses origin/main or origin/master when no tracking
- **Display**: Shows actual upstream ref (e.g., "origin/feature-x") in UI

### 6. Dirty Working Tree Guardrail
- Detects uncommitted changes before branch switch
- Shows warning with Yes/No choice
- Recommends committing or stashing (stash not implemented in this sprint)
- User can proceed at their own risk

### 7. Refresh Integration
- After branch creation: refreshes branch list, status, upstream
- After branch switch: refreshes everything including repo browser
- After push: updates upstream info (tracking ref and ahead/behind)
- All refreshes are automatic

### 8. Async Operations
- All git operations run via job runner (non-blocking)
- Busy indicators shown during operations
- Button states updated to prevent concurrent operations
- UI remains responsive throughout

## Acceptance Criteria Met

✅ User can see current branch and switch branches from within GitPDM  
✅ User can create new branch from main (or default) and switch to it  
✅ User can push new branch and GitPDM sets upstream automatically  
✅ Ahead/behind compares against @{u} when present, otherwise origin/default  
✅ Dirty working tree warning before branch switch  
✅ All operations are async and don't freeze UI  
✅ No GitHub API required (all local git operations)  
✅ Works with FreeCAD 1.0, PySide6/PySide2  
✅ No third-party packages used

## Out of Scope (As Specified)

- ❌ Pull/merge/rebase conflict UI improvements (kept simple)
- ❌ PR workflow integration
- ❌ Stash operations (only recommended in warning)

## Manual Verification

See [SPRINT_OAUTH-5_VERIFICATION.md](SPRINT_OAUTH-5_VERIFICATION.md) for complete testing checklist.

## Example Workflow

1. **User opens repo in GitPDM**
   - Branch dropdown shows "main"
   - Upstream shows "origin/main"
   - Ahead 0 / Behind 0

2. **User clicks "New Branch…"**
   - Dialog appears
   - User enters: "feature/my-feature"
   - Start point: "origin/main" (default)
   - Clicks OK

3. **GitPDM creates and switches**
   - Branch "feature/my-feature" created
   - Branch dropdown now shows "feature/my-feature"
   - Upstream shows "(not set)" (no tracking yet)

4. **User makes changes and commits**
   - Edit file, save
   - Enter commit message
   - Click Commit
   - Ahead becomes 1

5. **User pushes**
   - Click Push
   - GitPDM uses `git push -u origin HEAD`
   - Upstream now shows "origin/feature/my-feature"
   - Ahead becomes 0

6. **User switches back to main**
   - Select "main" from dropdown
   - Click "Switch"
   - (If changes exist, warning appears)
   - Branch switches
   - Upstream updates to "origin/main"

## Technical Notes

### Git Version Compatibility
- Prefers `git switch` (Git 2.23+)
- Falls back to `git checkout` for older versions
- All other commands work with Git 2.x

### Qt Compatibility
- Uses PySide6 if available (FreeCAD 1.0+)
- Falls back to PySide2 (FreeCAD 0.21)
- No Qt-version-specific code needed

### Error Handling
- All git operations return CmdResult with ok/stderr
- User-friendly error dialogs for failures
- Graceful degradation (e.g., if branch creation fails, no switch attempted)

### Performance
- Branch list cached in `_local_branches`
- Only refreshed when needed (repo load, create, delete, switch)
- Ahead/behind calculated once per fetch/push/refresh
- No polling or repeated git calls

## Git Commands Reference

**Branch Management:**
```bash
git branch --format=%(refname:short)           # list local branches
git branch -r --format=%(refname:short)        # list remote branches
git branch <name> <start_point>                # create branch
git switch <name>                              # switch branch (modern)
git checkout <name>                            # switch branch (classic)
git branch -d <name>                           # delete branch (safe)
git branch -D <name>                           # delete branch (force)
```

**Upstream Tracking:**
```bash
git rev-parse --abbrev-ref --symbolic-full-name @{u}  # get tracking upstream
git rev-list --left-right --count HEAD...@{u}         # ahead/behind vs tracking
git push -u origin HEAD                               # push and set upstream
```

## Implementation Quality

- **Code Reuse**: Leverages existing job runner and git client patterns
- **Consistency**: Follows GitPDM's async operation style
- **User Experience**: Warnings, confirmations, and clear feedback
- **Maintainability**: Well-documented methods, clear separation of concerns
- **Testability**: All operations can be tested via manual verification checklist

---

**Sprint OAUTH-5 Status**: ✅ **COMPLETE**
