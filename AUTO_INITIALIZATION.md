# GitPDM Auto-Initialization (Sprint 7)

## Overview
GitPDM now **automatically initializes** when you open a Git repository. No manual setup required!

## What Changed

### Before (v1.0.0)
❌ Manual initialization required:
1. Open repository
2. Right-click in file browser
3. Click "Initialize GitPDM"
4. Navigate confusing wizard with deprecated GitCAD references
5. Click "Initialize GitPDM" button
6. Wait for confirmation dialog
7. **THEN** lock/unlock options appeared

### After (Sprint 7)
✅ Automatic initialization:
1. Open repository
2. **Everything just works!**
   - Lock/unlock options appear immediately
   - Multi-select bulk operations available
   - No wizard, no manual steps

## Technical Details

### Auto-Initialization Points
GitPDM automatically initializes at two key points:

1. **Repository Changed** (`panel.py` → `_on_repository_changed()`)
   - When you select a different repository from the dropdown
   - Creates `.gitpdm/config.json` silently if not present

2. **Repository Validated** (`repo_validator.py` → `_handle_valid_repo()`)
   - When opening a repository that's already been used
   - Ensures config exists before enabling lock operations

### What Gets Created
- **`.gitpdm/config.json`** - Configuration file with sensible defaults:
  ```json
  {
    "fcstd_compress": true,
    "fcstd_export_step": true,
    "fcstd_export_stl": false,
    "fcstd_lfs": true,
    "fcstd_git_filter": false
  }
  ```

### Simplified Wizard
The initialization wizard has been completely rewritten:

#### Removed
- ❌ FreeCAD_Automation folder detection (deprecated)
- ❌ GitCAD reference lookup (consolidated in Sprint 3)
- ❌ Confusing "Sprint 4 deprecation" warnings
- ❌ Manual 3-step setup instructions
- ❌ Copying automation scripts

#### Added
- ✅ Clear description of what GitPDM does
- ✅ Simple one-click initialization (if auto-init fails)
- ✅ Helpful next steps after initialization
- ✅ Check for existing config (reinitialize prompt)

### New Functions

#### `auto_initialize_if_needed(repo_root: str) -> bool`
- **Purpose**: Silently create `.gitpdm/config.json` if not present
- **Called**: Automatically when repository is opened/changed
- **Returns**: `True` if initialization was performed, `False` if already initialized
- **Location**: `freecad/gitpdm/ui/init_wizard.py`

#### `show_init_wizard(repo_root: str, parent=None) -> bool`
- **Purpose**: Manual initialization (fallback/repair)
- **Called**: From context menu (still available for edge cases)
- **Returns**: `True` if user completed wizard successfully
- **Location**: `freecad/gitpdm/ui/init_wizard.py`

## User Experience

### First Time Opening Repository
1. User selects repository from dropdown
2. GitPDM Panel: "Checking..." → "OK" (green)
3. **Silent initialization happens in background**
4. File browser populates with files
5. Lock/unlock context menu options **immediately available**
6. Multi-select works right away

### Already Initialized Repository
1. User selects repository
2. GitPDM checks for `.gitpdm/config.json`
3. Config found → skip initialization
4. Everything works as expected

### Edge Case: Corrupted Config
1. User can still right-click → "Initialize GitPDM"
2. Wizard shows: "Already Initialized - Reinitialize?"
3. User confirms → config recreated with defaults

## Benefits

### For Users
- ✅ **Zero configuration** - just open a repo and go
- ✅ **No confusing wizards** - silent background setup
- ✅ **Faster workflow** - lock files immediately after opening repo
- ✅ **Better first impression** - features "just work"

### For Developers
- ✅ **Cleaner codebase** - removed 100+ lines of deprecated GitCAD logic
- ✅ **Better error handling** - auto-init catches missing configs
- ✅ **Easier testing** - predictable initialization behavior
- ✅ **Future-proof** - no more references to old GitCAD structure

## Testing Checklist

### Test 1: New Repository (Never Used GitPDM)
- [ ] Create new git repository
- [ ] Select it in GitPDM dropdown
- [ ] Verify `.gitpdm/config.json` created automatically
- [ ] Verify lock/unlock options appear in context menu
- [ ] Try locking a file - should work immediately

### Test 2: Existing Repository (Already Has Config)
- [ ] Open repository with existing `.gitpdm/config.json`
- [ ] Verify no duplicate config created
- [ ] Verify log message: "GitPDM configuration detected"
- [ ] Verify all features work normally

### Test 3: Corrupted Config
- [ ] Delete or corrupt `.gitpdm/config.json`
- [ ] Reopen repository in GitPDM
- [ ] Verify config auto-recreated
- [ ] Verify features work after recreation

### Test 4: Manual Initialization (Fallback)
- [ ] Delete `.gitpdm/config.json`
- [ ] Right-click in file browser → "Initialize GitPDM"
- [ ] Verify simplified wizard appears (no GitCAD references)
- [ ] Complete wizard
- [ ] Verify config created and features work

### Test 5: Reinitialize Existing
- [ ] Open initialized repository
- [ ] Right-click → "Initialize GitPDM"
- [ ] Verify prompt: "Already Initialized - Reinitialize?"
- [ ] Click Yes → verify config recreated
- [ ] Click No → verify nothing changes

## Migration Notes

### Upgrading from v1.0.0
Users with existing GitPDM repositories:
- **No action required** - existing `.gitpdm/config.json` files work as-is
- **New repositories** will auto-initialize on first open
- **Manual initialization** still available via context menu

### Removed Features
- ❌ FreeCAD_Automation folder (deprecated in Sprint 4)
- ❌ GitCAD reference detection (consolidated in Sprint 3)
- ❌ Manual 3-step setup wizard

### New Behavior
- ✅ Silent auto-initialization on repository open
- ✅ Simplified wizard for manual init (rare)
- ✅ Reinitialize option for repairing configs

## Files Modified

### Core Changes
1. **`freecad/gitpdm/ui/init_wizard.py`** (280 lines → 170 lines)
   - Removed FreeCAD_Automation logic
   - Added `auto_initialize_if_needed()` function
   - Simplified wizard UI

2. **`freecad/gitpdm/ui/panel.py`** (2148 lines)
   - Added auto-init call in `_on_repository_changed()`
   - Refreshes lock handler after initialization

3. **`freecad/gitpdm/ui/repo_validator.py`** (456 lines)
   - Added auto-init call in `_handle_valid_repo()`
   - Ensures initialization before checking lock availability

## Future Enhancements

### Possible Improvements
1. **One-Time Notification**
   - Show toast: "GitPDM initialized for this repository"
   - Only on first initialization
   - Dismissible/never show again option

2. **Config Migration**
   - Detect old GitCAD configs
   - Auto-migrate to modern `.gitpdm/config.json`
   - Show summary of changes

3. **Team Settings**
   - Detect `.gitpdm/config.json` in remote repo
   - Pull team settings automatically
   - Show "Team settings applied" notification

## Conclusion

Auto-initialization dramatically improves the GitPDM user experience by removing manual setup steps. Users can now:
- Open a repository
- Start locking files immediately
- Use multi-select bulk operations right away
- Never see confusing deprecated messages

This completes Sprint 7's goal of **seamless, automatic initialization** for GitPDM v1.1.0.

---
**Sprint**: 7  
**Version**: 1.1.0-dev  
**Date**: 2024  
**Status**: ✅ Complete
