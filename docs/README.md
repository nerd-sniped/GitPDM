# GitPDM - Git-based Product Data Management for FreeCAD

**Version Control Made Simple for Your CAD Projects**

> 🎯 **In 5 minutes:** Install GitPDM, create your first versioned CAD project, and never lose work again!

GitPDM is a FreeCAD workbench addon that brings the power of Git version control and GitHub collaboration directly into FreeCAD. Think of it as "Google Drive version history" but specifically designed for your 3D CAD parts and assemblies.

**Current Version:** 0.8.0 (Production Ready)

---

## 🤔 Wait, What Is This? (For Complete Beginners)

### Never worked with version control before? No problem!

**GitPDM helps you:**
- ✅ **Never lose your work** - Keep every version of your designs safely saved
- ✅ **Track your progress** - See what changed between versions (like "track changes" in Word)
- ✅ **Share easily** - Put your projects on GitHub for others to download and learn from
- ✅ **Collaborate safely** - Work on projects with teammates without overwriting each other's work
- ✅ **Look professional** - Automatic preview images and 3D models for web viewing

### What's Git? What's GitHub?

- **Git** = A system that tracks changes to your files (like a sophisticated "undo" button with infinite history)
- **GitHub** = A website where you can store and share your Git projects (like Dropbox, but for code and CAD files)
- **GitPDM** = This addon that makes Git work smoothly inside FreeCAD

**You don't need to be a programmer or Git expert to use GitPDM!** This guide will walk you through everything.

---

## ✨ What GitPDM Can Do (Current Features)

GitPDM is **production-ready** with a comprehensive set of features for managing your CAD projects:

### 🔄 Version Control Your CAD Files

- **Save Your History**: Every time you commit, GitPDM takes a snapshot of your work
- **See What Changed**: View exactly what files were modified, added, or deleted
- **Undo Mistakes**: Go back to any previous version if something goes wrong
- **Sync with GitHub**: Push your work to the cloud for backup and sharing

### 🌐 GitHub Integration (Optional but Awesome)
- **One-Click Login**: Securely connect your GitHub account (no passwords in FreeCAD!)
- **Browse Your Repos**: See all your GitHub projects right inside FreeCAD
- **Clone Projects**: Download any repository with a single click
- **Create New Repos**: Start a new GitHub project without leaving FreeCAD

### 🎨 Automatic Preview Generation
- **Beautiful Thumbnails**: GitPDM creates PNG preview images of your parts automatically
- **3D Web Models**: Export GLB files that can be viewed in a browser (great for sharing!)
- **Printable STL Files**: Automatic STL export for 3D printing
- **One-Click Publish**: Export previews + commit + push to GitHub in one action

### 🛡️ Safety Features
- **File Protection**: GitPDM prevents operations that could corrupt your FreeCAD files
- **Smart Warnings**: Tells you to close files before switching branches
- **Worktree Support**: Advanced users can isolate branches in separate folders
- **Background Operations**: Git operations won't freeze FreeCAD's interface

### 🔧 Works Great With
- **FreeCAD Versions**: 0.20, 0.21, and 1.0
- **Operating Systems**: Windows, Linux, and macOS
- **Git LFS**: Handle large files efficiently (we'll show you how)
- **Multiple Projects**: Manage as many repositories as you want

### ⚠️ Current Limitations

**Branch Operations:** The branch switching feature is currently **limited**. While you can create and view branches, switching between them with open FreeCAD files requires careful manual steps. We recommend:
- Always close all documents before switching branches
- Use the worktree feature for complex multi-branch workflows
- Or stick to simple main-branch-only workflows for now

*This is a known limitation we're actively working to improve!*

## 📦 Installation Guide

### What You'll Need (Prerequisites)

Before installing GitPDM, make sure you have:

1. **FreeCAD** (version 0.20, 0.21, or 1.0)
   - Download from: https://www.freecad.org/downloads.php
   - Install it first before continuing

2. **Git** (the version control system)
   - **Windows**: Download from https://git-scm.com/download/win
   - **Mac**: Open Terminal and run `git --version` (macOS will prompt to install if needed)
   - **Linux**: Usually pre-installed, or run `sudo apt install git` (Ubuntu/Debian)
   
   **How to check if Git is installed:**
   - Open a terminal/command prompt
   - Type: `git --version`
   - You should see something like `git version 2.40.0`

3. **GitHub Account** (optional, but highly recommended)
   - Free sign-up at: https://github.com/signup
   - You'll use this to store projects online

### Step-by-Step Installation

#### Method 1: Addon Manager (Easiest - Coming Soon)
*GitPDM will soon be available in FreeCAD's Addon Manager. For now, use Manual Installation.*

#### Method 2: Manual Installation

**Step 1: Find Your FreeCAD Mod Folder**

This is where FreeCAD looks for addons. The location depends on your operating system:

- **Windows:** 
  - Press `Windows + R`
  - Type: `%APPDATA%\FreeCAD\Mod`
  - Press Enter
  - If the folder doesn't exist, create it!

- **macOS:**
  - Open Finder
  - Press `Cmd + Shift + G`
  - Type: `~/Library/Application Support/FreeCAD/Mod`
  - Press Go
  - If the folder doesn't exist, create it!

- **Linux:**
  - Open your file manager
  - Press `Ctrl + H` to show hidden files
  - Navigate to: `~/.FreeCAD/Mod/`
  - If the folder doesn't exist, create it!

**Step 2: Download GitPDM**

1. Download the latest release from: [GitHub Releases](https://github.com/nerd-sniped/GitPDM/releases)
2. OR clone with git: `git clone https://github.com/nerd-sniped/GitPDM.git`

**Step 3: Copy to Mod Folder**

1. Extract the downloaded ZIP file (if you downloaded a release)
2. You should have a folder called `GitPDM` containing:
   - `Init.py`
   - `InitGui.py`
   - `freecad_gitpdm/` folder
   - `docs/` folder
3. Copy this entire `GitPDM` folder into your Mod directory

**Your folder structure should look like:**
```
Mod/
└── GitPDM/
    ├── Init.py
    ├── InitGui.py
    ├── freecad_gitpdm/
    │   ├── __init__.py
    │   ├── auth/
    │   ├── core/
    │   ├── export/
    │   ├── git/
    │   ├── github/
    │   └── ui/
    └── docs/
```

**Step 4: Restart FreeCAD**

1. Close FreeCAD completely (if it's open)
2. Start FreeCAD again

**Step 5: Verify Installation**

1. Look at the **workbench selector** dropdown (usually top-right or top-left)
2. Click it to see the list of workbenches
3. You should see **"Git PDM"** in the list
4. Click "Git PDM" to switch to it

**Success!** If you see the Git PDM workbench, you're ready to go! 🎉

### Troubleshooting Installation

**Problem: Git PDM doesn't appear in the workbench list**

✅ **Solutions to try:**
1. Check that the folder is named exactly `GitPDM` (not `GitPDM-main` or `GitPDM-master`)
2. Make sure `Init.py` and `InitGui.py` are directly in the `GitPDM` folder
3. Open FreeCAD's **Report View** (View → Panels → Report view) and look for error messages
4. Try `Tools` → `Customize` → `Workbenches` to see if Git PDM is hidden
5. Completely restart your computer and try again

**Problem: Git commands don't work**

✅ **Solutions:**
1. Make sure Git is installed (run `git --version` in a terminal)
2. On Windows, you might need to restart after installing Git
3. Check that Git is in your system PATH

**Problem: I see errors about PySide6 or PySide2**

✅ **Solution:**
- This usually means your FreeCAD installation is incomplete
- Try reinstalling FreeCAD from the official website
- These Qt libraries should come bundled with FreeCAD

**Still stuck?** Check the [Support & Community](#-support--community) section below!

---

## 🚀 First-Time Setup Walkthrough

Congratulations on installing GitPDM! Let's get you up and running with your first project.

### Part 1: Opening GitPDM for the First Time

**Step 1: Switch to the Git PDM Workbench**

1. Open FreeCAD
2. Find the **workbench selector** dropdown (usually in the top toolbar)
3. Click it and select **"Git PDM"**
4. The interface will change - you might see new buttons in the toolbar

**Step 2: Open the GitPDM Panel**

1. Look for a button in the toolbar that says **"Toggle GitPDM Panel"**
2. Click it
3. A new panel will appear (usually on the right side of the screen)
4. This panel is your control center for all Git operations!

**Understanding the GitPDM Panel:**

The panel has several sections:
- **📁 Repository Status** - Shows which project you're currently working in
- **🌿 Branch** - Shows which version/branch you're on (usually "main")
- **📝 Changes** - Lists files you've modified
- **🔘 Buttons** - Actions like Commit, Push, Fetch, etc.

### Part 2: Connecting to GitHub (Optional but Recommended)

You can use GitPDM without GitHub (just for local version control), but connecting to GitHub unlocks powerful features like cloud backup and sharing.

**Step 1: Click "Connect GitHub"**

1. In the GitPDM panel, find the **"Connect GitHub"** button
2. Click it
3. A dialog will appear with a special code (like "ABCD-1234")

**Step 2: Authorize on GitHub**

1. The dialog will have a button that says **"Open GitHub"** or similar
2. Click it (or manually visit: https://github.com/login/device)
3. Your web browser will open
4. Log in to GitHub if you haven't already
5. Enter the code from the dialog
6. Click **"Authorize"** when GitHub asks

**Step 3: Return to FreeCAD**

1. Go back to FreeCAD
2. The dialog should now show "✅ Connected!"
3. You'll see your GitHub username displayed in the panel

**🎉 Success!** You're now connected to GitHub!

### Part 3: Creating Your First Repository

A repository (or "repo") is like a project folder that tracks all your changes. Let's create one!

**Option A: Create a New Repository (Start from scratch)**

1. In the GitPDM panel, click **"Browse for Folder"** or the folder icon
2. Navigate to where you want to create your project
   - Example: `Documents/FreeCAD Projects/MyFirstProject`
   - **Tip:** Create a new empty folder for each project
3. Click the folder button again if the path isn't valid yet
4. Click **"Create Repo"** button (appears when folder has no Git repo)
5. GitPDM creates a new repository in that folder

**Option B: Clone an Existing Repository (Download someone else's project)**

1. Make sure you're connected to GitHub (see Part 2)
2. In the GitPDM panel, look for **"Browse GitHub Repos"** or similar
3. You'll see a list of all your GitHub repositories
4. Select one you want to work on
5. Click **"Clone"**
6. Choose where to download it on your computer
7. GitPDM will download the project and set it up

**Option C: Use an Existing Local Repository**

1. If you already have a Git repository on your computer
2. Click **"Browse for Folder"**
3. Navigate to the folder containing your repository
4. GitPDM will recognize it and show the status

**What Just Happened?**

- GitPDM created (or opened) a special `.git` folder in your project directory
- This hidden folder stores all the version history
- You can now start saving versions of your CAD files!

---

## 🎓 Your First Part - A Complete Tutorial

Let's walk through creating your first tracked CAD part from start to finish!

### Step 1: Create a Simple Part in FreeCAD

1. Make sure you're in the **Part Design** workbench
2. Create a new document: **File → New**
3. Create a simple object (for learning purposes):
   - Click **"Create Body"**
   - Click **"Create Sketch"** → Choose XY plane
   - Draw a simple rectangle (use the rectangle tool)
   - Click **"Close"**
   - Click **"Pad"** and set length to 10mm
4. Congratulations! You've created a simple 3D box

### Step 2: Save Your Part in the Repository

1. Click **File → Save As**
2. Navigate **inside** your repository folder (the one you created/chose earlier)
3. Name your file something descriptive: `simple-box.FCStd`
4. Click **Save**

**Important:** Always save FreeCAD files **inside** your repository folder! GitPDM can only track files that are in the repository.

### Step 3: See Your Changes in GitPDM

1. Switch back to the **Git PDM** workbench
2. Look at the GitPDM panel
3. In the **"Changes"** section, you should see:
   - `simple-box.FCStd` listed (might say "Untracked" or show a `?`)
4. This means Git knows the file exists but hasn't saved a version yet

### Step 4: Commit Your First Version (Taking a Snapshot)

"Committing" means saving a permanent snapshot of your work.

1. Look for the **Commit Message** text box in the GitPDM panel
2. Type a description of what you did:
   ```
   Add simple box part for testing
   ```
   - **Tip:** Good commit messages describe *what* you did and *why*
3. Click the **"Commit"** button
4. You'll see a confirmation message

**What Just Happened?**
- Git took a snapshot of your file
- This snapshot is saved forever in the `.git` folder
- You can always come back to this exact version later

### Step 5: Make a Change and See the Difference

Let's modify the part and see how GitPDM tracks changes:

1. Switch back to **Part Design** workbench
2. Double-click your Pad feature in the tree
3. Change the length from 10mm to **20mm**
4. Click **OK**
5. **File → Save** (or Ctrl+S)

6. Switch back to **Git PDM** workbench
7. Look at the GitPDM panel
8. You should see `simple-box.FCStd` listed again under "Changes"
9. This time it might show an `M` (Modified) instead of `?`

**This is the magic of version control!** Git knows the file changed!

### Step 6: Commit Your Second Version

1. In the commit message box, type:
   ```
   Increase box height to 20mm
   ```
2. Click **"Commit"**
3. Your change is now saved as a new snapshot

### Step 7: Push to GitHub (Cloud Backup)

If you're connected to GitHub, you can push your commits to the cloud:

1. Click the **"Push"** button in the GitPDM panel
2. If this is your first push, you might need to:
   - Create the repository on GitHub (GitPDM might prompt you)
   - Or connect to an existing remote repository
3. Wait for the upload to complete
4. You'll see a success message

**Now your project is backed up on GitHub!** 🎉

You can view it by going to: `https://github.com/YOUR_USERNAME/YOUR_REPO_NAME`

### Step 8: Understanding What You've Learned

Congratulations! You now know the **basic Git workflow**:

```
1. Make changes to your CAD file
2. Save in FreeCAD
3. Write a commit message
4. Click "Commit" (saves locally)
5. Click "Push" (backs up to GitHub)
```

This is the pattern you'll repeat hundreds of times! Each commit is a safe checkpoint you can return to.

---

## 📖 Core Concepts Explained

Now that you've used GitPDM hands-on, let's clarify some key concepts:

### What is a Repository?

**Simple explanation:** A repository is a project folder with superpowers.

- It's just a regular folder on your computer
- Contains a hidden `.git` subfolder that stores all history
- Can contain CAD files, documentation, images, etc.
- Think of it like a time machine for your project

**Technical explanation:** A repository is a directory tree tracked by Git, storing both the current working files and a complete version history in the `.git` database.

### What is a Commit?

**Simple explanation:** A commit is a saved snapshot of your project at a specific point in time.

- Like taking a photograph of all your files at once
- Includes a message describing what changed
- Creates a permanent bookmark you can return to
- Commit early, commit often!

**Technical explanation:** A commit is a Git object containing a tree (directory structure), parent commit reference(s), author metadata, timestamp, and a message. Each commit has a unique SHA-1 hash.

### What is Pushing?

**Simple explanation:** Pushing uploads your commits to GitHub.

- Your commits are stored locally on your computer first
- "Push" sends them to GitHub (or another remote server)
- This creates a backup and lets others see your work
- You can push many commits at once

**Technical explanation:** Push synchronizes your local branch with a remote repository by transferring commit objects and updating the remote branch reference.

### What is Pulling?

**Simple explanation:** Pulling downloads new commits from GitHub.

- If a teammate made changes, "pull" gets their work
- Updates your local files with the latest version
- Usually safe and automatic
- Always pull before you start working!

**Technical explanation:** Pull fetches remote commits and attempts to merge them into your current branch, potentially requiring conflict resolution.

### What is a Branch? ⚠️

**Simple explanation:** A branch is an alternate timeline for your project.

- The default branch is usually called "main"
- You can create new branches to try experiments
- Branches let multiple people work without conflicts
- **However:** GitPDM's branch features are currently limited (see limitations above)

**Technical explanation:** A branch is a movable pointer to a commit, allowing divergent development histories. GitPDM currently has restrictions on branch switching with open FreeCAD documents.

**For Now:** We recommend sticking to the "main" branch until you're comfortable with Git basics!

### What is Git LFS?

**Simple explanation:** Git LFS is for handling large files efficiently.

- FreeCAD files can be several megabytes (or larger!)
- Regular Git stores full copies of every version
- Git LFS stores large files separately (more efficient)
- Highly recommended for CAD projects

**How to enable it:** See the [Setting Up Git LFS](#setting-up-git-lfs) section below.

---

## 🔧 Common Workflows & How-To Guides

### Daily Workflow: Edit → Save → Commit → Push

This is the bread-and-butter workflow you'll use constantly:

```
1. Open your FreeCAD file from your repository
2. Make your changes/improvements
3. File → Save (Ctrl+S)
4. Switch to Git PDM workbench
5. Type commit message (e.g., "Add mounting holes")
6. Click "Commit"
7. Click "Push" (uploads to GitHub)
```

**How often should I commit?**
- Commit whenever you complete a logical unit of work
- Examples: "Add base plate", "Fix alignment issue", "Change material to aluminum"
- Better to commit too often than not enough!
- If you can describe what you did in one sentence, it's ready to commit

### Viewing Your Project History on GitHub

Want to see your project's timeline and download old versions?

1. Go to your repository on GitHub: `https://github.com/YOUR_USERNAME/REPO_NAME`
2. Click the **"commits"** link (usually shows a number like "12 commits")
3. You'll see a list of all your commits with messages
4. Click any commit to see exactly what changed
5. Click "Browse files" to download that specific version

### Working with Assemblies and Multiple Parts

**Organizing files:**

```
MyProject/
├── parts/
│   ├── base-plate.FCStd
│   ├── motor-mount.FCStd
│   └── cover.FCStd
├── assemblies/
│   └── main-assembly.FCStd
└── docs/
    └── notes.md
```

**Best practices:**
- Keep parts in a `parts/` subfolder
- Keep assemblies in an `assemblies/` subfolder
- Commit assemblies and their component parts together
- Use descriptive file names (not "Part1.FCStd")

**Commit message example:**
```
Add motor mount and update main assembly

- Created motor-mount.FCStd with mounting holes
- Updated main-assembly.FCStd to include new mount
- Aligned with base plate bolt pattern
```

### Sharing Your Project with Others

**Option 1: Public Repository (Open Source)**

1. When creating a repo on GitHub, choose "Public"
2. Anyone can view and download your project
3. Great for learning, portfolios, and collaboration
4. Share the link: `https://github.com/YOUR_USERNAME/REPO_NAME`

**Option 2: Private Repository (Personal Projects)**

1. Choose "Private" when creating the repository
2. Only you (and invited collaborators) can access it
3. Free for personal use on GitHub
4. Invite collaborators via Settings → Collaborators

**What others can do:**
- Download your CAD files
- View your commit history
- See preview images (if you use the publish feature)
- View 3D models in their browser (with GLB export)
- Fork your project to make their own version

### Setting Up Git LFS (For Large Files)

Git LFS (Large File Storage) is essential for CAD projects:

**Step 1: Install Git LFS**

- **Windows**: Download from https://git-lfs.github.com/
- **Mac**: Run `brew install git-lfs` (if you have Homebrew)
- **Linux**: Run `sudo apt install git-lfs` (Ubuntu/Debian)

**Step 2: Initialize in Your Repository**

1. Open a terminal/command prompt
2. Navigate to your repository folder:
   ```
   cd path/to/your/repository
   ```
3. Run:
   ```
   git lfs install
   ```

**Step 3: Track FreeCAD Files**

Create a file called `.gitattributes` in your repository root:

```
*.FCStd filter=lfs diff=lfs merge=lfs -text
*.glb filter=lfs diff=lfs merge=lfs -text
*.stl filter=lfs diff=lfs merge=lfs -text
*.step filter=lfs diff=lfs merge=lfs -text
*.iges filter=lfs diff=lfs merge=lfs -text
```

**Step 4: Commit the Configuration**

```
git add .gitattributes
git commit -m "Configure Git LFS for CAD files"
git push
```

**Done!** All future commits of these file types will use LFS automatically.

### Using the One-Click Publish Feature

The "Publish Branch" button does everything in one click:

**What it does:**
1. Generates a PNG thumbnail of your active document
2. Exports a GLB 3D model (viewable in browsers)
3. Optionally exports STL (for 3D printing)
4. Creates a JSON manifest with part metadata
5. Stages all these files + your source file
6. Commits with your message
7. Pushes to GitHub

**How to use it:**

1. Open a FreeCAD document in your repository
2. Make sure your part looks good (the preview uses current view)
3. Switch to Git PDM workbench
4. Type your commit message
5. Click **"Publish Branch"** instead of regular "Commit"
6. Wait for the progress dialog (exports can take 10-30 seconds)
7. Done! Your part is now on GitHub with beautiful previews

**Benefits:**
- People can see your part without downloading anything
- 3D preview works on GitHub (with proper plugins)
- Consistent documentation for all parts
- Professional-looking project

**Customizing exports:** See [Advanced Topics: Custom Preview Presets](#custom-preview-presets) below.

### Fetching Updates from GitHub

If you're collaborating or working from multiple computers:

1. Click the **"Fetch"** button
   - This checks GitHub for new commits
   - Doesn't change your files yet (safe to do anytime)
2. Check the status display for "Behind" count
3. If you see "Behind: X commits", click **"Pull"**
4. GitPDM will download and merge the new changes
5. Your files are now up to date!

**Best practice:** Always Fetch/Pull before starting work each day!

---

## 💡 Tips & Best Practices

### Commit Messages: Good vs Bad

**❌ Bad commit messages:**
```
- "update"
- "fix"
- "changes"
- "asdf"
- "WIP" (without explanation)
```

**✅ Good commit messages:**
```
- "Add mounting holes to base plate"
- "Fix alignment issue between motor and shaft"
- "Increase wall thickness to 3mm for strength"
- "Split monolithic assembly into subassemblies"
- "Update bearing dimensions to match SKF 6204"
```

**Template to use:**
```
[Action] [what] [optional: why]

Examples:
- Add motor mount with NEMA 17 bolt pattern
- Fix dimensional error in coupling (was 25mm, should be 20mm)
- Refactor assembly structure for easier updates
- Update to latest version of imported STEP file
```

### Organizing Your Repository Structure

**Recommended structure for a project:**

```
MyProject/
├── .gitattributes          # Git LFS configuration
├── .freecad-pdm/
│   └── preset.json         # Export settings
├── README.md               # Project description
├── parts/                  # Individual components
│   ├── mechanical/
│   │   ├── base.FCStd
│   │   ├── cover.FCStd
│   │   └── bracket.FCStd
│   └── hardware/           # Off-the-shelf parts
│       └── M3-bolt.FCStd
├── assemblies/
│   ├── subassembly1.FCStd
│   └── main-assembly.FCStd
├── drawings/               # 2D drawings (PDF)
│   └── base-drawing.pdf
├── exports/                # STEP, STL, etc.
│   ├── base.step
│   └── base.stl
├── docs/                   # Documentation
│   ├── assembly-instructions.md
│   └── bill-of-materials.md
└── previews/               # Auto-generated by GitPDM
    └── parts/
        └── mechanical/
            └── base/
                ├── preview.png
                ├── preview.json
                └── preview.glb
```

### When to Commit (Frequency Tips)

**Commit when you:**
- ✅ Complete a feature or component
- ✅ Fix a bug or error
- ✅ Make a significant change to dimensions
- ✅ Reach a good stopping point
- ✅ Before trying something risky/experimental

**Don't wait to commit when:**
- ❌ Your file gets corrupted (too late!)
- ❌ At the end of the week (commit daily!)
- ❌ Only when "everything is perfect" (commit incremental progress!)

**Golden rule:** If you can't describe what you did in one sentence, you probably should have committed earlier!

### Backup Strategies

GitPDM provides excellent version control, but consider these backup layers:

1. **Local Git** - All commits stored on your computer
2. **GitHub** - Push regularly for cloud backup
3. **External Backup** - Use regular file backup software for the whole repository folder
   - Windows: File History, OneDrive
   - Mac: Time Machine
   - Linux: Déjà Dup, Timeshift
4. **Git LFS** - Use for large files to save space

**Never rely on just one backup method!**

---

## 🐛 Troubleshooting & Common Issues

### Installation Issues

**Problem: Workbench doesn't appear**

See the detailed [Troubleshooting Installation](#troubleshooting-installation) section above!

### Git Operation Failures

**Problem: "Git is not recognized as a command"**

✅ **Solution:**
- Git is not installed or not in your system PATH
- Install Git from https://git-scm.com/
- On Windows, restart your computer after installing
- Verify by opening a terminal and typing `git --version`

**Problem: "Permission denied" or "Authentication failed"**

✅ **Solutions:**
- You might not have permission to access the repository
- For GitHub: Make sure you're connected (see "Connect GitHub")
- For private repos: Ensure you're logged into the correct account
- Try disconnecting and reconnecting GitHub

**Problem: "Failed to push - rejected"**

✅ **Solutions:**
- Someone else pushed changes since your last pull
- Click "Fetch" to check for updates
- Click "Pull" to get the latest changes
- Then try pushing again
- If conflicts occur, you may need to resolve them manually (advanced)

### FreeCAD-Specific Issues

**Problem: "Cannot switch branch - close all documents first"**

✅ **This is intentional!** 
- GitPDM prevents branch operations that could corrupt `.FCStd` files
- Solution:
  1. Save all your work (`File → Save All`)
  2. Close all documents (`File → Close All`)
  3. Now try the branch operation
  4. Reopen files after the branch switch completes

**Problem: Preview export fails or shows errors**

✅ **Solutions:**
- Make sure the document is saved
- Ensure your document has visible 3D geometry
- Check that you're in GUI mode (not headless/CLI FreeCAD)
- Verify the `.freecad-pdm/preset.json` is valid JSON (if you customized it)
- Check FreeCAD's Report View for detailed error messages

**Problem: "Auto-refresh not working after save"**

✅ **Solutions:**
- Check that the document is inside your repository folder
- Try manually clicking "Refresh" button
- Check FreeCAD's Report View for errors
- Restart FreeCAD and try again

### GitHub Connection Issues

**Problem: "OAuth authentication failed"**

✅ **Solutions:**
- Check your internet connection
- Make sure your system clock is correct (OAuth requires accurate time)
- Try the authentication flow again
- Check if GitHub is accessible: https://github.com/
- Look in Report View for detailed error messages

**Problem: "Session expired" or "Token invalid"**

✅ **Solution:**
- Your GitHub connection timed out (this is normal after some time)
- Click "Disconnect" then "Connect GitHub" again
- Re-authorize the application

**Problem: "Failed to load repositories"**

✅ **Solutions:**
- Check internet connection
- Try clicking "Refresh" button
- Disconnect and reconnect GitHub
- Check if you have any repositories (create one on GitHub to test)

### Performance & Speed

**Problem: Repository operations are slow**

✅ **Solutions:**
- Large repositories (1000s of files) naturally take longer
- Use Git LFS for `.FCStd` files to reduce repository size
- Consider splitting large projects into multiple repositories
- Add unnecessary files to `.gitignore`:
  ```
  __pycache__/
  *.pyc
  .DS_Store
  Thumbs.db
  ```

**Problem: FreeCAD freezes during Git operations**

✅ **This shouldn't happen!**
- All Git operations should run in background
- If FreeCAD freezes, check the Report View after it unfreezes
- This might indicate a bug - please report it!
- As a workaround, try smaller commits (fewer files at once)

### Getting Help

**Still having issues?**

1. **Check FreeCAD's Report View**
   - `View → Panels → Report view`
   - Look for errors prefixed with `[GitPDM]`
   - These often explain exactly what went wrong

2. **Search Existing Issues**
   - Visit: https://github.com/nerd-sniped/GitPDM/issues
   - Someone might have already solved your problem!

3. **Ask for Help**
   - Open a new issue on GitHub
   - Include:
     - Your OS and FreeCAD version
     - What you were trying to do
     - Error messages from Report View
     - Steps to reproduce the problem

4. **FreeCAD Community**
   - FreeCAD forum: https://forum.freecadweb.org/
   - Ask in the "Addons" section

---

## 🎓 Advanced Topics

### Understanding Worktrees

**What is a worktree?** A worktree creates a separate working directory for each branch, avoiding file corruption issues when switching branches.

**When to use worktrees:**
- You're working on multiple features simultaneously
- You want to compare branches side-by-side
- You need branch isolation (advanced users)

**How GitPDM handles worktrees:**
1. When you try to switch branches, GitPDM may offer to create a worktree
2. Each branch gets its own folder: `MyProject-feature-branch`
3. You can open files from different worktrees in different FreeCAD windows
4. Changes in one worktree don't affect others

**Limitations:**
- Takes more disk space (separate copy for each branch)
- Can be confusing for beginners
- Manual management required

**Recommendation:** Stick to single-branch workflows until you're very comfortable with Git!

### Custom Preview Presets

You can customize how GitPDM generates previews by creating `.freecad-pdm/preset.json`:

**Example preset:**
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

**Options explained:**

- **thumbnail.size**: Resolution in pixels `[width, height]`
- **thumbnail.projection**: `"orthographic"` or `"perspective"`
- **thumbnail.view**: `"isometric"`, `"front"`, `"top"`, `"left"`, etc.
- **thumbnail.background**: Hex color code
- **thumbnail.showEdges**: Show/hide edge lines

- **mesh.linearDeflection**: Lower = more detail (but larger files)
- **mesh.angularDeflectionDeg**: Lower = smoother curves
- **mesh.relative**: Use relative deflection values

- **stats.precision**: Decimal places for measurements

**Where previews are stored:**
```
previews/
└── parts/
    └── mechanical/
        └── base/
            ├── preview.png       (Thumbnail)
            ├── preview.json      (Metadata: mass, volume, etc.)
            └── preview.glb       (3D model for web viewing)
```

### Architecture Overview (For Developers)

GitPDM follows a modular architecture:

**Core modules:**
- `auth/` - GitHub OAuth authentication
- `git/` - Git subprocess wrapper
- `github/` - GitHub API client
- `export/` - Preview generation pipeline
- `core/` - Shared utilities (logging, jobs, paths)
- `ui/` - User interface (panel + handlers)

**Key design patterns:**
- **Handler Pattern**: UI operations delegated to specialized handler classes
- **Async Jobs**: Long-running operations use Qt threading
- **Service Container**: Dependency injection for testability
- **Safety Guards**: Multiple layers prevent file corruption

**For contributing:** See repository's `CONTRIBUTING.md` (if available) or open an issue to discuss!

---
---

## 🗺️ Roadmap & Future Development

### ✅ Completed Milestones

GitPDM has come a long way! Here's what's already working:

**Sprint 0-3: Core Foundation** ✅
- Complete Git client with subprocess wrapper
- GitHub OAuth authentication (secure device flow)
- Repository management (create, clone, validate)
- Basic branch operations (create, switch, delete)
- Commit, push, fetch, and pull operations
- Dockable UI panel with Qt compatibility (PySide2/PySide6)

**Sprint 4: Code Quality** ✅
- Refactored 5000+ line monolithic panel into modular handlers
- Established clean architecture patterns
- 6 specialized UI handler modules
- Comprehensive error handling

**Sprint 5: Documentation** ✅ (Current!)
- Complete README rewrite for beginners
- Installation guides
- Tutorial walkthroughs
- Troubleshooting documentation

**Sprint 6-7: Preview Export System** ✅
- Automatic PNG thumbnail generation
- GLB/STL 3D model export
- JSON metadata manifests
- Configurable export presets
- One-click publish workflow
- Path mapping for preview organization

### ⚠️ Known Limitations & Active Issues

**Branch Switching Limitations**
- **Status:** Partially functional
- **Issue:** FreeCAD `.FCStd` files are ZIP archives that can corrupt during branch switches
- **Current Workaround:** Must close all documents before branch operations
- **Future Solution:** Enhanced worktree system with better automation

**Performance with Large Repositories**
- **Issue:** Repos with 1000s of files can be slow to scan
- **Workaround:** Use `.gitignore` to exclude unnecessary files
- **Future:** Implement caching and incremental updates

### 🔨 Next Up: Imminent Features

These features are planned for the immediate future (next 1-3 months):

**Enhanced Branch System (Sprint 8)**
- **Goal:** Make branch switching seamless and safe
- **Features:**
  - Automatic document closure before branch operations
  - Enhanced worktree wizard with guided setup
  - Per-worktree FreeCAD session management
  - Branch comparison view
- **Why it matters:** Enables proper feature-branch workflows
- **Estimated effort:** 2-3 weeks
- **Status:** Design phase

**Conflict Resolution UI (Sprint 9)**
- **Goal:** Help users resolve merge conflicts visually
- **Features:**
  - Detect merge conflicts after pull
  - Side-by-side file comparison
  - Choose "theirs", "ours", or manual merge
  - Guided conflict resolution workflow
- **Why it matters:** Essential for team collaboration
- **Estimated effort:** 2 weeks
- **Status:** Planned

**Git History Viewer (Sprint 10)**
- **Goal:** Visualize project timeline inside FreeCAD
- **Features:**
  - Commit log with messages and dates
  - Visual diff viewer (file changes)
  - One-click revert to previous version
  - Blame view (who changed what)
- **Why it matters:** Understand project evolution without leaving FreeCAD
- **Estimated effort:** 2-3 weeks
- **Status:** Design phase

**Improved Error Messages & Diagnostics**
- **Goal:** Make troubleshooting easier
- **Features:**
  - Diagnostic tool that checks Git installation, permissions, etc.
  - Friendly error messages with actionable solutions
  - One-click fixes for common issues
  - Health check system
- **Why it matters:** Reduces frustration for beginners
- **Estimated effort:** 1 week
- **Status:** Planned

### 🚀 Long-Term Vision (6+ months)

These features would significantly enhance GitPDM but require more time or external contributions:

**Pull Request Integration**
- **Vision:** Create and review GitHub pull requests from within FreeCAD
- **Features:**
  - Create PR with description from FreeCAD
  - View PR status and comments
  - Merge PRs from the panel
  - Code review workflow for CAD files
- **Benefit:** Full GitHub workflow without leaving FreeCAD
- **Blockers:** Requires GitHub API integration work
- **Looking for:** Contributor with GitHub API experience

**Multi-Repository Support**
- **Vision:** Work on multiple projects simultaneously
- **Features:**
  - Repository list/switcher
  - Quick switch between projects
  - Persistent repository settings
  - Workspace management
- **Benefit:** Manage complex projects with multiple repos
- **Blockers:** UI redesign needed for repo selection
- **Looking for:** UI/UX designer to help with mockups

**Advanced Git Operations**
- **Vision:** Support power-user Git workflows
- **Features:**
  - Interactive rebase
  - Cherry-pick commits
  - Stash changes
  - Tag management and releases
  - Submodule support
- **Benefit:** Professional-grade version control
- **Blockers:** Requires extensive testing, complex UI
- **Looking for:** Git expert for design guidance

**Automated Testing & CI/CD**
- **Vision:** Run automated tests on CAD files
- **Features:**
  - Run FreeCAD Python scripts on commit
  - Validate assemblies automatically
  - Check for missing dependencies
  - Generate previews automatically (GitHub Actions)
- **Benefit:** Catch errors before they break projects
- **Blockers:** Requires CI/CD expertise, GitHub Actions setup
- **Looking for:** DevOps contributor

**Team Collaboration Features**
- **Vision:** Better support for team workflows
- **Features:**
  - Assign parts to team members
  - Track "who's working on what"
  - Review and approval workflows
  - Comment system on parts
- **Benefit:** Coordinate design teams
- **Blockers:** Requires server/backend or GitHub integration
- **Looking for:** Full-stack developer

**Assembly Change Tracking**
- **Vision:** Detect when referenced parts change
- **Features:**
  - Notify when linked parts are updated
  - Visual indicators for out-of-date references
  - One-click update of assembly references
  - Dependency graph visualization
- **Benefit:** Keep assemblies in sync automatically
- **Blockers:** Requires deep FreeCAD assembly integration
- **Looking for:** FreeCAD core contributor

**Cloud Hosting Options**
- **Vision:** Support GitLab, Bitbucket, self-hosted Git
- **Features:**
  - GitLab OAuth integration
  - Bitbucket support
  - Generic Git server support
  - SSH key management
- **Benefit:** Not locked into GitHub
- **Blockers:** Each platform needs custom OAuth/API work
- **Looking for:** Contributors familiar with these platforms

**Revision Tagging & Releases**
- **Vision:** Formal release management
- **Features:**
  - Tag versions (v1.0, v2.0, etc.)
  - Create GitHub releases with notes
  - Attach export files (STEP, STL) to releases
  - Semantic versioning support
- **Benefit:** Professional release management
- **Blockers:** UI design for release workflow
- **Looking for:** Product manager / release process expert

### 💰 Funding & Support

GitPDM is open-source and free, developed in our spare time. If you find it useful, consider:

**Ways to support development:**

1. **Contribute Code**
   - Pick an issue from the "good first issue" label
   - Submit PRs for bug fixes
   - Implement features from the roadmap

2. **Write Documentation**
   - Improve tutorials
   - Create video guides
   - Translate to other languages
   - Add examples

3. **Report Bugs & Request Features**
   - Open issues on GitHub
   - Provide detailed reproduction steps
   - Share your use cases

4. **Sponsor Development** (If available)
   - GitHub Sponsors (if set up)
   - Buy the developer a coffee: [Link to sponsor page]
   - Commission specific features

5. **Spread the Word**
   - Blog about GitPDM
   - Share on social media
   - Recommend to CAD communities
   - Star the repo on GitHub ⭐

### 🤝 Contributing

Want to help build GitPDM? We'd love your contribution!

**Areas where we need help:**
- 🐛 **Bug fixes** - Help make GitPDM more stable
- 📚 **Documentation** - Improve guides and tutorials
- 🎨 **UI/UX** - Design better interfaces
- 🧪 **Testing** - Test on different OS and FreeCAD versions
- 🌍 **Translations** - Make GitPDM accessible worldwide
- 🚀 **Features** - Implement roadmap items

**How to contribute:**

1. **Check existing issues**: https://github.com/nerd-sniped/GitPDM/issues
2. **Fork the repository**
3. **Create a feature branch**: `git checkout -b feature/my-cool-feature`
4. **Make your changes** with good commit messages
5. **Test thoroughly** (on your OS + FreeCAD version)
6. **Submit a pull request** with description

**Contribution guidelines:**
- Follow existing code style (see `pyproject.toml` for Ruff config)
- Add tests if adding features
- Update documentation for user-facing changes
- Be respectful and constructive in discussions

**Development setup:**
```bash
# Clone the repository
git clone https://github.com/nerd-sniped/GitPDM.git
cd GitPDM

# Install development dependencies (optional)
pip install ruff  # For linting

# Link to FreeCAD Mod folder for testing
# (symlink the GitPDM folder to your FreeCAD Mod directory)
```

---

## 📋 Requirements Summary

**What you need to use GitPDM:**

| Requirement | Version | Notes |
|-------------|---------|-------|
| **FreeCAD** | 0.20, 0.21, or 1.0 | Get from https://www.freecad.org/ |
| **Git** | 2.20+ | Get from https://git-scm.com/ |
| **Python** | 3.8+ | Bundled with FreeCAD |
| **PySide2 or PySide6** | Any | Bundled with FreeCAD |
| **GitHub Account** | N/A | Optional, for cloud features |
| **Git LFS** | 2.0+ | Recommended for large files |

**Operating Systems:**
- ✅ Windows 10/11
- ✅ macOS 10.15+
- ✅ Linux (Ubuntu, Debian, Fedora, Arch, etc.)

**Internet Connection:**
- Required for GitHub features (clone, push, pull, OAuth)
- Not required for local-only Git operations

---

## 🆘 Support & Community

### Getting Help

**📖 Start here:**
1. Read this README (especially [Troubleshooting](#-troubleshooting--common-issues))
2. Check [FreeCAD's Report View](#getting-help) for error details
3. Search [existing issues](https://github.com/nerd-sniped/GitPDM/issues)

**💬 Ask questions:**
- **GitHub Discussions**: [Coming soon]
- **FreeCAD Forum**: Post in the Addons section
- **GitHub Issues**: For bug reports and feature requests

**🐛 Report a bug:**

1. Go to: https://github.com/nerd-sniped/GitPDM/issues/new
2. Use the bug report template
3. Include:
   - OS and FreeCAD version
   - GitPDM version
   - What you expected to happen
   - What actually happened
   - Error messages from Report View
   - Steps to reproduce

**💡 Request a feature:**

1. Check the [Roadmap](#-roadmap--future-development) - might already be planned!
2. Open an issue with the "feature request" label
3. Describe:
   - What you want to do
   - Why it's useful
   - How you imagine it working

### Community Guidelines

- Be respectful and constructive
- Help others when you can
- Share your workflows and tips
- Celebrate successes (first commit, first PR, etc!)

### Staying Updated

**How to get notified about new features:**
- ⭐ **Star the repository** on GitHub
- 👁️ **Watch releases** for version announcements
- 📰 Follow development updates (if blog/social media links available)

---

## 📜 License

MIT License (to be confirmed - check repository for definitive license)

Copyright (c) 2025 GitPDM Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

[Standard MIT License text...]

---

## 🙏 Acknowledgments

GitPDM stands on the shoulders of giants:

- **FreeCAD Community** - For building an amazing open-source CAD platform
- **Git** - Linus Torvalds and the Git development team
- **GitHub** - For hosting and excellent APIs
- **Qt/PySide** - For the UI framework
- **All Contributors** - Everyone who's contributed code, docs, and ideas!

---

## 📚 Additional Resources

### Learn More About Git
- **Git Handbook**: https://guides.github.com/introduction/git-handbook/
- **Pro Git Book** (free): https://git-scm.com/book/en/v2
- **GitHub Learning Lab**: https://lab.github.com/
- **Visual Git Guide**: https://marklodato.github.io/visual-git-guide/index-en.html

### Learn More About FreeCAD
- **Official FreeCAD Documentation**: https://wiki.freecad.org/
- **FreeCAD Forum**: https://forum.freecadweb.org/
- **FreeCAD YouTube Tutorials**: Search "FreeCAD tutorial"

### Related Projects
- **FreeCAD-Git**: Another Git integration approach
- **Assembly 4**: Popular FreeCAD assembly workbench
- **KiCad**: PCB design tool with good Git integration (inspiration!)

---

## 📝 Changelog

### Version 0.8.0 (Current - Production Ready)
- ✅ Complete Git workflow (commit, push, pull, fetch)
- ✅ GitHub OAuth authentication
- ✅ Repository management (create, clone, validate)
- ✅ Branch operations with safety guards
- ✅ Preview export system (PNG, JSON, GLB, STL)
- ✅ One-click publish workflow
- ✅ Modular architecture (6 UI handlers)
- ✅ Cross-platform support (Windows, Mac, Linux)
- ✅ FreeCAD 0.20, 0.21, and 1.0 compatibility
- ⚠️ Branch switching requires closed documents

### Future Versions
See [Roadmap](#-roadmap--future-development) for planned features!

---

## ❓ FAQ (Frequently Asked Questions)

**Q: Do I need to know Git to use GitPDM?**
A: No! This guide teaches you everything you need. GitPDM simplifies Git for CAD users.

**Q: Is my data safe with GitPDM?**
A: Yes! Your files are stored locally and optionally backed up to GitHub. Git is battle-tested version control used by millions of developers.

**Q: Can I use GitPDM without GitHub?**
A: Yes! GitHub features are optional. You can use local Git version control without connecting to any remote service.

**Q: Will GitPDM slow down FreeCAD?**
A: No. All Git operations run in the background without blocking the UI. FreeCAD remains responsive.

**Q: Can I collaborate with others?**
A: Yes! Push your project to GitHub and teammates can clone it. Everyone can work independently and merge changes.

**Q: What happens if two people edit the same file?**
A: Git will detect the conflict when you try to merge. GitPDM will show a warning, and you'll need to resolve it (future versions will have a UI for this).

**Q: Can I use this for commercial projects?**
A: Yes! GitPDM is MIT licensed (open source). Use it however you want. Check your employer's policies on using open-source software.

**Q: Does it work with assemblies?**
A: Yes! You can commit assemblies and their component parts together. GitPDM tracks all `.FCStd` files.

**Q: Can I use it for other file types (STEP, STL, etc.)?**
A: Yes! Git tracks any file type. GitPDM is optimized for `.FCStd` files but works with any files in your repository.

**Q: How much does it cost?**
A: GitPDM is completely free and open-source! GitHub is also free for public and private repositories (with some limits on private repos).

**Q: What if I make a mistake and commit the wrong thing?**
A: You can revert commits or go back to previous versions. Git makes it hard to permanently lose data. See the Advanced Topics section for details.

**Q: Is there a file size limit?**
A: Git works best with files under 100MB. Use Git LFS for larger files. GitHub has some size limits (50MB soft limit, 100MB hard limit without LFS).

**Q: Can I see a demo before installing?**
A: [Link to demo video/screenshots once available]

---

**Happy designing with GitPDM!** 🎉🚀

If you have questions, suggestions, or just want to share what you're building, don't hesitate to reach out!

---



---

## 🏗️ Technical Architecture (For Developers)

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

### Qt Compatibility

GitPDM supports both PySide2 (Qt5) and PySide6 (Qt6), automatically detecting
which is available in your FreeCAD installation.

### Logging

GitPDM logs messages to the FreeCAD console (Report View). To see log output:

1. Enable the Report View: `View` > `Panels` > `Report view`
2. Log messages are prefixed with `[GitPDM]`

### Settings Persistence

Settings are stored in FreeCAD's parameter store at:
```
User parameter:BaseApp/Preferences/Mod/GitPDM
```

You can view/edit these manually via `Tools` > `Edit parameters...`

---
