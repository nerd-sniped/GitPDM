# GitPDM - Git-based Product Data Management for FreeCAD

## Overview

GitPDM is a FreeCAD workbench addon that integrates Git-based version control
workflows into FreeCAD, with a focus on GitHub Desktop-style user experience.

**Current Version:** 0.1.0 (Sprint 0 - Foundation)

## Features (Sprint 0)

- Dockable panel interface
- Repository path selection and persistence
- Placeholder UI for future git operations:
  - Repository status display
  - Changes list
  - Branch management
  - Fetch/Pull/Push/Commit actions
  - Repository browser
- Settings persistence using FreeCAD's parameter store
- Logging to FreeCAD console

## Installation

### Manual Installation

1. Locate your FreeCAD user Mod directory:
   - **Windows:** `%APPDATA%\FreeCAD\Mod\`
   - **Linux:** `~/.FreeCAD/Mod/`
   - **macOS:** `~/Library/Application Support/FreeCAD/Mod/`

2. Copy the entire `GitPDM` folder into the Mod directory:
   ```
   Mod/
   └── GitPDM/
       ├── Init.py
       ├── InitGui.py
       ├── freecad_gitpdm/
       └── docs/
   ```

3. Restart FreeCAD.

### Verify Installation

1. After restarting FreeCAD, open the workbench selector dropdown.
2. You should see "Git PDM" in the list.
3. Switch to the "Git PDM" workbench.

## Usage

### Opening the Panel

1. Switch to the "Git PDM" workbench using the workbench selector.
2. Click the "Toggle GitPDM Panel" button in the toolbar, or select it from
   the "Git PDM" menu.
3. The dock panel will appear (typically on the right side).

### Selecting a Repository

1. In the "Repository" section, click the "Browse..." button.
2. Navigate to a folder containing a git repository (or any folder for now).
3. The path will be saved and restored when you restart FreeCAD.

### Current Limitations (Sprint 0)

- No actual git operations are performed yet.
- All action buttons (Fetch, Pull, Commit, Push, Publish) are disabled.
- The changes list and repository browser are placeholders.
- Repository validation is not implemented.

### GitHub Authentication

GitPDM includes GitHub OAuth authentication for future features like
release creation and pull request management. See
[OAUTH_DEVICE_FLOW.md](OAUTH_DEVICE_FLOW.md) for details on how
GitPDM authenticates with GitHub using OAuth Device Flow.

**Note**: OAuth authentication is prepared but not yet functional in
Sprint OAUTH-0. It will be enabled in Sprint OAUTH-1.

## Architecture

```
GitPDM/
├── Init.py                    # Base addon initialization
├── InitGui.py                 # GUI workbench registration
├── freecad_gitpdm/           # Main Python package
│   ├── __init__.py
│   ├── workbench.py          # Workbench utilities
│   ├── commands.py           # FreeCAD command registration
│   ├── core/                 # Core functionality
│   │   ├── __init__.py
│   │   ├── log.py           # Logging to FreeCAD console
│   │   └── settings.py      # Persistent settings
│   ├── ui/                  # User interface
│   │   ├── __init__.py
│   │   └── panel.py         # Main dock panel widget
│   ├── git/                 # Git operations (placeholder)
│   │   └── __init__.py
│   └── export/              # Export functionality (placeholder)
│       └── __init__.py
└── docs/
    └── README.md            # This file
```

## Qt Compatibility

GitPDM supports both PySide2 (Qt5) and PySide6 (Qt6), automatically detecting
which is available in your FreeCAD installation.

## Logging

GitPDM logs messages to the FreeCAD console (Report View). To see log output:

1. Enable the Report View: `View` > `Panels` > `Report view`
2. Log messages are prefixed with `[GitPDM]`

## Settings Persistence

Settings are stored in FreeCAD's parameter store at:
```
User parameter:BaseApp/Preferences/Mod/GitPDM
```

You can view/edit these manually via `Tools` > `Edit parameters...`

## Development Roadmap


### Sprint 6: Preview Export Pipeline (v1)

- Deterministic previews for the active document:
   - `preview.png` thumbnail
   - `preview.json` manifest (sorted keys, LF endings)
- Repo-scoped preset: `.freecad-pdm/preset.json`
- Output mapping (mirror-the-source-path):
   - Source: `<rel_dir>/<name>.FCStd`
   - Outputs: `previews/<rel_dir>/<name>/preview.png` and `preview.json`
- UI: "Generate Previews" button in the panel
   - Optional staging of generated files (default ON)
   - Preview status: last generated time and open folder

Preset schema (v1):

```
{
   "presetVersion": 1,
   "thumbnail": {
      "size": [512, 512],
      "projection": "orthographic",
      "view": "isometric",
      "background": "#ffffff",
      "showEdges": false
   },
   "stats": { "precision": 2 }
}
```

Notes:
- If preset missing or malformed, defaults are used with a friendly log.
- Thumbnail requires FreeCAD GUI; JSON is always written.

### Sprint 7: Preview Export Pipeline (v2) + One-Click Publish

Extended preview exports to include 3D web-view artifacts:

- **GLB Export:** Exports active document as `model.glb` (GLB preferred for web compatibility)
  - Uses FreeCAD's Mesh module with configurable tessellation
  - Fallback to STL if GLB export unavailable
  - Mesh statistics: triangle count, vertex count
- **Extended Manifest:** `preview.json` now includes:
  - `artifacts.model`: path to GLB file
  - `meshStats`: triangle and vertex counts
  - `generationWarnings`: array of non-fatal issues
- **Mesh Preset Settings:** Added to `.freecad-pdm/preset.json`:
  ```json
  {
    "mesh": {
      "linearDeflection": 0.1,
      "angularDeflectionDeg": 28.5,
      "relative": false
    }
  }
  ```

**One-Click Publish Workflow:**

The "Publish Branch" button orchestrates a complete publish workflow:

1. **Precheck:** Validates document, repository, remote, and branch status
   - Warns if branch is behind remote (offers to continue or cancel)
2. **Export Previews:** Generates PNG + JSON + GLB artifacts
3. **Stage Files:** Stages source document and all preview artifacts
4. **Commit:** Creates commit with user-provided message
   - Default message: "Publish <filename> (GitPDM)"
5. **Push:** Pushes commit to remote repository

Features:
- Modal progress dialog with step-by-step feedback
- Friendly error handling for each step
- Automatic status refresh after success
- Works seamlessly with Git LFS for large binary files

**Git LFS Recommendations:**

For optimal performance with large FreeCAD files and GLB models:

1. Install Git LFS: https://git-lfs.github.com/
2. Track binary files in `.gitattributes`:
   ```
   *.FCStd filter=lfs diff=lfs merge=lfs -text
   *.glb filter=lfs diff=lfs merge=lfs -text
   ```
3. Run `git lfs install` in your repository
 

## Requirements
- Git (for future functionality)

## Troubleshooting

### Workbench doesn't appear

1. Check that the folder structure is correct in your Mod directory.
2. Look for errors in FreeCAD's Report View during startup.
3. Try `Tools` > `Customize` > `Workbenches` to see if it's listed but hidden.

### Panel doesn't open

1. Check the Report View for error messages.
2. Ensure you're in the "Git PDM" workbench.
3. Try restarting FreeCAD.

### Settings not saving

1. Check FreeCAD has write permissions to its user config directory.
2. Manually verify parameters at `Tools` > `Edit parameters...` >
   `BaseApp/Preferences/Mod/GitPDM`

## License

MIT License (to be confirmed)

## Contributing

This is Sprint 0 - foundation code. Future contributions welcome!

## Support

For issues or questions, please refer to the project repository.
