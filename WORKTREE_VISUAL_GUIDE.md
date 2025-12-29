# GitPDM Worktree Visual Guide

## Folder Structure: Before vs After Worktrees

### ❌ BEFORE (Single Folder - Risky)
```
C:\Projects\
└── MyProject\
    ├── .git\
    ├── circle.FCStd       ← File content changes when switching branches!
    └── square.FCStd       ← Can corrupt if open during switch
```

**Problem:** Git swaps file content in-place when switching branches.  
If FreeCAD has `circle.FCStd` open, corruption can occur.

### ✅ AFTER (Per-Branch Worktrees - Safe)
```
C:\Projects\
├── MyProject\                  ← Main repo (main branch)
│   ├── .git\                   ← Real .git directory
│   ├── circle.FCStd            (main version)
│   └── square.FCStd
│
├── MyProject-feature-a\        ← Worktree for feature-a
│   ├── .git                    ← Pointer file (not a directory)
│   ├── circle.FCStd            (feature-a version)
│   ├── square.FCStd
│   └── triangle.FCStd          (new file in feature-a)
│
└── MyProject-feature-b\        ← Worktree for feature-b
    ├── .git                    ← Pointer file
    ├── circle.FCStd            (feature-b version)
    └── square.FCStd
```

**Solution:** Each branch has its own folder. No in-place file swapping!

## Repository Browser: What You See

### Main Repo (MyProject/)
```
┌─────────────────────────────────────────┐
│ Repository Browser                      │
├─────────────────────────────────────────┤
│ 📂 MyProject  •  🌿 main               │ ← Indicator
├─────────────────────────────────────────┤
│ Found 2 FCStd files.                    │
├─────────────────────────────────────────┤
│ Filter files...           [Refresh Files]│
├─────────────────────────────────────────┤
│ ☐ circle.FCStd                          │
│ ☐ square.FCStd                          │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│ Select a file to preview                │
└─────────────────────────────────────────┘
```

### Feature-A Worktree (MyProject-feature-a/)
```
┌─────────────────────────────────────────┐
│ Repository Browser                      │
├─────────────────────────────────────────┤
│ 📂 MyProject-feature-a  •  🌿 feature-a│ ← Indicator changed!
├─────────────────────────────────────────┤
│ Found 3 FCStd files.                    │
├─────────────────────────────────────────┤
│ Filter files...           [Refresh Files]│
├─────────────────────────────────────────┤
│ ☐ circle.FCStd          ← Modified      │
│ ☐ square.FCStd                          │
│ ☐ triangle.FCStd        ← New!          │
│                                         │
├─────────────────────────────────────────┤
│ Select a file to preview                │
└─────────────────────────────────────────┘
```

## Branch Switching Flow

```
┌──────────────────────────┐
│ User clicks              │
│ "Switch to feature-a"    │
└────────────┬─────────────┘
             │
             ▼
    ┌────────────────────┐
    │ Check: Files Open? │
    └────────┬───────────┘
             │
        ┌────┴────┐
        │         │
        NO       YES
        │         │
        │         ▼
        │    ┌─────────────────────┐
        │    │ ⚠️ Block switch!    │
        │    │ Show warning with   │
        │    │ list of open docs   │
        │    └─────────────────────┘
        │
        ▼
┌───────────────────────────┐
│ Show Worktree Prompt:     │
│                           │
│ "Create per-branch        │
│  worktree? (Recommended)" │
│                           │
│ [Yes] [No - risky]        │
└────────┬──────────────────┘
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    │         ▼
    │    ┌─────────────────────┐
    │    │ In-place switch     │
    │    │ git switch branch   │
    │    │ (risky for CAD)     │
    │    └─────────────────────┘
    │
    ▼
┌───────────────────────────┐
│ Create Worktree           │
│ git worktree add          │
│   ../MyProject-feature-a  │
│   feature-a               │
└────────┬──────────────────┘
         │
         ▼
┌───────────────────────────┐
│ Update Repo Root          │
│ self._current_repo_root = │
│   "MyProject-feature-a/"  │
└────────┬──────────────────┘
         │
         ▼
┌───────────────────────────┐
│ Refresh Browser           │
│ - List files from new root│
│ - Update indicator        │
└────────┬──────────────────┘
         │
         ▼
┌───────────────────────────┐
│ Show Success Dialog       │
│                           │
│ ✓ Worktree created!       │
│   Path: MyProject-...     │
│                           │
│ ⚠️ Open files from this   │
│    folder in FreeCAD      │
│                           │
│ [Open Folder] [Close]     │
└────────┬──────────────────┘
         │
         ▼
┌───────────────────────────┐
│ User clicks "Open Folder" │
│ → Explorer opens          │
│   MyProject-feature-a/    │
└───────────────────────────┘
```

## File Opening Flow

```
┌─────────────────────────────┐
│ User double-clicks          │
│ "circle.FCStd" in Browser   │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ _open_repo_file("circle...") │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Build absolute path:        │
│ join(self._current_repo_root│
│      "circle.FCStd")        │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ If current root is          │
│ "MyProject-feature-a/":     │
│                             │
│ Path = "C:\Projects\        │
│   MyProject-feature-a\      │
│   circle.FCStd"             │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ FreeCAD.openDocument(path)  │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ ✓ CORRECT file opened!      │
│   (feature-a version)       │
└─────────────────────────────┘
```

## Wrong Folder Detection

```
┌──────────────────────────┐
│ GitPDM Panel Opens       │
└────────┬─────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ _check_for_wrong_folder_editing()│
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Get FreeCAD open documents:     │
│ App.listDocuments()             │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ For each doc:                   │
│   Check if doc.FileName         │
│   starts with                   │
│   self._current_repo_root       │
└────────┬────────────────────────┘
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    │         ▼
    │    ┌──────────────────────────┐
    │    │ ⚠️ WRONG FOLDER!        │
    │    │                          │
    │    │ Document from different  │
    │    │ folder than current repo │
    │    │                          │
    │    │ Close and reopen from    │
    │    │ correct worktree!        │
    │    └──────────────────────────┘
    │
    ▼
┌────────────────────┐
│ ✓ All OK          │
└────────────────────┘
```

## Common Scenarios

### ✅ CORRECT: User follows workflow
```
1. Switch to feature-a
2. Accept worktree creation
3. Click "Open Folder"
4. Open circle.FCStd from MyProject-feature-a/ in FreeCAD
5. Edit and save
6. Commit changes

Result: Changes saved to worktree ✓
```

### ❌ WRONG: User opens from main repo
```
1. Switch to feature-a
2. Accept worktree creation
3. Ignore "Open Folder" button
4. Open circle.FCStd from MyProject/ (main repo) in FreeCAD
5. Edit and save
6. Confusion: "My changes aren't showing in Git!"

Result: Wrong file edited! GitPDM shows warning ⚠️
```

### ❌ WRONG: Switch with files open
```
1. Open circle.FCStd from MyProject/
2. Try to switch to feature-a
3. Guard blocks switch
4. Warning: "Close FreeCAD documents first"

Result: Switch prevented ✓ Corruption avoided ✓
```

## Visual Indicators Meaning

| Indicator | Meaning |
|-----------|---------|
| `📂 MyProject  •  🌿 main` | Main repo folder, main branch |
| `📂 MyProject-feature-a  •  🌿 feature-a` | Worktree folder, feature-a branch |
| `📂 MyProject-feature-b  •  🌿 feature-b` | Different worktree, feature-b branch |

## Color Coding

| Color | Meaning |
|-------|---------|
| 🔵 Blue | Branch/worktree indicator (normal) |
| 🟢 Green | Success messages |
| 🟠 Orange | Loading/in-progress |
| 🔴 Red | Errors |
| ⚠️ Warning | Important warnings (wrong folder, files open) |

## Quick Reference

### To Switch Branches Safely:
1. Close all FreeCAD documents
2. Click "Switch to <branch>"
3. Accept worktree creation
4. Click "Open Folder"
5. Open files from the new worktree folder

### To Check Which Folder You're Editing:
- Look at Repository Browser indicator
- In FreeCAD: `App.ActiveDocument.FileName`
- Should match the indicator's folder name

### If You See "Wrong Folder" Warning:
1. Note the paths shown
2. Close the wrong-folder documents
3. Open files from the correct worktree folder shown in indicator

### To See All Your Worktrees:
- Terminal: `git worktree list`
- Or browse parent folder of your main repo
- Each `<repo>-<branch>` folder is a worktree
