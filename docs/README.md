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

- **Sprint 0 (Current):** Project foundation and UI skeleton ✓
- **Sprint 1:** Basic git repository detection and status display
- **Sprint 2:** Branch switching and history viewing
- **Sprint 3:** Fetch and pull operations
- **Sprint 4:** Commit and push operations
- **Sprint 5:** FreeCAD document export integration

## Requirements

- FreeCAD 1.0 or later
- Python 3.8+ (bundled with FreeCAD)
- PySide2 or PySide6 (bundled with FreeCAD)
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
