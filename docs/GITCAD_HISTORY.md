# GitCAD Project History

This document provides historical context about the GitCAD project and its integration into GitPDM.

---

## What Was GitCAD?

GitCAD was an innovative bash-based automation system for managing FreeCAD `.FCStd` files in Git repositories. Created by Michael Marais, it pioneered several techniques for version controlling FreeCAD projects.

### Original Repository
- **GitHub:** GitCAD (original standalone project)
- **Video Demo:** https://youtu.be/wSL3G5QyPD0
- **Video Tutorial:** https://youtu.be/oCrGdhwICGk
- **License:** MIT License (Copyright 2025 Michael Marais)

---

## Key Innovations from GitCAD

GitCAD introduced several groundbreaking features that have been incorporated into GitPDM:

### 1. **FCStd Decompression/Compression**
- Decompress `.FCStd` files (which are ZIP archives) into uncompressed directories
- Store human-readable XML files directly in Git for proper diffing
- Store binary files (`.brp`, `.Map.*`) in Git LFS with optional compression
- **Status in GitPDM:** ✅ Fully ported to native Python in `core/fcstd_tool.py`

### 2. **Git Clean Filter**
- Used Git filters to make `.FCStd` files appear "empty" to Git
- Automatically export on `git add`, import on checkout
- Kept `.FCStd` files in working directory synced with uncompressed data
- **Status in GitPDM:** ⚠️ Available via legacy hooks, native Python alternative planned

### 3. **File Locking Mechanism**
- Lock `.lockfile` inside uncompressed directory (not the `.FCStd` itself)
- Integrated with Git LFS locking
- Custom git aliases: `git lock`, `git unlock`, `git locks`
- Prevent multiple collaborators from editing same file
- **Status in GitPDM:** ✅ Fully ported to `core/lock_manager.py` with GUI support

### 4. **Binary Compression**
- Compress large binary files (`.brp`) before storing in LFS
- Multi-zip splitting for files over size limit
- Configurable patterns and compression levels
- **Status in GitPDM:** ✅ Implemented in `core/fcstd_tool.py`

### 5. **Git Hooks Integration**
- Pre-commit: Verify locks, enforce policies
- Post-merge/checkout: Auto-import changes to `.FCStd`
- Post-commit: Set readonly status on unlocked files
- **Status in GitPDM:** 🔄 Native Python alternative under development

---

## Why Consolidate?

Two independent development efforts emerged:

### GitCAD (Michael Marais)
**Strengths:**
- Battle-tested core logic
- Elegant bash-based automation
- Comprehensive git integration
- Proven in production use

**Limitations:**
- No graphical user interface
- Command-line only workflow
- Bash dependency (cross-platform challenges)
- Steep learning curve for non-technical users

### GitPDM (Nerd-Sniped Team)
**Strengths:**
- Beautiful Qt6-based GUI
- FreeCAD workbench integration
- GitHub OAuth authentication
- User-friendly wizards and dialogs

**Limitations:**
- Reinvented some core logic
- Initially lacked GitCAD's robustness
- Subprocess wrapper approach added complexity

---

## The Consolidation Journey

### Phase 1: Initial Integration (Early 2025)
- GitCAD included as subdirectory (`GitCAD-main/`)
- Wrapper layer (`freecad/gitpdm/gitcad/wrapper.py`) called bash scripts
- Subprocess overhead
- Dual project structure caused confusion

### Phase 2: Sprint 1 - Native Python Port (January 2026)
- Core logic ported from bash to Python:
  - `FCStdFileTool.py` → `core/fcstd_tool.py` ✅
  - Lock scripts → `core/lock_manager.py` ✅
  - Config parser → `core/config_manager.py` ✅
- Eliminated subprocess dependency
- Feature flag for gradual migration

### Phase 3: Sprint 3 - Repository Cleanup (January 2026)
- Removed `GitCAD-main/` nested directory
- Deleted bash wrapper layer
- Single unified codebase
- Pure FreeCAD 1.2 addon structure

### Phase 4: Complete Consolidation (Sprints 4-7)
- Remove all legacy bash dependencies
- Standardize configuration
- Polish and release GitPDM v1.0.0

---

## Attribution & Credit

### GitCAD Original Author
**Michael Marais**
- Created the original GitCAD project
- Pioneered `.FCStd` version control techniques
- Developed the compression and locking mechanisms
- MIT License (2025)

### GitPDM Team (Nerd-Sniped)
- Developed GUI and FreeCAD workbench integration
- Ported bash logic to native Python
- GitHub integration and OAuth
- Consolidated the projects

---

## Technical Legacy

### Key GitCAD Concepts Preserved

1. **Uncompressed Directory Structure**
   - Default: `filename_uncompressed/`
   - Configurable prefix/suffix/subdirectory
   - **Example:**
     ```
     MyPart.FCStd
     MyPart_uncompressed/
       ├── Document.xml
       ├── GuiDocument.xml
       ├── .lockfile (for locking)
       ├── binaries_0.zip (compressed .brp files)
       └── no_extension/ (files without extensions)
     ```

2. **Config.json Format**
   - Originally: `FreeCAD_Automation/config.json`
   - Now: `.gitpdm/config.json` (migrated in Sprint 4)
   - Backward compatible conversion layer maintained

3. **Locking Strategy**
   - Lock the `.lockfile`, not the `.FCStd`
   - Prevents storing entire `.FCStd` in LFS
   - Efficient for large files

### Git Aliases (Original GitCAD)
GitCAD introduced custom git aliases for FCStd workflows:
- `git fadd` - Export and add
- `git freset` - Reset and import
- `git fstash` - Stash with export/import
- `git fco` - Checkout with import
- `git fimport` - Manual import
- `git fexport` - Manual export
- `git lock` / `git unlock` / `git locks`

**GitPDM Approach:** GUI-based workflow replaces aliases for most users, but aliases remain available for power users.

---

## Alternative Approaches Considered

GitCAD's README mentioned Subversion (SVN) as an alternative:

### SVN Approach
- Native file locking support
- TortoiseSVN GUI shows lock icons
- Store entire `.FCStd` files (no decompression)
- Simpler setup, but less Git ecosystem benefits

### Why Git Was Chosen
- Better branching and merging
- Distributed workflows
- GitHub integration
- Industry standard for software development
- Git LFS for large binary files

---

## Migration Guide (For Original GitCAD Users)

If you have an existing repository using the original GitCAD bash scripts:

### Option 1: Continue Using GitCAD
- The original GitCAD project remains available
- Your existing repos will continue to work
- No migration necessary

### Option 2: Migrate to GitPDM
1. **Backup your repository**
2. **Install GitPDM** (FreeCAD 1.2.0+ required)
3. **Config Migration:** GitPDM will auto-detect and migrate `FreeCAD_Automation/config.json`
4. **Git Hooks:** Can optionally remove bash hooks, GitPDM handles this via workbench
5. **Aliases:** Still work if you want to use them, or use GitPDM GUI
6. **Locking:** Works identically (Git LFS-based)

See `docs/LEGACY_GITCAD_REPOS.md` (created in Sprint 4) for detailed migration steps.

---

## References

### Original GitCAD Documentation
The following GitCAD documentation has been preserved for reference:
- Git Aliases: `FreeCAD_Automation/docs/added-aliases.md` (if kept)
- Examples: `FreeCAD_Automation/docs/examples.md` (if kept)
- Configuration: See `core/config_manager.py` docstrings

### GitPDM Documentation
- Main README: `README.md`
- Architecture: `docs/ARCHITECTURE.md`
- Consolidation Plan: `CONSOLIDATION_PLAN.md`
- Sprint Reports: `docs/SPRINT_*_COMPLETE.md`

---

## Lessons Learned

### What Went Well
- GitCAD's core algorithms were sound and portable
- Native Python port proved feasible
- Git LFS integration worked across both approaches
- Compression strategies were effective

### Challenges
- Bash-to-Python translation required careful testing
- Platform differences (Windows vs Linux)
- Git filter complexity
- Balancing backward compatibility with modernization

### For Future Projects
- **Communicate early:** If these teams had talked sooner, consolidation would've been easier
- **Architecture first:** Design unified structure before implementing
- **Incremental migration:** Feature flags and gradual cutover worked well
- **Respect prior art:** GitCAD's innovations were valuable and worth preserving

---

## Acknowledgments

Thank you to **Michael Marais** for creating GitCAD and pioneering version control for FreeCAD files. The techniques you developed form the foundation of GitPDM's core functionality.

Thank you to the **Nerd-Sniped team** for recognizing the value of GitCAD's approach and building a user-friendly interface around it.

---

## License

### GitCAD Original Code
MIT License - Copyright (c) 2025 Michael Marais

### GitPDM Consolidated Project
MIT License - Copyright (c) 2026 Nerd-Sniped

All original GitCAD algorithms and techniques are preserved and attributed. The consolidation represents a evolution and enhancement of the original work, not a replacement.

---

*Last Updated: January 4, 2026 (Sprint 3)*
