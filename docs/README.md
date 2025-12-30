# GitPDM - Git-based Product Data Management for FreeCAD

## Overview

GitPDM is a FreeCAD workbench addon that integrates Git-based version control and GitHub workflows into FreeCAD, providing a streamlined PDM (Product Data Management) experience for CAD files.

**Current Version:** 0.8.0 (Production Ready)

## Key Features

### ✅ Git Integration
- **Repository Management**: Clone, create, and manage Git repositories directly from FreeCAD
- **Branch Operations**: Create, switch, and delete branches with safety guards to prevent file corruption
- **Commit & Push**: Stage changes, write commit messages, and push to remote repositories
- **Fetch & Pull**: Keep your local repository synchronized with remote changes
- **Status Display**: Real-time view of modified files, branch status, and ahead/behind counts

### ✅ GitHub Integration
- **OAuth Authentication**: Secure GitHub login using OAuth Device Flow
- **Repository Browser**: Browse and clone your GitHub repositories  
- **Create Repositories**: Initialize new GitHub repositories with one click
- **Identity Verification**: Verify and display your GitHub account information

### ✅ Preview Export Pipeline  
- **Automatic Previews**: Generate preview.png thumbnails and preview.json manifests
- **3D Model Export**: Export GLB/OBJ/STL files for web viewing and 3D printing
- **One-Click Publish**: Complete workflow from export to commit to push
- **Configurable Presets**: Customize thumbnail size, mesh quality, and export settings via `.freecad-pdm/preset.json`

### ✅ Worktree Support
- **Per-Branch Folders**: Create isolated worktrees for each branch to prevent file corruption
- **Automatic Management**: Guided workflow for creating and switching between worktrees
- **Safety Guards**: Prevents branch operations when FreeCAD files are open

### ✅ User Experience
- **Modular Architecture**: Clean, maintainable codebase with 6 specialized handler modules
- **Async Operations**: All git operations run in background without freezing UI
- **Rich Feedback**: Progress dialogs, status messages, and clear error handling
- **Cross-Platform**: Works on Windows, Linux, and macOS
- **FreeCAD Compatibility**: Supports FreeCAD 0.20, 0.21, and 1.0 with both PySide2 and PySide6

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

### Quick Start

1. **Switch to Git PDM Workbench**: Use the workbench selector dropdown
2. **Open the Panel**: Click "Toggle GitPDM Panel" button in the toolbar
3. **Connect GitHub** (optional but recommended):
   - Click "Connect GitHub" button
   - Follow the OAuth device flow instructions
   - Copy the code and authorize in your browser
4. **Set up a Repository**:
   - **Option A - Clone**: Browse GitHub repos and clone one you own
   - **Option B - Create**: Create a new GitHub repository
   - **Option C - Open**: Browse to an existing local git repository

### Working with Branches

**⚠️ IMPORTANT: Close all FreeCAD documents before branch operations!**

GitPDM includes comprehensive safety guards to prevent `.FCStd` file corruption:
- Detects open documents and lock files
- Blocks branch operations until all files are closed
- Recommends using worktrees for safer branch isolation

**Branch Workflow**:
1. Save and close all FreeCAD documents
2. Use "New Branch..." to create a new feature branch
3. GitPDM automatically switches to the new branch
4. Make your changes and commit
5. Push to set upstream tracking

**Worktree Workflow** (Recommended for complex projects):
1. Create a worktree when switching branches (GitPDM will prompt)
2. Each branch gets its own folder (e.g., `MyProject-feature-x`)
3. Open files from the worktree folder
4. Switch between worktrees by opening different folders in FreeCAD

### Committing Changes

1. Make changes to your `.FCStd` files and save
2. Modified files appear in the "Changes" section
3. Review the changes in the file list
4. Enter a commit message
5. Click "Commit" to create the commit
6. Click "Push" to send changes to GitHub

### One-Click Publish Workflow

The "Publish Branch" button executes a complete workflow:
1. **Precheck**: Validates document, repo, remote, and branch status
2. **Export Previews**: Generates PNG thumbnail + JSON manifest + GLB/STL model
3. **Stage Files**: Stages source file and all preview artifacts  
4. **Commit**: Creates commit with your message
5. **Push**: Pushes to remote repository

**Benefits**:
- Automatic preview generation for web viewing
- Single-click operation from edit to published
- Works seamlessly with Git LFS for large files
- Progress dialog with step-by-step feedback

### Preview Export Configuration

Create a `.freecad-pdm/preset.json` file in your repository root to customize export settings:

```json
{
  "presetVersion": 1,
  "thumbnail": {
    "size": [512, 512],
    "projection": "orthographic",
    "view": "isometric",
    "background": "#ffffff",
    "showEdges": false
  },
  "mesh": {
    "linearDeflection": 0.1,
    "angularDeflectionDeg": 28.5,
    "relative": false
  },
  "stats": {
    "precision": 2
  }
}
```

### Git LFS Recommendations

For large FreeCAD files and 3D models, configure Git LFS:

1. Install Git LFS: https://git-lfs.github.com/
2. Create `.gitattributes` in repository root:
   ```
   *.FCStd filter=lfs diff=lfs merge=lfs -text
   *.glb filter=lfs diff=lfs merge=lfs -text
   *.stl filter=lfs diff=lfs merge=lfs -text
   ```
3. Run `git lfs install` in your repository
4. Git will automatically use LFS for tracked file types

## Architecture

GitPDM follows a modular architecture with clear separation of concerns:

```
GitPDM/
├── Init.py                           # Addon initialization
├── InitGui.py                        # Workbench registration
├── freecad_gitpdm/                  # Main package
│   ├── __init__.py
│   ├── workbench.py                 # Workbench definition
│   ├── commands.py                  # FreeCAD commands
│   │
│   ├── core/                        # Core functionality
│   │   ├── diagnostics.py           # System diagnostics
│   │   ├── jobs.py                  # Async job runner
│   │   ├── log.py                   # Logging system
│   │   ├── paths.py                 # Path safety utilities
│   │   ├── publish.py               # Publish workflow coordinator
│   │   ├── scaffold.py              # Project scaffolding
│   │   └── settings.py              # Settings persistence
│   │
│   ├── ui/                          # User interface (Sprint 4: Refactored)
│   │   ├── panel.py                 # Main dock widget (1998 lines, down from 5042)
│   │   ├── dialogs.py               # Modal dialogs
│   │   ├── new_repo_wizard.py       # Repository creation wizard
│   │   ├── repo_picker.py           # GitHub repository selector
│   │   ├── github_auth.py           # OAuth authentication handler (501 lines)
│   │   ├── file_browser.py          # File tree browser handler (483 lines)
│   │   ├── fetch_pull.py            # Fetch/pull operations handler (370 lines)
│   │   ├── commit_push.py           # Commit/push operations handler (560 lines)
│   │   ├── repo_validator.py        # Repository validation handler (396 lines)
│   │   └── branch_ops.py            # Branch operations handler (673 lines)
│   │
│   ├── auth/                        # Authentication
│   │   ├── oauth_device_flow.py     # OAuth Device Flow implementation
│   │   ├── token_store.py           # Token storage interface
│   │   ├── token_store_wincred.py   # Windows credential store
│   │   ├── config.py                # OAuth configuration
│   │   └── keys.py                  # OAuth client credentials
│   │
│   ├── git/                         # Git operations
│   │   └── client.py                # Git subprocess wrapper (1855 lines)
│   │
│   ├── github/                      # GitHub API
│   │   ├── api_client.py            # GitHub REST API client
│   │   ├── cache.py                 # Repository list caching
│   │   ├── create_repo.py           # Repository creation
│   │   ├── errors.py                # Error handling
│   │   ├── identity.py              # User identity verification
│   │   └── repos.py                 # Repository listing
│   │
│   └── export/                      # Preview export pipeline
│       ├── exporter.py              # PNG/JSON/GLB export (825 lines)
│       ├── preset.py                # Preset configuration loader
│       ├── mapper.py                # Path mapping utilities
│       └── stl_converter.py         # OBJ to STL converter
│
└── docs/
    ├── README.md                    # This file
    ├── STRUCTURE.txt                # Detailed structure notes
    ├── OAUTH_DEVICE_FLOW.md         # OAuth documentation
    └── BRANCH_SYSTEM_STATUS.md      # Branch implementation notes
```

### Handler Pattern (Sprint 4)

The UI layer uses a handler pattern for maintainability:
- **panel.py**: Main coordinator (1998 lines, 60% reduction)
- **Specialized Handlers**: Each major feature has its own handler module
- **Public APIs**: Clean interfaces between panel and handlers
- **Delegation**: Panel delegates operations to handlers
- **State Management**: Handlers own their feature-specific state

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

### ✅ Sprint 0: Foundation (Complete)
- Addon scaffolding and workbench registration
- Dockable panel UI with placeholder sections
- Settings persistence using FreeCAD parameters
- Logging infrastructure
- Qt compatibility (PySide2/PySide6)

### ✅ Sprint 1-3: Core Git & GitHub Integration (Complete)
- Git client wrapper with subprocess-based operations
- GitHub OAuth Device Flow authentication
- Repository validation and status display
- Branch management (create, switch, delete)
- Commit and push operations
- Fetch and pull with merge handling
- GitHub repository browser and cloning
- Repository creation wizard

### ✅ Sprint 4: Panel Decomposition (Complete)
**Objective**: Refactor monolithic 5042-line panel.py into maintainable modules

**Achievements**:
- Reduced panel.py from 5042 to 1998 lines (60% reduction)
- Created 6 specialized handler modules (3,589 total lines)
  - `github_auth.py` (501 lines) - OAuth and identity management
  - `file_browser.py` (483 lines) - Repository file tree
  - `fetch_pull.py` (370 lines) - Remote synchronization
  - `commit_push.py` (560 lines) - Staging and pushing
  - `repo_validator.py` (396 lines) - Repository validation
  - `branch_ops.py` (673 lines) - Branch and worktree management
- Established handler pattern with clean delegation
- Updated architecture baseline enforcement
- All 22 tests passing

### ✅ Sprint 5 (In Progress): Documentation & Polish
**Current Task**: Update documentation to reflect current feature set
- Comprehensive README with installation and usage guides
- User documentation for all workflows
- Code quality improvements
- Enhanced logging and diagnostics

### ✅ Sprint 6: Preview Export Pipeline v1 (Complete)

Deterministic preview generation for CAD files:
- `preview.png` thumbnail (configurable size, view, projection)
- `preview.json` manifest with metadata and stats
- Repo-scoped preset configuration (`.freecad-pdm/preset.json`)
- Path mapping: Source `<rel_dir>/<name>.FCStd` → Previews `previews/<rel_dir>/<name>/`
- Optional auto-staging of preview files

### ✅ Sprint 7: Preview Export v2 + One-Click Publish (Complete)

Extended preview pipeline and complete publish workflow:
- **GLB/OBJ/STL Export**: 3D models for web viewing and 3D printing
- **Mesh Statistics**: Triangle and vertex counts in manifest
- **Configurable Tessellation**: Mesh quality settings in preset
- **One-Click Publish**: Complete workflow (precheck → export → stage → commit → push)
- **Progress Feedback**: Modal dialog with step-by-step status
- **Git LFS Support**: Optimized for large binary files

### Future Enhancements
- Pull request workflow integration
- Conflict resolution UI
- Multiple repository support
- Tag and release management
- Advanced git operations (rebase, cherry-pick, stash)
- Team collaboration features
 

## Requirements

- **FreeCAD**: Version 0.20, 0.21, or 1.0
- **Git**: Installed and available in system PATH
- **Python**: Bundled with FreeCAD (no additional install needed)
- **Internet**: Required for GitHub features and OAuth authentication

## Troubleshooting

### Workbench doesn't appear

1. Verify folder structure: `Mod/GitPDM/Init.py` and `Init Gui.py` must exist
2. Check FreeCAD's Report View (View → Panels → Report view) for startup errors
3. Try `Tools` > `Customize` > `Workbenches` to see if it's listed but hidden
4. Restart FreeCAD after installation

### Panel doesn't open

1. Ensure you're in the "Git PDM" workbench (check workbench selector)
2. Check Report View for error messages when clicking the toggle button
3. Try closing and reopening FreeCAD
4. Verify Qt libraries are available (PySide2 or PySide6)

### Git operations fail

1. Verify Git is installed: Open terminal and run `git --version`
2. Ensure Git is in system PATH
3. Check repository is valid: `.git` folder must exist
4. Review error messages in Report View for specific issues

### GitHub authentication fails

1. Check internet connection
2. Verify OAuth app credentials in `freecad_gitpdm/auth/keys.py`
3. Try disconnecting and reconnecting GitHub
4. Check Report View for detailed error messages
5. Ensure system time is correct (OAuth requires accurate time)

### Branch operations blocked

**This is intentional!** GitPDM blocks branch operations when FreeCAD files are open to prevent corruption.

**Solution**:
1. Save all work: `File` > `Save`
2. Close all documents: `File` > `Close All`
3. Retry the branch operation
4. Reopen files after branch switch completes

**Why**: `.FCStd` files are ZIP archives. Git operations that modify files while they're open in FreeCAD can corrupt the internal structure, making files unreadable.

### Preview export fails

1. Ensure active document is saved
2. Check document has visible 3D shapes
3. Verify FreeCAD GUI is running (headless mode limitations)
4. Review preset configuration in `.freecad-pdm/preset.json`
5. Check disk space for output files

### Settings not saving

1. Check FreeCAD has write permissions to config directory
2. Manually verify at `Tools` > `Edit parameters...` > `BaseApp/Preferences/Mod/GitPDM`
3. Try running FreeCAD as administrator (Windows) or with proper permissions

### Performance issues

1. **Large repositories**: Consider using Git LFS for `.FCStd` files
2. **Slow file tree**: Repositories with thousands of files may take time to load
3. **Network delays**: Fetch/pull operations depend on internet speed
4. **Background operations**: Check if git operations are still running (busy indicators)

## License

MIT License (to be confirmed)

## Contributing

GitPDM is production-ready but welcomes contributions:
- Bug reports and feature requests via GitHub Issues
- Pull requests with tests and documentation
- Documentation improvements
- Platform testing (especially Linux and macOS)

## Support

For issues or questions:
1. Check this README's Troubleshooting section
2. Review FreeCAD's Report View for error details
3. Check existing GitHub Issues
4. Open a new Issue with system details and error logs
