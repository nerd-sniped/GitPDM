# GitPDM Installation & Testing Guide

## Quick Install (Windows)

1. Copy the GitPDM folder to FreeCAD's Mod directory:
   ```powershell
   # Find your FreeCAD Mod directory
   cd %APPDATA%\FreeCAD\Mod
   
   # Copy GitPDM folder here
   # Expected structure:
   # %APPDATA%\FreeCAD\Mod\GitPDM\Init.py
   # %APPDATA%\FreeCAD\Mod\GitPDM\InitGui.py
   # %APPDATA%\FreeCAD\Mod\GitPDM\freecad_gitpdm\...
   ```

2. Restart FreeCAD

## Testing Checklist

### 1. Verify Workbench Appears
- [ ] Open FreeCAD
- [ ] Open workbench dropdown (top toolbar)
- [ ] Verify "Git PDM" appears in the list
- [ ] Switch to "Git PDM" workbench

### 2. Verify Panel Opens
- [ ] Click "Toggle GitPDM Panel" toolbar button
- [ ] Panel should appear (usually on right side)
- [ ] Panel title should be "Git PDM"

### 3. Test Repository Selector
- [ ] Click "Browse..." button
- [ ] Select any folder
- [ ] Verify path appears in text field
- [ ] Verify "Not validated (Sprint 0)" message appears

### 4. Test Settings Persistence
- [ ] Enter or browse to a repository path
- [ ] Close FreeCAD completely
- [ ] Reopen FreeCAD
- [ ] Switch to "Git PDM" workbench
- [ ] Open the panel
- [ ] Verify the repository path is still there

### 5. Check Console Output
- [ ] Enable Report View: View > Panels > Report view
- [ ] Look for "[GitPDM]" prefixed messages
- [ ] Should see:
  - "GitPDM workbench activated"
  - "Creating GitPDM dock panel"
  - "GitPDM dock panel initialized"
  - "Saved repo path: ..." (when you select a folder)

### 6. Verify UI Sections
Panel should contain these sections (top to bottom):
- [ ] Repository (text field + Browse button + validation label)
- [ ] Status (Branch: —, Sync: —)
- [ ] Changes (empty list, disabled)
- [ ] Actions (Fetch, Pull, Commit, Push, Publish buttons - all disabled)
- [ ] Repository Browser (tree widget, disabled)

### 7. Test Toggle Behavior
- [ ] Click toolbar button to hide panel
- [ ] Click again to show panel
- [ ] Panel should toggle on/off

### 8. Check for Errors
- [ ] No Python exceptions in Report View
- [ ] No red error messages
- [ ] Addon loads cleanly on startup

## Troubleshooting

### "Git PDM doesn't appear in workbench list"
- Check folder structure matches exactly
- Look for errors in Report View during FreeCAD startup
- Verify Init.py and InitGui.py are in GitPDM/ root

### "Panel doesn't open"
- Check Report View for Python errors
- Verify you're in "Git PDM" workbench before clicking button
- Try View > Panels menu to see if "Git PDM" is listed there

### "Path not saving"
- Check FreeCAD has write permissions
- Manually check: Tools > Edit parameters > BaseApp > Preferences > Mod > GitPDM
- Should see "RepoPath" parameter

### "Qt import errors"
- Verify FreeCAD installation includes PySide2 or PySide6
- Check FreeCAD version (requires 1.0+)

## Expected Behavior (Sprint 0)

**WORKING:**
- Workbench loads and appears in selector
- Panel opens and closes
- Repository path can be selected
- Settings persist across restarts
- Console logging works

**NOT YET IMPLEMENTED:**
- Git repository validation
- Actual git operations (status, fetch, pull, push, commit)
- Branch switching
- Changes detection
- Repository browsing
- All action buttons are intentionally disabled

## Next Steps (Future Sprints)

- Sprint 1: Git repository detection and status display
- Sprint 2: Branch operations
- Sprint 3: Fetch/Pull
- Sprint 4: Commit/Push
- Sprint 5: FreeCAD export integration
