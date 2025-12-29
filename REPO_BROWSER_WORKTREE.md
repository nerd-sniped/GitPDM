# Repository Browser Worktree Integration

## Problem Statement

When using per-branch worktrees, the Repository Browser must always show files from the **current worktree/branch**, not from a cached or stale location.

## Solution Implemented

### 1. **Visual Branch/Worktree Indicator**
Added at the top of the Repository Browser:
```
📂 MyProject-feature-a  •  🌿 feature-a
```

Shows:
- 📂 Current folder name (worktree directory)
- 🌿 Current branch name

**Color:** Blue with light blue background for high visibility.

### 2. **Always Use `self._current_repo_root`**
The browser **always** uses `self._current_repo_root` for:
- Listing files: `git -C <current_repo_root> ls-files`
- Opening files: `os.path.join(self._current_repo_root, rel_path)`
- Revealing in explorer: absolute paths from current root

### 3. **Automatic Refresh on Worktree Switch**
When switching to a worktree:
1. `_on_worktree_created()` calls `settings.save_repo_path(worktree_path)`
2. Then calls `_validate_repo_path(worktree_path)`
3. `_validate_repo_path()` updates `self._current_repo_root = worktree_path`
4. Then calls `_refresh_repo_browser_files()`
5. Browser lists files from the new worktree path
6. Indicator updates to show new worktree/branch

### 4. **Enhanced Logging**
When opening files:
```python
log.info(f"Opening file from repo browser: {rel}")
log.info(f"  Absolute path: {abs_path}")
log.info(f"  Current repo root: {self._current_repo_root}")
```

This helps diagnose any path mismatches.

## Expected Behavior

### Scenario 1: Main Repo (MyProject/)
**Repo Root:** `C:\Projects\MyProject\`  
**Current Branch:** `main`  
**Browser Shows:**
- `circle.FCStd`
- `square.FCStd`

**Indicator:** `📂 MyProject  •  🌿 main`

**Opening `circle.FCStd` opens:** `C:\Projects\MyProject\circle.FCStd`

### Scenario 2: After Switching to feature-a (Worktree)
**User Action:** Click "Switch to feature-a" → Accept worktree creation

**Repo Root:** `C:\Projects\MyProject-feature-a\`  
**Current Branch:** `feature-a`  
**Browser Shows:**
- `circle.FCStd` (modified version)
- `square.FCStd`
- `triangle.FCStd` (new file)

**Indicator:** `📂 MyProject-feature-a  •  🌿 feature-a`

**Opening `circle.FCStd` opens:** `C:\Projects\MyProject-feature-a\circle.FCStd`

### Scenario 3: Switching Back to Main
**User Action:** Browse to `C:\Projects\MyProject\` in Repo Path field

**Repo Root:** `C:\Projects\MyProject\`  
**Current Branch:** `main`  
**Browser Shows:**
- `circle.FCStd`
- `square.FCStd`

**Indicator:** `📂 MyProject  •  🌿 main`

**Opening `circle.FCStd` opens:** `C:\Projects\MyProject\circle.FCStd` (original version)

## How Files Are Listed

```python
# In _refresh_repo_browser_files():
git_cmd = self._git_client._get_git_command()
args = [git_cmd, "-C", self._current_repo_root, "ls-files", "-z"]
```

**Key:** The `-C <repo_root>` flag tells git to operate in that directory. This ensures files listed are from the current worktree, not the original repo.

## How Files Are Opened

```python
# In _open_repo_file():
abs_path = os.path.normpath(
    os.path.join(self._current_repo_root, rel)
)
```

**Key:** Relative paths from the browser are **always** resolved against `self._current_repo_root`, ensuring files opened come from the active worktree.

## Testing the Browser

### Manual Test Steps:

1. **Start with main repo:**
   - Open GitPDM panel
   - Set Repo Path to your main repo folder
   - Open Repository Browser
   - Verify indicator shows: `📂 <repo-name>  •  🌿 main`
   - Note which files are listed

2. **Switch to feature branch with worktree:**
   - Click "Switch to feature-a"
   - Accept worktree creation prompt
   - Click "Open Folder" to see the worktree directory
   - Repository Browser should automatically refresh
   - Verify indicator shows: `📂 <repo-name>-feature-a  •  🌿 feature-a`
   - Note any new/modified files

3. **Open a file from worktree:**
   - Double-click a file in the browser
   - In FreeCAD, check: `App.ActiveDocument.FileName`
   - Should show: `C:\...\<repo-name>-feature-a\<file>.FCStd`
   - **Not:** `C:\...\<repo-name>\<file>.FCStd`

4. **Verify file content:**
   - Edit and save the file
   - Close FreeCAD document
   - Open the worktree folder in File Explorer
   - Verify your edits are in the worktree file, not main repo file

### Automated Test:
Run `python test_repo_browser_worktree.py` to verify file listing logic.

## Code Changes Summary

### `_create_browser_content()` - Added indicator label
```python
self.repo_branch_indicator = QtWidgets.QLabel("—")
self.repo_branch_indicator.setStyleSheet(
    "color: #2196F3; font-weight: bold; padding: 4px; "
    "background-color: #E3F2FD; border-radius: 3px;"
)
```

### `_refresh_repo_browser_files()` - Update indicator
```python
current_branch = self._git_client.current_branch(self._current_repo_root)
repo_name = os.path.basename(os.path.normpath(self._current_repo_root))
if current_branch:
    self.repo_branch_indicator.setText(
        f"📂 {repo_name}  •  🌿 {current_branch}"
    )
```

### `_refresh_repo_browser_files()` - Added logging
```python
log.info(f"Listing files from: {self._current_repo_root} (branch: {current_branch})")
```

### `_open_repo_file()` - Enhanced logging
```python
log.info(f"Opening file from repo browser: {rel}")
log.info(f"  Absolute path: {abs_path}")
log.info(f"  Current repo root: {self._current_repo_root}")
```

### `_clear_repo_browser()` - Reset indicator
```python
self.repo_branch_indicator.setText("—")
```

## Troubleshooting

### "Browser shows wrong files after switching branches"
**Cause:** `self._current_repo_root` not updated, or browser not refreshed.  
**Fix:** Ensure `_validate_repo_path()` is called after worktree creation. Check logs for "Listing files from:" message.

### "Opening file opens wrong version"
**Cause:** File opened from main repo instead of worktree.  
**Fix:** Check `App.ActiveDocument.FileName` in FreeCAD. Should match worktree path. Check logs for "Opening file from repo browser" message.

### "Indicator shows wrong branch"
**Cause:** `current_branch()` called on wrong repo root, or indicator not updated.  
**Fix:** Verify `self._current_repo_root` points to worktree. Check if `_refresh_repo_browser_files()` is called.

### "Browser not refreshing after worktree switch"
**Cause:** `_validate_repo_path()` not called, or job runner busy.  
**Fix:** Ensure `_on_worktree_created()` completes successfully. Click "Refresh Files" button manually.

## Summary

The Repository Browser now:
- ✅ Always shows files from the current worktree/branch
- ✅ Visually indicates which folder and branch is active
- ✅ Opens files from the correct worktree directory
- ✅ Automatically refreshes when switching worktrees
- ✅ Logs all file operations for debugging

This ensures **no confusion** about which version of a file you're editing, **preventing corruption** from editing the wrong folder.
