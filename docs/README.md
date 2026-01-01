# GitPDM - Git-based Product Data Management for FreeCAD

**Version Control Made Simple for Your CAD Projects**

GitPDM is a FreeCAD workbench addon that brings Git version control and GitHub collaboration directly into FreeCAD. Think of it as “version history” for CAD projects, designed around FreeCAD documents, previews, and publishing.

**Current Version:** 0.8.0 (Production Ready)

---

## Documentation Structure

This documentation is organized into four sections. Each section is intended to stand alone with minimal cross-references.

- **[Tutorials](#tutorials)** — learning-oriented lessons for newcomers
- **[How-To Guides](#how-to-guides)** — goal-oriented recipes for specific tasks
- **[Technical Reference](#technical-reference)** — accurate, “lookup-style” system details
- **[Explanations](#explanations)** — background concepts and context to build understanding

---

# Tutorials

Learning-oriented lessons that teach GitPDM by example.

## Tutorial 1: First Local Versioned CAD Project

**Goal:** Install GitPDM, create a repository, and make two commits.

**Prerequisites:**
- FreeCAD (0.20, 0.21, or 1.0)
- Git installed and available on PATH (`git --version` works)

### 1) Install GitPDM (manual)

1. Find your FreeCAD Mod folder:
   - **Windows**: Press `Windows + R`, enter `%APPDATA%\FreeCAD\Mod`
   - **macOS**: Finder → `Cmd + Shift + G` → `~/Library/Application Support/FreeCAD/Mod`
   - **Linux**: `~/.FreeCAD/Mod/`
   - Create the folder if it doesn't exist.

2. Download the latest GitPDM release:
   - https://github.com/nerd-sniped/GitPDM/releases

3. Copy the extracted `GitPDM` folder into the Mod folder so you have:
   - `Mod/GitPDM/Init.py`
   - `Mod/GitPDM/InitGui.py`
   - `Mod/GitPDM/freecad_gitpdm/`

4. Restart FreeCAD.

5. In the workbench dropdown, select **Git PDM**.

### 2) Create a repository

1. In the Git PDM toolbar, click **Toggle GitPDM Panel**.
2. In the panel, click **Browse for Folder**.
3. Create/select an empty folder for your project (example: `Documents/FreeCAD Projects/MyFirstProject`).
4. Click **Create Repo**.

### 3) Create and save a simple part

1. Switch to **Part Design** workbench.
2. Create a new document: **File → New**.
3. Create a simple box:
   - Create Body → Create Sketch (XY)
   - Draw a rectangle → Close
   - Pad → length 10mm
4. Save inside the repository folder as `simple-box.FCStd`.

### 4) Commit v1

1. Switch back to **Git PDM** workbench.
2. In the panel, confirm `simple-box.FCStd` shows up under Changes.
3. Enter commit message:
   ```
   Add simple box part for testing
   ```
4. Click **Commit**.

### 5) Make a change and commit v2

1. Switch to **Part Design**.
2. Edit the Pad length from 10mm to 20mm.
3. Save.
4. Switch to **Git PDM**.
5. Enter commit message:
   ```
   Increase box height to 20mm
   ```
6. Click **Commit**.

You now have a local commit history you can always return to.

---

## Tutorial 2: Connect to GitHub and Push for Backup

**Goal:** Authenticate to GitHub and push your local commits.

**Prerequisites:**
- Completed Tutorial 1
- A GitHub account

### 1) Connect GitHub (device flow)

1. In the GitPDM panel, click **Connect GitHub**.
2. A dialog appears with a short code.
3. Click the dialog button to open GitHub (or visit https://github.com/login/device).
4. Log in, enter the code, and click **Authorize**.
5. Return to FreeCAD and confirm it shows “Connected”.

### 2) Push

1. In the GitPDM panel, click **Push**.
2. If prompted to set up the remote repository, follow the instructions shown.
3. After success, verify your repo on GitHub at:
   - `https://github.com/YOUR_USERNAME/YOUR_REPO_NAME`

---

## Tutorial 3: Publish a Part with Previews

**Goal:** Use the one-click publish flow to generate previews and push them.

**Prerequisites:**
- A saved FreeCAD document inside a Git repository
- GitHub connected (if you want to push)

### 1) Prepare the view

1. Open your part in FreeCAD.
2. Rotate to a nice viewing angle (the thumbnail uses the current view).

### 2) Publish

1. Switch to **Git PDM**.
2. Enter a commit message.
3. Click **Publish Branch**.

GitPDM will generate exports (PNG thumbnail, GLB model, optional STL), stage them alongside the source file, commit, and push.

---

# How-To Guides

Goal-oriented recipes for specific problems.

## How to Install GitPDM

**Goal:** Install GitPDM into FreeCAD.

1. Find your FreeCAD Mod folder:
   - Windows: `%APPDATA%\FreeCAD\Mod`
   - macOS: `~/Library/Application Support/FreeCAD/Mod`
   - Linux: `~/.FreeCAD/Mod/`
2. Download a GitPDM release ZIP from https://github.com/nerd-sniped/GitPDM/releases
3. Extract it.
4. Copy the `GitPDM` folder into `Mod/`.
5. Restart FreeCAD.
6. Select **Git PDM** from the workbench list.

---

## How to Fix Git PDM Doesn’t Appear in the Workbench List

**Goal:** Make the workbench show up.

1. Ensure the folder name is exactly `GitPDM` (not `GitPDM-main`).
2. Ensure `Init.py` and `InitGui.py` are directly inside `GitPDM/`.
3. Open FreeCAD’s Report View: **View → Panels → Report view**.
4. Restart FreeCAD fully.

---

## How to Install Git (Prerequisite)

**Goal:** Install Git and verify it works.

- **Windows**: install from https://git-scm.com/download/win, then restart; verify with `git --version`.
- **macOS**: run `git --version` in Terminal and install Xcode CLI tools if prompted.
- **Linux**: install via your package manager (e.g. `sudo apt install git`), verify with `git --version`.

---

## How to Use the Daily Workflow (Edit → Save → Commit → Push)

**Goal:** Safely iterate on CAD work with checkpoints and backup.

1. Open your FreeCAD file from inside the repository.
2. Make changes.
3. **Save** in FreeCAD.
4. Switch to **Git PDM**.
5. Write a commit message.
6. Click **Commit**.
7. Click **Push**.

---

## How to Fetch and Pull Updates

**Goal:** Get the latest commits from GitHub.

1. Click **Fetch** (safe any time; doesn't change files).
2. If you're behind, click **Pull** to download and merge.

---

## How to Fix Push Rejected

**Goal:** Push successfully when the remote moved ahead.

1. Click **Fetch**.
2. Click **Pull**.
3. If Pull succeeds, try **Push** again.
4. If you hit conflicts, you'll need to resolve them manually (until a dedicated UI exists).

---

## How to Set Up Git LFS for CAD Files

**Goal:** Track large CAD files efficiently.

1. Install Git LFS from https://git-lfs.github.com/.
2. In your repository, run:
   ```
   git lfs install
   ```
3. Create or update `.gitattributes` in the repo root:
   ```
   *.FCStd filter=lfs diff=lfs merge=lfs -text
   *.glb filter=lfs diff=lfs merge=lfs -text
   *.stl filter=lfs diff=lfs merge=lfs -text
   *.step filter=lfs diff=lfs merge=lfs -text
   *.iges filter=lfs diff=lfs merge=lfs -text
   ```
4. Commit and push:
   ```
   git add .gitattributes
   git commit -m "Configure Git LFS for CAD files"
   git push
   ```

---

## How to Organize a Multi-Part Project

**Goal:** Keep parts, assemblies, exports, and docs tidy.

Recommended structure:

```
MyProject/
 parts/
    base-plate.FCStd
    motor-mount.FCStd
 assemblies/
    main-assembly.FCStd
 exports/
    base.step
    base.stl
 docs/
     notes.md
```

Recipe:
1. Put parts in `parts/`, assemblies in `assemblies/`.
2. Use descriptive filenames.
3. Commit assemblies and dependent parts together.

---

## How to Customize Preview Exports

**Goal:** Configure thumbnail/mesh settings.

1. Create `.freecad-pdm/preset.json` in your repository.
2. Add a preset (example):
   ```json
   {
     "presetVersion": 1,
     "thumbnail": {
       "size": [1024, 1024],
       "projection": "perspective",
       "view": "isometric",
       "background": "#2C3E50",
       "showEdges": true
     },
     "mesh": {
       "linearDeflection": 0.05,
       "angularDeflectionDeg": 20.0,
       "relative": false
     },
     "stats": {
       "precision": 3
     }
   }
   ```
3. Commit the preset.
4. Run **Publish Branch** and confirm the outputs changed.

---

## How to Switch Branches Safely (Current Workaround)

**Goal:** Avoid corrupting FreeCAD `.FCStd` files.

1. Save all documents.
2. Close all documents.
3. Switch branches.
4. Re-open documents after the switch.

---

## How to Use Worktrees for Branch Isolation

**Goal:** Work on multiple branches without repeatedly switching the same working folder.

1. Create a new worktree folder (example): `MyProject-feature-branch`.
2. Use Git’s worktree command:
   ```
   git worktree add ../MyProject-feature-branch feature-branch
   ```
3. Open the FreeCAD files from that worktree folder in a separate FreeCAD window.

---

## How to Fix “Git Is Not Recognized as a Command”

**Goal:** Make Git available to GitPDM.

1. Install Git from https://git-scm.com/.
2. Restart your computer (Windows commonly needs this).
3. Verify in a terminal:
   ```
   git --version
   ```

---

## How to Fix GitHub Authentication Failures

**Goal:** Successfully connect GitPDM to GitHub.

1. Confirm GitHub is reachable in a browser: https://github.com/
2. Confirm your system clock is correct (OAuth is time-sensitive).
3. Retry **Connect GitHub** and complete the device flow.
4. If you see “Session expired” / “Token invalid”, disconnect and connect again.
5. Check FreeCAD Report View for detailed `[GitPDM]` errors.

---

## How to Set Up Linux Token Storage (GNOME Keyring / KWallet)

**Goal:** Enable secure token storage on Linux.

1. Install packages:
   ```bash
   # Ubuntu/Debian
   sudo apt install python3-secretstorage gnome-keyring
   ```
2. Ensure a Secret Service compatible keyring daemon is running.
3. Retry **Connect GitHub** in GitPDM.

**Alternative:** If a keyring is not available (headless systems), use SSH for Git operations.

---

## How to Fix macOS Keychain Access Issues

**Goal:** Allow token storage in Keychain.

1. Retry **Connect GitHub** and approve the Keychain prompt.
2. If the prompt is blocked by system policy, consider granting FreeCAD/Python appropriate permissions in **System Settings → Privacy & Security**.

---

## How to Fix Preview Export Failures

**Goal:** Get PNG/GLB/JSON (and optional STL) exports working.

1. Confirm the document is saved inside the repository.
2. Confirm the document has visible 3D geometry.
3. Confirm FreeCAD is running in GUI mode.
4. If using `.freecad-pdm/preset.json`, confirm it is valid JSON.
5. Check Report View for the specific error.

---

## How to Speed Up a Slow Repository

**Goal:** Reduce unnecessary scanning work.

1. Add common junk files to `.gitignore`:
   ```
   __pycache__/
   *.pyc
   .DS_Store
   Thumbs.db
   ```
2. Use Git LFS for large CAD binaries.
3. Consider splitting very large projects into multiple repositories.

---

# Technical Reference

Accurate lookup documentation. Minimal narrative.

## What GitPDM Does (Current Feature Summary)

- Version control of files inside a Git repository (commit/push/pull/fetch)
- Optional GitHub integration via OAuth device flow
- Preview export and publishing pipeline (thumbnail PNG, GLB, JSON metadata, optional STL)
- Safety guards to reduce risk of file corruption during risky operations

### Known limitation: branch switching

Branch switching is currently limited because FreeCAD `.FCStd` files are ZIP archives and can be corrupted if the working directory changes while documents are open. GitPDM protects you by requiring documents to be closed for certain operations.

---

## Requirements Summary

| Requirement | Version | Notes |
|-------------|---------|-------|
| FreeCAD | 0.20, 0.21, or 1.0 | Install from https://www.freecad.org/downloads.php |
| Git | 2.20+ | Install from https://git-scm.com/ |
| Python | 3.8+ | Bundled with FreeCAD |
| PySide2 or PySide6 | Any | Bundled with FreeCAD |
| GitHub account | N/A | Optional, for cloud features |
| Git LFS | 2.0+ | Recommended for large CAD files |

---

## Platform Token Storage

GitHub tokens are stored using the host platform’s secure credential store.

- **Windows**: Windows Credential Manager
- **macOS**: Keychain
- **Linux**: Secret Service API (GNOME Keyring / KWallet)

### Linux packages for Secret Service

```bash
# Ubuntu/Debian
sudo apt install python3-secretstorage gnome-keyring

# Fedora/RHEL
sudo dnf install python3-secretstorage gnome-keyring

# Arch Linux
sudo pacman -S python-secretstorage gnome-keyring
```

---

## Preview Export Files

### Preset file

- Path: `.freecad-pdm/preset.json`
- Format: JSON

### Output layout (example)

```
previews/
 parts/
     mechanical/
         base/
             preview.png
             preview.json
             preview.glb
```

---

## Logging

GitPDM logs to FreeCAD’s Report View.

- Enable: **View → Panels → Report view**
- Look for messages prefixed with `[GitPDM]`

---

## Settings Persistence

Settings are stored in FreeCAD’s parameter store:

```
User parameter:BaseApp/Preferences/Mod/GitPDM
```

Access via: **Tools → Edit parameters...**

---

## Developer-Facing Architecture Overview

High-level modules:

- `auth/` — GitHub OAuth device flow and token storage
- `git/` — Git subprocess wrapper
- `github/` — GitHub API client
- `export/` — preview generation pipeline
- `core/` — shared utilities (logging, jobs, paths, settings)
- `ui/` — panel and handlers

---

## Roadmap & Future Development (Project Information)

### Completed milestones (high level)

- Git client wrapper and repository management (create/clone/validate)
- GitHub OAuth authentication (device flow)
- Commit/push/fetch/pull operations
- UI refactor into specialized handlers
- Preview export (PNG/GLB/STL/JSON) and publish workflow

### Known limitations

- Branch switching requires care (close documents first)
- Merge conflict resolution is currently manual
- Very large repositories can be slow to scan

### Near-term focus

- Enhanced branch/worktree UX
- Conflict resolution UI
- Git history viewer inside FreeCAD
- Improved diagnostics and more actionable error messages

### Long-term ideas

- Pull request integration
- Support for additional hosting providers (GitLab/Bitbucket/self-hosted)
- Advanced Git operations for power users (rebase/cherry-pick/stash)

---

## Changelog

### Version 0.8.0 (Current)

- Complete Git workflow (commit, push, pull, fetch)
- GitHub OAuth device flow
- Repository management (create, clone, validate)
- Branch operations with safety guards (switching requires closed documents)
- Preview export system (PNG, JSON, GLB, STL)
- One-click publish workflow
- Cross-platform support (Windows, macOS, Linux)

---

## License

MIT License (confirm in repository for definitive license text).

---

# Explanations

Discursive background material to build understanding.

## What Problem GitPDM Solves (for CAD work)

CAD projects evolve through many small edits: dimension tweaks, feature additions, assembly adjustments, refactors. Without structured checkpoints, it's easy to lose work (corruption, accidental overwrite, “save-as” chaos) or forget what changed and why.

GitPDM brings Git’s history of states into FreeCAD so that saving a meaningful checkpoint becomes routine.

---

## Git vs GitHub vs GitPDM

- **Git** stores history as commits in a local database (inside `.git`).
- **GitHub** hosts a remote copy of your repository for backup/sharing.
- **GitPDM** makes Git workflows usable inside FreeCAD, and optionally connects to GitHub.

A practical mental model:

- Commit = “make a durable checkpoint on my machine.”
- Push = “copy my checkpoints to GitHub.”

---

## Repositories and Commits

A **repository** is a project folder plus its history store (`.git`). A **commit** is a named snapshot of the repository contents.

Commit messages matter because CAD changes can be hard to remember later. The snapshot captures the state; the message captures intent.

---

## Why Branch Switching Is Tricky with FreeCAD Files

FreeCAD `.FCStd` files are ZIP archives. If the on-disk file changes underneath an open document (as can happen during a branch switch), you can get inconsistent state and corruption risk.

That’s why GitPDM takes a safety-first approach and requires closing documents for certain operations, and why worktrees are useful for multi-branch workflows.

---

## Git LFS (Why It’s Recommended for CAD)

Git is optimized for many small text changes. CAD files are larger binaries.

**Git LFS (Large File Storage)** stores large binaries outside the normal Git object store and keeps lightweight pointers in history. Practically, this keeps repositories more manageable as the project grows.

---

## What “Publishing” Adds Beyond Regular Commits

A regular commit is primarily for restoring and collaborating on versions.

Publishing adds shareability artifacts:

- a thumbnail image for quick scanning
- a browser-viewable 3D model (GLB)
- metadata summaries (JSON)

These outputs make the repository easier to browse and understand without opening FreeCAD.

---

## Common Questions (Context)

If you’re new to version control, it helps to separate the *local* and *remote* ideas:

- You don’t need deep Git knowledge to get value: a repository plus a few well-named commits already gives you durable checkpoints.
- GitHub is optional: GitPDM can be used with local-only Git, but pushing to a remote is a practical backup layer.

On safety and backups:

- GitPDM is designed to be safety-first (notably around branch switching).
- Still treat backups as layered: local commits + push to a remote + normal filesystem backups.

On performance:

- Git operations are intended not to freeze the UI, but very large repositories can be slower to scan.
- `.gitignore` and Git LFS are common ways to keep CAD repositories manageable.

---

## Getting Help

If something goes wrong, the two best sources are:

- GitPDM issue tracker: https://github.com/nerd-sniped/GitPDM/issues
- FreeCAD forum: https://forum.freecadweb.org/

---

## Further Reading

- Git book: https://git-scm.com/book/en/v2
- GitHub Git handbook: https://guides.github.com/introduction/git-handbook/
- FreeCAD wiki: https://wiki.freecad.org/

---

## Acknowledgments

GitPDM builds on a lot of great work:

- FreeCAD community
- Git and GitHub ecosystems
- Qt/PySide
- Contributors and testers
