# GitPDM - Git-based Product Data Management for FreeCAD

**Version Control Made Simple for Your CAD Projects**

GitPDM is a FreeCAD workbench addon that brings Git version control and GitHub collaboration directly into FreeCAD. Think of it as “version history” for CAD projects, designed around FreeCAD documents, previews, and publishing.

**Current Version:** 0.5.0 

---

## Documentation Structure

- **[Tutorials](#tutorials)** — learning-oriented lessons for newcomers
- **[How-To Guides](#how-to-guides)** — goal-oriented recipes for specific tasks
- **[Technical Reference](#technical-reference)** — accurate, “lookup-style” system details
- **[Explanations](#explanations)** — background concepts and context to build understanding

---

# Tutorials

## Tutorial 1: First Local Versioned CAD Project

**Goal:** Install GitPDM, create a repository, and make two commits.

**Prerequisites:**
- FreeCAD — supported policy: **current stable + one prior** (1.1.x and 1.0.x
  at the time of this release; originally developed on 0.20–1.0)
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

1. In the Git PDM toolbar, click **Toggle GitPDM Panel**. The panel docks at
   the bottom of the window (tabbed with Report view/Python console).
2. In the panel's Repository column, click **Browse…**.
3. Create/select an empty folder for your project (example: `Documents/FreeCAD Projects/MyFirstProject`).
4. Once GitPDM notices the folder isn't a Git repository yet, a **Create Repo**
   button appears — click it and confirm.

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
2. In the panel, confirm `simple-box.FCStd` shows up under the pending-changes
   chip.
3. There's no GitHub connection yet, so click the small **▼** beside the big
   Actions button and choose **Save Only (don't share yet)** — the button
   label changes to **Commit**.
4. Enter commit message:
   ```
   Add simple box part for testing
   ```
5. Click **Commit**.

### 5) Make a change and commit v2

1. Switch to **Part Design**.
2. Edit the Pad length from 10mm to 20mm.
3. Save.
4. Switch to **Git PDM**.
5. Enter commit message:
   ```
   Increase box height to 20mm
   ```
6. Click **Commit** (still in "Save Only" mode from step 4).

You now have a local commit history you can always return to.

---

## Tutorial 2: Connect to GitHub and Push for Backup

**Goal:** Authenticate to GitHub, connect this repo to a GitHub remote, and
push your local commits.

**Prerequisites:**
- Completed Tutorial 1
- A GitHub account

> GitHub is the convenience default, not a requirement — GitPDM also works
> with GitLab, Bitbucket, Gitea/Forgejo, SourceHut, or a bare/self-hosted git
> remote. See [How to Connect a Non-GitHub Host](#how-to-connect-a-non-github-host)
> if you're using one of those instead.

### 1) Connect your GitHub account (device flow)

1. Open the **Git PDM** menu (top menu bar) → **Connections…**.
2. In the **GitHub Account** section, click **Connect GitHub**.
3. A dialog appears with a short code (and a **Copy Link** button for the
   verification URL).
4. Open the link (or visit https://github.com/login/device), log in, enter
   the code, and click **Authorize**.
5. Return to FreeCAD; the Connections dialog shows "Connected". Close the
   dialog.

### 2) Connect this repository to a GitHub remote

Tutorial 1 created a local-only repository, so it has no remote yet:

1. Create a new, empty repository on github.com (no README/license, so it
   has nothing to conflict with your local history) and copy its URL.
2. Back in the GitPDM panel, click **Connect Remote** (it appears once
   GitPDM notices the repo has no remote configured).
3. Paste the URL and confirm.

### 3) Push

1. Click the small **▼** beside the big Actions button and choose
   **Share Only (already saved)** — the button label changes to **Push**
   (your v1/v2 commits from Tutorial 1 are already saved locally; this just
   sends them).
2. Click **Push**.
3. After success, verify your repo on GitHub at:
   - `https://github.com/YOUR_USERNAME/YOUR_REPO_NAME`

---

# How-To Guides

Goal-oriented recipes for specific problems.

---

## How to Install Git (Prerequisite)

**Goal:** Install Git and verify it works.

- **Windows**: install from https://git-scm.com/download/win, then restart; verify with `git --version`.
- **macOS**: run `git --version` in Terminal and install Xcode CLI tools if prompted.
- **Linux**: install via your package manager (e.g. `sudo apt install git`), verify with `git --version`.

---

## How to Fix Push Rejected

**Goal:** Push successfully when the remote moved ahead.

1. Click **Check for Updates** (fetch).
2. Click **Get Updates** (pull, fast-forward only).
3. If that succeeds, try pushing again (**▼ → Share Only**, then **Push**,
   or **Save & Share** if you also have new local changes).
4. If you hit conflicts, you'll need to resolve them manually (until a dedicated UI exists).
5. If your local clone is shallow (history-truncated), a banner offers a
   **Deepen** button — see [Shallow Clone](#shallow-clone) in the Technical
   Reference if pull/push behaves unexpectedly on a shallow clone.

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

## How to Configure the Part Glossary

**Goal:** Show exported parts in your project's `README.md` automatically.

GitPDM maintains a "Part Glossary" section in your repository's `README.md`,
listing every part with a generated preview (thumbnail, path, category,
bounding box) so collaborators can browse parts without digging through
folders. It's regenerated every time you export/publish, and is enabled by
default — the section is inserted between
`<!-- GITPDM:PART-GLOSSARY:START -->` / `<!-- GITPDM:PART-GLOSSARY:END -->`
markers so the rest of your `README.md` is left untouched.

The thumbnail and part name both link to the part's `.stl` file. GitHub
renders an interactive 3D viewer when you open an `.stl` blob directly, so
clicking through from the glossary opens that viewer (this only works on
GitHub's own file page — a live 3D viewer can't be embedded inline in a
rendered `README.md`).

1. Add (or edit) `.freecad-pdm/preset.json` with a `partGlossary` section:
   ```json
   {
     "partGlossary": {
       "enabled": true,
       "onlyAssemblies": false,
       "exclude": ["cad/fasteners/*"]
     }
   }
   ```
2. `enabled` — turn the whole feature off (`false`) if you don't want GitPDM
   touching `README.md`.
3. `onlyAssemblies` — only list parts GitPDM detects as assemblies (documents
   with linked sub-parts or more than one body), hiding standalone parts.
4. `exclude` — glob patterns (matched against the repo-relative source path,
   e.g. `cad/fasteners/*`) for parts to always leave out of the glossary.
5. Commit the preset, export/publish a part, and check `README.md`.

---

## How to Avoid Wrong Save Locations for New Parts

**Goal:** Make sure new documents save inside your repo, not some unrelated
folder.

FreeCAD's own Save dialog can't be reliably steered to a specific folder for
a document that has never been saved before — its starting folder comes from
internal state that isn't refreshed from preferences per dialog, so it can
default to your home folder or whatever folder a previous project last used.

For a document created via **File → New**, use **Git PDM → Save Into Repo**
instead of `Ctrl+S` for its first save. It shows its own dialog defaulting to
the repo's `cad/` folder and saves directly — once saved this way, later
`Ctrl+S`/Save As on that document will also default correctly.

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

## How to Connect a Non-GitHub Host

**Goal:** Use GitPDM with GitLab, Bitbucket, Gitea/Forgejo, SourceHut, or
another git host, instead of (or alongside) GitHub.

GitHub is the only host with an OAuth "click a button, no typing" device-flow
connection, because it's the only one GitPDM has a pre-registered OAuth app
for. The others authenticate via a pasted Personal Access Token (PAT) — a
credential you generate on that host's own website — which is a one-time
setup, not an ongoing inconvenience:

1. Open the **Git PDM** menu → **Connections…**.
2. In the **Other Git Hosts** section, pick a host from the **Host** dropdown
   (GitLab, Bitbucket, Gitea/Forgejo, or SourceHut).
3. For Gitea/Forgejo (self-hosted, no fixed address), a **Server URL** field
   appears — fill in your instance's URL.
4. On that host's website, generate a Personal Access Token with
   repository-creation/read/write scope, then paste it into the **Token**
   field here.
5. Click **Connect**.
6. Click **Browse Repos…** to list and clone existing repositories from that
   host, the same way **Join Team…** works for GitHub.

To create a **new** project on a non-GitHub host, use the panel's
**New Project…** button — the wizard's first page lets you choose any
connected host (or "Generic," for any git remote at all, no host API
involved) before asking for repository details.

Every host has different feature support (repo creation via API, PR
integration, LFS locking) — GitPDM only offers actions the selected host can
actually do; it won't show a button that would just fail. Two hosts have
extra requirements: Bitbucket repos live under a **workspace** (not just
"your account"), and Gitea/Forgejo needs the **Server URL** above since it's
self-hosted with no single fixed address GitPDM can assume.

---

## How to Fix GitHub Authentication Failures

**Goal:** Successfully connect GitPDM to GitHub.

1. Confirm GitHub is reachable in a browser: https://github.com/
2. Confirm your system clock is correct (OAuth is time-sensitive).
3. Open **Git PDM → Connections…** and retry **Connect GitHub** to complete
   the device flow.
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

# Technical Reference

Accurate lookup documentation. Minimal narrative.

## What GitPDM Does (Current Feature Summary)

- Version control of files inside a Git repository (commit/push/pull/fetch)
- Any git host: GitHub (OAuth device flow, no typing) plus GitLab, Bitbucket,
  Gitea/Forgejo, and SourceHut (paste a Personal Access Token) — or any bare
  git remote at all, with zero host API involved (the "Generic" option)
- A per-repository **storage mode** choice (delta vs. LFS) so history size
  and team file-locking are a deliberate tradeoff, not a silent default —
  see [Storage Modes](#storage-modes)
- Continuous background checkpointing to a recovery branch, so an idle or
  crashed session loses at most a few minutes of work — see
  [Continuous Checkpointing](#continuous-checkpointing)
- An advisory session lock so two GitPDM instances don't silently fight over
  the same working tree
- Shallow-clone support with a "history truncated" banner and one-click
  deepen, for fast cold starts
- Preview export and publishing pipeline (thumbnail PNG, JSON metadata, STL)
- Auto-generated "Part Glossary" section in `README.md` from exported previews
- "Save Into Repo" command so new documents reliably save inside the repo
  instead of wherever FreeCAD's Save dialog last defaulted to
- Safety guards to reduce risk of file corruption during risky operations

### Known limitation: branch switching

Branch switching is currently limited because FreeCAD `.FCStd` files are ZIP archives and can be corrupted if the working directory changes while documents are open. GitPDM protects you by requiring documents to be closed for certain operations.

---

## Requirements Summary

| Requirement | Version | Notes |
|-------------|---------|-------|
| FreeCAD | Current stable + one prior (1.1.x / 1.0.x as of this release) | Policy — verified manually before each release. Originally developed on 0.20–1.0. Install from https://www.freecad.org/downloads.php |
| Git | 2.20+ | Install from https://git-scm.com/ |
| Python | 3.8+ | Bundled with FreeCAD |
| PySide2 or PySide6 | Any | Bundled with FreeCAD |
| Git host account | N/A | Optional, for cloud features — GitHub, GitLab, Bitbucket, Gitea/Forgejo, SourceHut, or any other git remote |

---

## Storage Modes

Every repository has one storage mode, recorded in
`.freecad-pdm/config.json`'s `storageMode` field (`"delta"` or `"lfs"`) and
enforced in `.gitattributes` — the two modes are mutually exclusive **by
design**, not just by convention (GitPDM won't let a repo end up in both at
once):

| | **Delta mode (default)** | **LFS mode (opt-in)** |
|---|---|---|
| `.FCStd` compression | 0 (store, no deflate) — scoped to the moment of each save, restored right after | Normal (restored to your prior FreeCAD preference) |
| Git history | Plain git objects, delta-compressible across saves | Git LFS pointers; each version stored in full |
| Cost | Free, unmetered on GitHub | GitHub's free LFS allowance: ~1 GiB storage, ~1 GiB/month bandwidth |
| File locking | Not available | Available (prevents two people editing the same `.FCStd` at once) |

**These are opposites on purpose** (R1.1/R4.2): compression=0 makes each
saved file bigger on disk but keeps unchanged bytes identical across saves,
which is what lets Git (or LFS) delta-compress or dedupe between versions.
Turning LFS on without also restoring normal compression would store every
uncompressed version in full, multiplying storage and bandwidth for no
benefit — so GitPDM restores normal compression automatically in LFS mode,
and the combination "compression 0 + LFS" is unreachable through the UI.

Change a repo's mode via **Git PDM → Change Storage Mode…** (or the panel's
Storage Mode row); switching always shows a confirmation explaining the
consequence, in either direction — never a silent flip. See also
[Why GitPDM Sets FreeCAD's Compression Level to 0](#why-gitpdm-sets-freecads-compression-level-to-0-in-delta-mode)
for exactly when and how the compression change happens.

### Benchmark

`tools/storage_mode_benchmark.py` saves a synthetic document 10× per mode
and reports git's packed size after `git gc`. **Read this caveat before the
numbers**: FreeCAD isn't pip-installable, so the script can't drive real
`App.Document.save()` calls — it zips a synthetic ~160 KB XML-like payload
instead of real BREP geometry, using `ZIP_STORED`/`ZIP_DEFLATED` to stand in
for compression 0/3. A real run (2026-07-19, this synthetic proxy):

```
=== Summary (packed size after git gc) ===
delta: 59.78 KiB
lfs: 5.45 KiB
```

**LFS mode "wins" here** — which is the opposite of what delta mode is
supposed to demonstrate, and is the script's own documented caveat playing
out for real: at this small, synthetic scale, generic zlib deflate over
repetitive text-like content already lets git's own delta compression find
cross-version similarity just as well as (better than, in this run) storing
it uncompressed. Real `.FCStd` files differ in exactly the ways that matter
here — genuine BREP binary data, topological-naming churn on parametric
edits, and file sizes far larger than this toy example — which is expected
to make delta mode's advantage real in practice even though it doesn't show
up in this small synthetic test. Treat these numbers as a worked example of
the *measurement technique*, not proof of which mode is smaller for your
project; run the same script's technique through FreeCAD's own CLI
(`freecadcmd`) against a real project for a trustworthy verdict.

---

## Credential Chain & Environment Variables

GitPDM resolves git-host credentials through an ordered chain, so the same
codebase runs unmodified from a desktop session (interactive OAuth/keyring)
or a headless container (environment variables only, no keyring daemon):

1. `GITPDM_TOKEN_FILE` — path to a file containing the token (read fresh
   each time; never logged)
2. `GITPDM_TOKEN` — the token value directly
3. The OS keyring (Windows Credential Manager / macOS Keychain / Linux
   Secret Service) — the desktop path, via **Connect GitHub** / **Connect**
   in the Connections dialog
4. Interactive device flow or a pasted PAT prompt (UI layer only)

| Variable | Purpose |
|---|---|
| `GITPDM_TOKEN_FILE` | Path to a file holding the access token. Highest precedence. |
| `GITPDM_TOKEN` | The access token value directly (e.g. set by a container orchestrator as a secret). |
| `GITPDM_PROVIDER` | Which host the token is for (`github`, `gitlab`, `gitea`, `bitbucket`, `sourcehut`, or `generic`). Defaults to `github` if unset — matters because hosts disagree on the username to pair with a token over HTTPS (e.g. GitLab requires `oauth2`, Bitbucket requires `x-token-auth`). |
| `GITPDM_ALLOW_FILE_TOKENS` | Set to `1` to allow an opt-in on-disk token file store (`~/.config/GitPDM/credentials.json`, `chmod 0600`) as a keyring-less fallback. Unset by default — this file-store backend is unreachable without it, a deliberate desktop-security invariant. |

Once resolved, a token is bridged into network git operations (`clone`,
`fetch`, `pull`, `push`) via an inline git credential helper that references
the environment variable **by name only** — the token value never appears on
a command line or in a process listing. On desktop (no env vars set) this
bridge is a complete no-op; your normal git credential helper is untouched.

Headless check (no FreeCAD required, e.g. as a container smoke test):

```bash
GITPDM_TOKEN=<pat> python -m freecad_gitpdm.auth.check
# OK — source=env provider=github host=github.com login=<your-username>
```

---

## Shallow Clone

Cloning with limited history (`git clone --depth N`) is much faster for a
cold start — useful in a container, or just a very large repo. GitPDM's
**Join Team…** clone dialog offers a "Shallow clone" checkbox (default depth
20), pre-checked automatically when headless credential backends are active
(the same signal `GITPDM_TOKEN`/`GITPDM_TOKEN_FILE` give the credential
chain above — a strong hint you're in a container, not an interactive
desktop session).

When the active repo is a shallow clone, the panel shows a persistent
**"History truncated (shallow clone)"** banner with a **Deepen** button
(`git fetch --deepen` under the hood, or a full unshallow if no depth is
given). Commit, push, and pull all work normally against a shallow clone
without deepening first — the banner is informational, not a blocker.

---

## Continuous Checkpointing

While a document is dirty, GitPDM saves it and snapshots the working tree
onto a `gitpdm/recovery` git branch once either **45 seconds of idle time**
have passed since your last edit, or **3 minutes** have passed since the
last checkpoint (10 minutes in `lfs` storage mode) — whichever comes first,
so continuous active editing still gets checkpointed periodically instead of
never going idle. This is via git plumbing only, so it never touches your
real commit history, moves `HEAD`, or does anything porcelain-level that
could corrupt an open `.FCStd` file. It's a safety net, not a replacement
for real commits: "walk away anytime, lose at most a few minutes of work"
if FreeCAD or your machine crashes.

- **Push policy:** checkpoints **push to your remote by default** —
  desktop and headless/container sessions alike — so a checkpoint is a real
  off-machine record as soon as it's made, not something stranded on one
  machine until your next real commit. Turn this off (or force it back on
  explicitly) in **Git PDM → Connections… → Checkpointing** — useful if
  you're on limited bandwidth or would rather keep in-progress work local
  until you choose to share it. A checkpoint with no remote configured yet
  simply stays local; there's nothing to push to.
- **Restore:** on opening a repo, if a checkpoint newer than your current
  history exists (and no document is currently open), GitPDM offers to
  restore it into your working files.
- **Cleanup:** once a real commit supersedes a checkpoint, GitPDM offers to
  clear it (or do it anytime via **Git PDM → Clear Recovery Checkpoint**).
- In `lfs` storage mode, checkpoints are spaced further apart by default —
  each one is a full stored LFS object, so frequent checkpoints are more
  expensive there than in `delta` mode.

---

## Platform Token Storage

GitHub tokens are stored using the host platform’s secure credential store.
Tokens for other hosts (pasted PATs) are stored the same way, under a
separate namespaced entry per host, so connecting a second host never
overwrites GitHub's credentials.

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

Each part's `preview.json` includes a `category` field (`"part"` or
`"assembly"`, auto-detected) used by the Part Glossary's `onlyAssemblies`
filter — see [How to Configure the Part Glossary](#how-to-configure-the-part-glossary).

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

- `auth/` — OAuth device flow (GitHub), token storage, the headless
  credential chain, token refresh
- `git/` — Git subprocess wrapper; all git operations go through here,
  host-agnostic by design
- `providers/` — git host abstraction: `base.py` (capability flags,
  `GenericProvider` as the zero-API base case), `github/`, `gitlab/`,
  `gitea/`, `bitbucket/`, `sourcehut/` (each a subpackage), `shared/`
  (the host-agnostic HTTP client/cache/rate-limiter parts)
- `export/` — preview generation pipeline (thumbnails, mesh export, manifest)
- `core/` — shared utilities: logging, jobs, paths, settings, storage mode,
  session lock, continuous checkpointing, per-repo provider selection
- `ui/` — the dockable panel and its feature handlers, plus the standalone
  Connections dialog for credential management

For the full, current module-by-module breakdown (including internal
conventions and the reasoning behind non-obvious design choices), see
`CLAUDE.md` at the repo root — it's written for both human contributors and
coding agents working on GitPDM.

---

## Roadmap & Future Development (Project Information)

### Known limitations

- Branch switching requires care (close documents first)
- Merge conflict resolution is currently manual
- Very large repositories can be slow to scan
- No in-panel commit-log/history browser yet — checkpoint restore and
  storage-mode changes act on "the current state" rather than letting you
  browse and pick a specific point in time

### Near-term focus
- Docs sweep and FreeCAD Addon Manager submission (this phase)
- Enhanced branch/worktree UX
- Conflict resolution UI
- Git history viewer inside FreeCAD
- Improved diagnostics and more actionable error messages

### Long-term ideas

- Pull request integration
- HistoryWorkbench integration for visual 3D diffs (spike planned)
- Advanced Git operations for power users (rebase/cherry-pick/stash)

### Recently shipped

- Support for GitLab, Bitbucket, Gitea/Forgejo, and SourceHut, alongside
  GitHub — see [How to Connect a Non-GitHub Host](#how-to-connect-a-non-github-host)
- Repo-scoped storage modes (delta vs. LFS) — see [Storage Modes](#storage-modes)
- Continuous background checkpointing — see [Continuous Checkpointing](#continuous-checkpointing)
- Headless/container operation via environment-variable credentials — see
  [Credential Chain & Environment Variables](#credential-chain--environment-variables)

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

- Commit = “make a local checkpoint on my machine.”
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

## Storage Modes (Delta vs. LFS)

**Delta mode (default, free).** GitPDM saves `.FCStd` files uncompressed so
that git can store only what actually changed between versions, rather than
a fresh copy each commit. Repos stay small, and plain git on GitHub is free
and unmetered. Individual files on disk are larger; this is intentional and
is what makes the history small.

**LFS mode (opt-in, for teams).** Git LFS adds file locking — the ability to
reserve a file so a teammate cannot edit it simultaneously. Because `.FCStd`
files cannot be merged, locking is the only real answer to concurrent edits.
The cost: LFS stores every version in full, with no delta compression, and
GitHub's free LFS allowance is ~1 GiB of storage and ~1 GiB/month of
bandwidth. GitPDM restores normal compression in this mode to keep those
numbers down.

**Which do I want?** Working alone: delta mode. You do not have a
concurrency problem, and delta mode is free. Sharing write access with
others: LFS mode, and budget for a data pack.

See [Storage Modes](#storage-modes) in the Technical Reference for the exact
mechanics (the `.gitattributes`/`.freecad-pdm/config.json` fields) and real
benchmark numbers, and the compression explanation below for exactly when
GitPDM touches FreeCAD's global preference.

---

## Why GitPDM Sets FreeCAD's Compression Level to 0 (in Delta Mode)

`.FCStd` files are ZIP archives, and FreeCAD compresses (deflates) the entries inside by default. Deflate output is sensitive to small input changes — editing one feature can rewrite most of the archive's compressed bytes even though the underlying model barely changed, which leaves Git nothing meaningful to diff or delta-compress between saves.

Earlier versions of GitPDM set FreeCAD's global **Compression level**
preference to 0 whenever a repository was opened, and left it there — which
silently affected every `.FCStd` file you saved afterward, in any project,
until you noticed and changed it back. That behavior is gone. GitPDM now
scopes the change to the moment of an actual save: right before a save
starts (and only for a document inside a `delta`-mode repo), it records your
current compression preference, sets it to **0** for that one save, and
restores your prior value immediately after — every time, even if you're
also saving unrelated documents in other projects at the same time. In `lfs`
mode this never happens at all; LFS mode keeps your normal compression
preference throughout.

If FreeCAD or GitPDM crashes mid-save, the next time GitPDM starts it
detects a scope left active from the interrupted save and restores your
preference immediately, rather than leaving it pinned at 0 indefinitely.

---

## What “Publishing” Adds Beyond Regular Commits

A regular commit is primarily for restoring and collaborating on versions.

Publishing adds shareability artifacts:

- a thumbnail image for quick scanning
- a browser-viewable 3D model (STL)
- metadata summaries (JSON)

These outputs make the repository easier to browse and understand without opening FreeCAD.

---

## Common Questions (Context)

If you’re new to version control, it helps to separate the *local* and *remote* ideas:

- You don’t need deep Git knowledge to get value: a repository plus a few well-named commits already gives you durable checkpoints.
- GitHub is optional: GitPDM can be used with local-only Git, but pushing to a remote is a practical cloud backup layer.
- Still treat backups as layered: local commits + push to a remote + normal filesystem backups.

On performance:

- Git operations are intended not to freeze the UI, but very large repositories can be slower to scan.
- `.gitignore` and choosing the right [storage mode](#storage-modes-delta-vs-lfs) are the two main ways to keep CAD repositories manageable.

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
