# Sprint OAUTH-5: Branch Workflow UX - Manual Verification Checklist

## Overview
This sprint adds branch workflow UX with create/switch/delete operations and improves ahead/behind calculations to use tracking upstream when available.

## Pre-Test Setup
1. Ensure you have a GitHub repo with at least one branch (e.g., main)
2. Clone or open the repo in FreeCAD using GitPDM
3. Have some test files ready to commit

## Verification Steps

### 1. Branch Display and Selector
- [ ] **Open FreeCAD** → Launch GitPDM workbench
- [ ] **Select a repository** using the repo selector
- [ ] **Verify Branch section appears** between Status and Changes sections
- [ ] **Check Current branch shows** in dropdown (should show "main" or current branch)
- [ ] **Verify branch dropdown is populated** with all local branches
- [ ] **Check buttons present**: "New Branch…", "Switch", "Delete…"

### 2. Upstream Tracking Display
- [ ] **Click Fetch** button
- [ ] **Verify upstream shows** correct ref (e.g., "origin/main")
- [ ] **Check ahead/behind counts** make sense
- [ ] **Verify Status section shows**:
  - Branch: current branch name
  - Upstream: tracking ref (e.g., "origin/main")
  - Ahead/Behind: "Ahead X / Behind Y"

### 3. Create New Branch
- [ ] **Click "New Branch…"** button
- [ ] **Verify dialog appears** with:
  - Branch name field (empty)
  - Start point field (shows default like "origin/main")
  - OK button (disabled until name entered)
- [ ] **Enter branch name**: `feature/test-branch`
- [ ] **Verify OK button enables** after entering name
- [ ] **Click OK**
- [ ] **Verify branch is created** and GitPDM switches to it
- [ ] **Check branch dropdown** now shows `feature/test-branch` selected
- [ ] **Check Status section** updates:
  - Branch: `feature/test-branch`
  - Upstream: should show "(not set)" or similar (no tracking yet)

### 4. Make Changes and Commit
- [ ] **Make a small change** (edit a file or save a FreeCAD document in repo)
- [ ] **Verify Changes section** shows the modified file
- [ ] **Enter commit message** (e.g., "Test commit on feature branch")
- [ ] **Click Commit button**
- [ ] **Verify commit succeeds**
- [ ] **Check Working tree** shows "Clean"
- [ ] **Check Ahead/Behind** shows "Ahead 1" (or similar)

### 5. Push New Branch (Sets Upstream)
- [ ] **Click Push button**
- [ ] **Verify push succeeds**
- [ ] **Check Status section updates**:
  - Upstream: should now show `origin/feature/test-branch`
  - Ahead: should be 0
  - Behind: should be 0
- [ ] **Verify no errors** during push

### 6. Switch Branch (Clean Working Tree)
- [ ] **Select "main"** from branch dropdown
- [ ] **Click "Switch" button**
- [ ] **Verify branch switches** to main
- [ ] **Check Status section**:
  - Branch: `main`
  - Upstream: `origin/main` (or tracking ref)
  - Ahead/Behind: updated for main branch
- [ ] **Verify UI remains responsive** (no freezing)

### 7. Dirty Working Tree Warning
- [ ] **Make a change** without committing (edit a file)
- [ ] **Verify Changes section** shows uncommitted change
- [ ] **Try to switch branch** (select different branch and click Switch)
- [ ] **Verify warning dialog appears**:
  - Title: "Uncommitted Changes"
  - Message: warns about uncommitted changes
  - Buttons: Yes / No
- [ ] **Click "No"** to cancel
- [ ] **Verify branch does NOT switch**
- [ ] **Try again and click "Yes"**
- [ ] **Verify branch switch completes** (or fails if git prevents it)

### 8. Delete Branch
- [ ] **Ensure you're on main branch** (not the branch to delete)
- [ ] **Select `feature/test-branch`** from dropdown
- [ ] **Verify "Delete…" button is enabled**
- [ ] **Click "Delete…" button**
- [ ] **Verify confirmation dialog** appears
- [ ] **Click "Yes"** to confirm
- [ ] **Verify branch is deleted**
- [ ] **Check branch dropdown** no longer shows `feature/test-branch`
- [ ] **Verify current branch remains** on main (unchanged)

### 9. Delete Current Branch (Should Fail)
- [ ] **Verify "Delete…" button is disabled** when current branch is selected
- [ ] **Try selecting current branch** in dropdown
- [ ] **Confirm Delete button stays disabled**

### 10. Ahead/Behind with Tracking Upstream
- [ ] **Create another branch** and push it (sets upstream)
- [ ] **Make a commit** on that branch locally
- [ ] **Verify Ahead shows** increased count
- [ ] **Verify Upstream shows** correct tracking ref (e.g., `origin/feature/...`)
- [ ] **Switch to different branch**
- [ ] **Switch back**
- [ ] **Verify Ahead/Behind updates** correctly for each branch

### 11. UI Responsiveness
- [ ] **All branch operations** should run asynchronously
- [ ] **UI should not freeze** during:
  - Branch creation
  - Branch switching
  - Branch deletion
  - Fetching branch list
- [ ] **Verify busy indicators** appear during operations (e.g., "Switching to branch…")

### 12. Compact Mode
- [ ] **Click "Collapse" button** to enter compact mode
- [ ] **Verify Branch section is hidden** in compact mode
- [ ] **Click "Expand" button**
- [ ] **Verify Branch section reappears**

## Expected Results Summary

✅ **Branch selector** shows current branch and all local branches  
✅ **New Branch** creates and switches to new branch  
✅ **Switch** changes to selected branch with dirty tree warning  
✅ **Delete** removes non-current branches with confirmation  
✅ **Push** automatically sets upstream for new branches  
✅ **Ahead/Behind** uses tracking upstream (@{u}) when available  
✅ **Upstream display** shows correct tracking ref after push  
✅ **All operations** are async and don't freeze UI  
✅ **Refresh works** after branch operations (status, upstream, changes)  

## Common Issues to Check

- **Branch dropdown empty**: Check if git is available and repo is valid
- **Delete button always disabled**: Make sure selected branch ≠ current branch
- **Upstream not updating after push**: Verify push succeeded and check git log
- **UI freeze during switch**: Check if operation is truly async via job runner
- **Wrong ahead/behind counts**: Verify fetch has run and upstream ref is correct

## Notes

- This sprint does NOT include:
  - Pull/merge/rebase conflict resolution UI
  - PR workflow integration
  - Stash operations
  
- All branch operations use local git commands (no GitHub API)
- Push with `-u` flag automatically sets tracking upstream
- Ahead/behind compares HEAD...@{u} when tracking exists, otherwise falls back to origin/default

## Test Environment

- FreeCAD version: 1.0+
- Python version: (auto-detected)
- Qt binding: PySide6 or PySide2
- Git version: (check in System section)

---

**Tester**: _______________  
**Date**: _______________  
**Pass/Fail**: _______________  
**Notes**: _________________________________________________
