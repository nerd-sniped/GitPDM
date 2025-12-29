# Working Directory Management for Repo Health

## Problem

When users open FreeCAD files from the Repository Browser, FreeCAD's "Save As" dialog may default to:
- The last directory where any file was saved (across sessions)
- FreeCAD's installation directory
- User's home directory

This causes **serious repo health issues**:
1. User accidentally saves files outside the repo
2. Files are not tracked by Git
3. Changes are lost or orphaned
4. Confusion about which files are "real" vs "copies"

## Solution

GitPDM now **automatically sets and maintains** the FreeCAD working directory to match the current repo folder.

## Implementation

### 1. Set Working Directory on Repo Validation
When a repo is validated (selected or switched):
```python
# In _validate_repo_path():
self._current_repo_root = repo_root
self._set_freecad_working_directory(repo_root)  # ← New!
```

**Result:** As soon as you select a repo, FreeCAD's working directory is set to that folder.

### 2. Set Working Directory on File Open
When opening a file from the Repository Browser:
```python
# In _open_repo_file():
self._set_freecad_working_directory(self._current_repo_root)  # ← Before opening
FreeCAD.open(abs_path)
self._set_freecad_working_directory(self._current_repo_root)  # ← After opening (belt and suspenders)
```

**Result:** Opening a file ensures the working directory is the repo folder.

### 3. Periodic Refresh
Every 10 seconds, GitPDM checks if the working directory has "drifted":
```python
def _refresh_working_directory(self):
    current_wd = os.getcwd()
    if current_wd != self._current_repo_root:
        # Reset to repo folder
        self._set_freecad_working_directory(self._current_repo_root)
```

**Result:** Even if FreeCAD or another addon changes the working directory, GitPDM resets it back to the repo.

## How _set_freecad_working_directory() Works

```python
def _set_freecad_working_directory(self, directory: str):
    # Method 1: Python's os.chdir()
    os.chdir(directory)
    
    # Method 2: FreeCAD's parameter (if available)
    FreeCAD.ParamGet("User parameter:BaseApp/Preferences/General")
        .SetString("FileOpenSavePath", directory)
    
    # Method 3: Qt static directory (belt and suspenders)
    QtWidgets.QFileDialog.setDirectory(directory)
```

**Multi-pronged approach:** Covers different FreeCAD versions and Qt bindings.

## User Experience

### Before GitPDM Enhancement:
```
1. User opens circle.FCStd from repo browser
2. User edits the file
3. User clicks File → Save As...
4. Dialog opens to: C:\Users\Ryank\Documents\FreeCAD\
   (last used directory from a different project!)
5. User saves file there (accidentally)
6. File is now outside the repo!
7. Git doesn't see changes
8. Confusion ensues
```

### After GitPDM Enhancement:
```
1. User opens circle.FCStd from repo browser
2. GitPDM sets working directory: C:\Projects\MyProject\
3. User edits the file
4. User clicks File → Save As...
5. Dialog opens to: C:\Projects\MyProject\  ✓
   (correct repo folder!)
6. User saves file in repo (default behavior)
7. Git tracks changes ✓
8. No confusion ✓
```

## Worktree Support

This works seamlessly with worktrees:

**Main Repo:**
```
Current repo: C:\Projects\MyProject\
Working directory: C:\Projects\MyProject\
Save As dialog: C:\Projects\MyProject\  ✓
```

**Feature-A Worktree:**
```
Current repo: C:\Projects\MyProject-feature-a\
Working directory: C:\Projects\MyProject-feature-a\
Save As dialog: C:\Projects\MyProject-feature-a\  ✓
```

**Result:** Each worktree has its own working directory. No cross-contamination!

## Testing

### Manual Test:

1. **Open GitPDM and select a repo:**
   ```
   Repo Path: C:\Projects\MyProject
   ```

2. **Verify working directory in FreeCAD Python console:**
   ```python
   import os
   print(os.getcwd())
   # Should show: C:\Projects\MyProject
   ```

3. **Open a file from Repository Browser:**
   - Double-click circle.FCStd

4. **Check working directory again:**
   ```python
   import os
   print(os.getcwd())
   # Should still show: C:\Projects\MyProject
   ```

5. **Try File → Save As...:**
   - Dialog should default to: `C:\Projects\MyProject\`
   - Not some random previous location!

6. **Wait 15 seconds and recheck:**
   ```python
   import os
   print(os.getcwd())
   # Should STILL show: C:\Projects\MyProject
   ```

7. **Switch to a worktree:**
   - Click "Switch to feature-a"
   - Accept worktree creation
   - Verify working directory: `C:\Projects\MyProject-feature-a\`

### Automated Test:

```python
# In FreeCAD Python console:
import os
import FreeCAD

# Get GitPDM panel
mw = FreeCADGui.getMainWindow()
dock = mw.findChild(QtWidgets.QDockWidget, "GitPDM")
panel = dock.widget()

# Check current repo
print(f"Current repo: {panel._current_repo_root}")

# Check Python working directory
print(f"Python cwd: {os.getcwd()}")

# They should match!
assert os.getcwd() == panel._current_repo_root, "Working directory mismatch!"

print("✓ Working directory correctly set to repo folder")
```

## Edge Cases Handled

### 1. FreeCAD Resets Working Directory
**Scenario:** FreeCAD or another addon changes `os.chdir()` to a different location.

**Solution:** Periodic refresh (every 10 seconds) detects drift and resets to repo folder.

**Log output:**
```
Working directory drifted to C:\Users\Ryank, resetting to C:\Projects\MyProject
```

### 2. Invalid Repo Path
**Scenario:** User hasn't selected a valid repo yet.

**Solution:** Working directory is not set (no valid path to set).

**Behavior:** FreeCAD's default working directory remains active until repo is validated.

### 3. Multiple Worktrees Open Simultaneously
**Scenario:** User has multiple FreeCAD instances with different worktrees.

**Solution:** Each GitPDM instance maintains its own `_current_repo_root` and sets working directory independently.

**Result:** Each FreeCAD instance has the correct working directory for its worktree.

### 4. User Manually Changes Working Directory
**Scenario:** User runs `os.chdir()` in FreeCAD Python console.

**Solution:** Next periodic refresh (within 10 seconds) resets to repo folder.

**Tradeoff:** User's manual change is overridden, but repo health is protected.

## Benefits

### ✅ Repo Health Protection
- Files always saved in repo (by default)
- No orphaned files outside repo
- Git tracks all changes

### ✅ User Convenience
- Save As dialog defaults to correct location
- No manual navigation required
- Less cognitive load

### ✅ Worktree Safety
- Each worktree has correct working directory
- No cross-contamination between branches
- Clear separation of contexts

### ✅ Automatic Maintenance
- Working directory maintained without user intervention
- Resilient to drift from other sources
- Works across FreeCAD sessions

## Code Changes Summary

### Modified Methods:
1. **`_validate_repo_path()`** - Sets working directory when repo is validated
2. **`_open_repo_file()`** - Sets working directory before and after opening files
3. **`_deferred_initialization()`** - Starts periodic working directory refresh

### New Methods:
1. **`_set_freecad_working_directory(directory)`** - Multi-method approach to set working directory
2. **`_start_working_directory_refresh()`** - Initializes 10-second refresh timer
3. **`_refresh_working_directory()`** - Periodic check and reset of working directory

### Logging:
- `log.debug("Set Python working directory: ...")` - When working directory is set
- `log.debug("Set FreeCAD FileOpenSavePath: ...")` - When FreeCAD parameter is set
- `log.debug("Working directory drifted..., resetting...")` - When drift is detected and corrected

## Troubleshooting

### "Save As dialog still opens to wrong directory"
**Possible causes:**
1. FreeCAD caches file dialog paths in its own settings
2. Qt file dialog has its own memory

**Solutions:**
- Check FreeCAD logs for "Set Python working directory" messages
- Manually test: `import os; print(os.getcwd())` in FreeCAD console
- Restart FreeCAD to clear dialog cache

### "Working directory changes back after a while"
**Possible causes:**
1. Another FreeCAD addon is changing it
2. User running commands in Python console

**Solutions:**
- Check logs for "Working directory drifted" messages
- Periodic refresh should restore it within 10 seconds
- If persistent, investigate other addons

### "Multiple worktrees interfere with each other"
**Possible causes:**
1. Multiple FreeCAD instances sharing global state

**Solutions:**
- Each instance should have independent GitPDM panel
- Check that `_current_repo_root` is different in each
- Logs should show different paths for each instance

## Summary

GitPDM now **automatically manages FreeCAD's working directory** to ensure:
- ✅ Save As dialogs default to the current repo/worktree folder
- ✅ Users don't accidentally save files outside the repo
- ✅ Repo health is maintained
- ✅ Worktrees are properly isolated

This prevents a common source of repo health issues and user confusion, making GitPDM safer and more user-friendly.
