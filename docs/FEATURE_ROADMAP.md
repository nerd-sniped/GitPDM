# GitPDM Feature Roadmap

**Last Updated:** January 4, 2026  
**Current Version:** v0.8.0 (Sprint 7 Complete)  
**Branch:** GitCADConsolidationAttempt

This roadmap outlines the planned feature development for GitPDM, focusing on exposing powerful backend functionality through user-friendly GUI interfaces.

---

## 🎯 Vision Statement

**Goal:** Make all GitCAD-consolidated functionality accessible to non-technical users through intuitive GUI controls, while maintaining the power and flexibility that advanced users expect.

**Success Metric:** 95%+ of backend functionality accessible via GUI by v1.0.0 (future release)

---

## ✅ Sprint 7 - COMPLETED (January 2026)

### Auto-Initialization & Lock System
**Status:** 🟢 Production Ready

**Completed Features:**
- ✅ Auto-initialization on repository open (no manual setup required)
- ✅ Panel auto-docking on FreeCAD startup
- ✅ Lock/unlock with multi-select support in file browser
- ✅ Context menu: Lock, Unlock, Force Lock
- ✅ Lock status indicators (icons, tooltips, owner display)
- ✅ "Show Locks" button lists all repository locks
- ✅ Lock status persists after refresh
- ✅ Git config reads repository-specific settings (not global)
- ✅ Terminal popup suppression on Windows
- ✅ Force lock properly implemented (unlock → lock workflow)

**Impact:** Lock system fully operational, ready for production use by teams.

**Lines of Code:** ~1200 lines across 4 files (lock_manager.py, lock_handler.py, file_browser.py, panel.py)

---

## 🚧 Sprint 8 - CURRENT PRIORITY (Q1 2026)

### Branch Operations & FCStd Synchronization
**Status:** 🟡 Backend Complete, GUI Disabled  
**Estimated Effort:** 30-40 hours  
**Target:** v1.1.0 Release

### Critical Requirements

#### 1. FCStd Export/Import Workflow (HIGH PRIORITY)
**Problem:** Branch operations create worktrees but don't synchronize .FCStd files, causing corruption.

**Solution:**
- [ ] Implement `export_all_fcstd()` function - exports all .FCStd files in repo
- [ ] Call export before branch switch operation
- [ ] Call `import_all_fcstd()` after branch switch completes
- [ ] Add progress dialog for bulk export/import operations
- [ ] Handle errors gracefully (skip files that can't export)

**Files to Modify:**
- `ui/branch_ops.py` lines 732-783 (`_create_and_open_worktree()`)
- `core/fcstd_tool.py` - add batch operation functions
- `ui/dialogs.py` - add progress dialog for export/import

**Testing:** Create branch, switch between branches, verify files open correctly in both worktrees.

#### 2. Manual Export/Import Controls
**User Story:** As a user, I want to manually export/import FCStd files so I can control when synchronization happens.

**Implementation:**
- [ ] Add "Export FCStd" button to file browser context menu
- [ ] Add "Import FCStd" button to file browser context menu
- [ ] Support multi-select (batch export/import)
- [ ] Show progress bar for operations
- [ ] Display results (success/failure counts)

**Success Criteria:** User can right-click any .FCStd file and export/import it.

#### 3. Branch UI Re-enablement
**Current State:** Fully implemented (880 lines), disabled with `setVisible(False)`

**Task:**
- [ ] Change `ui/panel.py` line 677 from `setVisible(False)` to `setVisible(True)`
- [ ] Add "Beta" badge or warning label to Branch section
- [ ] Update tooltips to explain worktree system
- [ ] Add worktree path display in status area
- [ ] Test all branch operations thoroughly

**Acceptance Criteria:** Branch operations work without file corruption, worktrees created successfully.

#### 4. Worktree Path Switching
**Problem:** After creating worktree, panel stays on original folder path.

**Solution:**
- [ ] Call `validate_repo_path()` with worktree path after creation
- [ ] Update file browser to show worktree files
- [ ] Add visual indicator showing which worktree is active
- [ ] Allow switching back to main folder

**User Experience:** Seamless transition to new worktree, clear indication of current context.

### Additional Sprint 8 Features

#### 5. Repository Health Check Tool
**Access:** Help menu → "Repository Health Check"

**Checks:**
- [ ] Orphaned `_uncompressed` directories (no matching .FCStd)
- [ ] .FCStd files without exports
- [ ] Stale lock files (locked by non-existent users)
- [ ] Git LFS setup status
- [ ] Config file validity
- [ ] Disk space usage

**Output:** Report dialog with fix buttons for common issues.

#### 6. Advanced Configuration Dialog
**Current:** Minimal config dialog (Sprint 6)  
**Goal:** Expose all FCStdConfig options

**New Settings:**
- [ ] `uncompressed_prefix` - Add prefix to uncompressed dirs
- [ ] `uncompressed_suffix` - Modify suffix (default: `_uncompressed`)
- [ ] `subdirectory_mode` - Put exports in subdirectory
- [ ] `subdirectory_name` - Subdirectory name (default: `.freecad_data`)
- [ ] `include_thumbnails` - Include thumbnail.png
- [ ] `binary_patterns` - Custom compression patterns
- [ ] `max_compressed_size_gb` - Max size before splitting
- [ ] `compression_level` - ZIP compression (0-9)

**UI Design:** Tabbed dialog with "Basic" and "Advanced" tabs.

---

## 📦 v1.1.0 Release - "Complete Workflow" (Q2 2026)

**Theme:** Enable full Git workflow with FCStd file management

### Features Included from Sprint 8
- ✅ Branch operations (create, switch, delete)
- ✅ Worktree management
- ✅ Manual export/import buttons
- ✅ Repository health check
- ✅ Advanced configuration dialog

### Additional Features

#### 7. Git Stash Integration
**User Story:** As a user, I want to stash my work-in-progress so I can switch contexts without committing.

**Implementation:**
- [ ] "Stash Changes" button in Changes section
- [ ] Stash list viewer (dialog)
- [ ] "Apply Stash" with dropdown selection
- [ ] "Pop Stash" (apply + delete)
- [ ] "Drop Stash" (delete without applying)
- [ ] Export/import cycle around stash operations

**Files:** New module `ui/stash_handler.py` (~200 lines)

#### 8. Bulk Operations Dialog
**Access:** File menu → "Batch Operations"

**Operations:**
- [ ] Export all .FCStd files
- [ ] Import all .FCStd files
- [ ] Lock multiple files (with pattern matching)
- [ ] Unlock all files owned by current user
- [ ] Generate previews for all files

**UI:** Checklist with filter/search, progress bar, results summary.

### Release Criteria
- [ ] All Sprint 8 features tested and working
- [ ] Documentation updated
- [ ] Migration guide for v0.8.0 users
- [ ] Performance testing with large repos (100+ files)
- [ ] Cross-platform testing (Windows, macOS, Linux)

**Estimated Release:** May 2026

---

## 🚀 v1.2.0 Release - "Team Collaboration" (Q3 2026)

**Theme:** Enhanced multi-user workflows and conflict management

### Major Features

#### 9. Conflict Resolution Wizard
**Trigger:** When merge conflict detected in .FCStd file

**Workflow:**
1. Detect conflict in .FCStd or `_uncompressed` files
2. Show dialog: "Conflict Detected in [filename]"
3. Options:
   - Keep My Version (discard theirs)
   - Take Their Version (discard mine)
   - Manual Merge (open both in separate tabs)
   - Export Both for Comparison
4. After resolution, auto-import and mark as resolved

**Files:** New module `ui/conflict_resolver.py` (~400 lines)

#### 10. Activity Log Viewer
**Access:** View menu → "GitPDM Activity Log"

**Display:**
- Filterable table of all operations
- Columns: Timestamp, Operation, File, User, Status, Details
- Filters: Operation type, date range, user, success/failure
- Export to CSV

**Data Source:** Structured logging to JSON file in `.gitpdm/activity.log`

#### 11. Multi-View Preview Generation
**Enhancement:** Export previews from multiple angles

**Settings:**
- [ ] Front, top, side, isometric views
- [ ] Custom camera angles (preset editor)
- [ ] Render quality per-view
- [ ] Batch generation for all files

**Usage:** Context menu → "Generate Previews" → Select views

#### 12. Export Format Selection
**Enhancement:** Allow multiple export formats simultaneously

**Formats:**
- [ ] GLB (current default)
- [ ] STL (for 3D printing)
- [ ] OBJ (for rendering)
- [ ] STEP (for CAD interop)

**UI:** Checkboxes in export dialog, format-specific settings

### Release Criteria
- [ ] Conflict resolution tested with real team scenarios
- [ ] Activity log handles high-volume operations (1000+ entries)
- [ ] Preview generation optimized (parallel processing)
- [ ] User testing with 5+ person teams

**Estimated Release:** August 2026

---

## 🔮 v2.0.0 Release - "Power User Tools" (Q4 2026)

**Theme:** Advanced features, automation, and extensibility

### Major Features

#### 13. Git Hooks GUI Manager
**Backend:** `git/hooks_manager.py` (342 lines, fully implemented)

**GUI:**
- [ ] List installed hooks
- [ ] Enable/disable hooks with toggle switches
- [ ] View hook scripts
- [ ] Test hooks manually
- [ ] Configure hook behavior (options dialog)

**Hooks Supported:**
- pre-commit (validate locks, enforce policies)
- post-checkout (auto-import changes)
- post-merge (auto-import merged files)
- post-rewrite (handle rebases)
- pre-push (verify all exports up-to-date)

#### 14. Storage Analytics Dashboard
**Access:** Tools menu → "Storage Analytics"

**Metrics:**
- Total repository size
- LFS usage breakdown (by file type)
- Largest files (top 20)
- Compression ratios
- Growth trends (chart)
- Worktree disk usage
- Uncompressed directory sizes

**Visualizations:** Charts using matplotlib or built-in Qt charts

#### 15. Custom Automation Rules
**User Story:** As a user, I want to define custom triggers so I can automate repetitive tasks.

**Examples:**
- Auto-lock when opening file in FreeCAD
- Auto-export on save
- Notify when teammate locks file I have open
- Auto-generate preview on commit
- Auto-unlock on FreeCAD close

**UI:** Rules editor with trigger/action pairs, enable/disable toggles

#### 16. Binary Diff Viewer for FCStd
**Feature:** Visual comparison of two .FCStd files

**Implementation:**
- [ ] Export both files to `_uncompressed`
- [ ] Show side-by-side XML diffs (Document.xml, GuiDocument.xml)
- [ ] Highlight changed objects in 3D view
- [ ] Show geometry differences (if possible)
- [ ] Integration with git diff workflow

#### 17. Lock Management Enhancements

**Lock Expiration:**
- [ ] Configure auto-release after N days
- [ ] "Stale Locks" report
- [ ] Admin force-unlock all stale locks

**Lock Notifications:**
- [ ] Real-time notifications when files are locked/unlocked
- [ ] Option to watch specific files
- [ ] Integration with system notifications (Windows toast, macOS notification center)

#### 18. Extension System / Plugin Architecture
**Goal:** Allow third-party extensions

**Components:**
- [ ] Plugin discovery (scan `~/.freecad/gitpdm/plugins/`)
- [ ] Plugin manifest format
- [ ] Extension points (hooks for custom behavior)
- [ ] API documentation for plugin developers
- [ ] Example plugins (custom exporters, validators)

### Release Criteria
- [ ] All features tested with power users
- [ ] Performance optimization (lazy loading, caching)
- [ ] Complete API documentation
- [ ] Plugin development guide
- [ ] Security review for extension system

**Estimated Release:** December 2026

---

## 🎨 Ongoing Improvements (All Versions)

### Performance Optimization
- Lazy loading of file lists (virtualized tables)
- Background threads for expensive operations
- Caching of lock status, git status
- Incremental refresh instead of full refresh

### User Experience
- Keyboard shortcuts for common operations
- Drag-and-drop support
- Customizable toolbar
- Dark mode support
- Localization (i18n) framework

### Documentation
- Video tutorials for common workflows
- Interactive getting-started guide
- Troubleshooting wiki
- API reference (Sphinx-generated)

### Testing & Quality
- Increase test coverage to 90%+ for all modules
- Automated UI testing (where possible)
- Performance benchmarks
- Memory leak detection
- Cross-platform CI/CD

---

## 📊 Progress Tracking

### Feature Accessibility Metrics

| Version | GUI-Accessible Features | Total Features | Percentage | Change |
|---------|-------------------------|----------------|------------|--------|
| v0.8.0 (Sprint 6) | ~60% | 100% | 60% | - |
| v0.8.0 (Sprint 7) | ~75% | 100% | 75% | +15% |
| v1.1.0 (Target) | ~85% | 100% | 85% | +10% |
| v1.2.0 (Target) | ~90% | 100% | 90% | +5% |
| v2.0.0 (Target) | ~95% | 100% | 95% | +5% |

### Sprint Completion Status

- ✅ Sprint 1-2: FreeCAD 1.2 Migration & Native Python Core
- ✅ Sprint 3: GitCAD-main Consolidation
- ✅ Sprint 4: Configuration System Overhaul
- ✅ Sprint 5: UI Refactoring (Phase 1)
- ✅ Sprint 6: GitHub OAuth & Config Dialog
- ✅ Sprint 7: Auto-Initialization & Lock System
- 🚧 Sprint 8: Branch Operations & FCStd Sync (In Progress)
- 🔜 Sprint 9-12: v1.1.0 Feature Development
- 🔜 Sprint 13-16: v1.2.0 Team Collaboration
- 🔜 Sprint 17-20: v2.0.0 Power User Tools

---

## 🎯 Success Criteria by Milestone

### v1.1.0 Success
- [ ] Users can create/switch branches without file corruption
- [ ] Manual export/import available in context menu
- [ ] Repository health check finds and fixes common issues
- [ ] All configuration options accessible via GUI
- [ ] Stash workflow functional

### v1.2.0 Success
- [ ] Teams of 5+ can collaborate without confusion
- [ ] Conflicts are resolved through wizard (no command line needed)
- [ ] Activity log provides audit trail
- [ ] Multi-view previews generate successfully

### v2.0.0 Success
- [ ] Advanced users can customize automation rules
- [ ] Storage analytics help optimize repository size
- [ ] Git hooks managed entirely through GUI
- [ ] Plugin system has 2+ community extensions
- [ ] 95%+ of features accessible via GUI

---

## 🚀 Getting Started Contributing

Interested in helping build these features?

1. **Pick a Feature:** Check issues tagged with the corresponding milestone
2. **Read the Spec:** See [MISSING_GUI_FEATURES.md](docs/MISSING_GUI_FEATURES.md) for implementation details
3. **Set Up Dev Environment:** Follow [CONTRIBUTING.md](CONTRIBUTING.md)
4. **Submit PR:** Reference this roadmap in your pull request

**High-Impact, Good First Issues:**
- Manual export/import buttons (Sprint 8, item #2)
- Lock expiration settings (v2.0.0, item #17)
- Storage analytics dashboard (v2.0.0, item #14)

---

## 📅 Release Schedule

| Milestone | Target Date | Status |
|-----------|-------------|--------|
| Sprint 7 Complete | ✅ January 4, 2026 | Done |
| Sprint 8 Start | January 7, 2026 | Starting |
| v1.1.0 Beta | April 2026 | Planned |
| v1.1.0 Release | May 2026 | Planned |
| v1.2.0 Beta | July 2026 | Planned |
| v1.2.0 Release | August 2026 | Planned |
| v2.0.0 Beta | November 2026 | Planned |
| v2.0.0 Release | December 2026 | Planned |

---

## 💬 Feedback & Prioritization

This roadmap is a living document. Priorities may shift based on:
- User feedback and feature requests
- Technical discoveries during implementation
- Team capacity and resources
- Community contributions

**Have feedback?** Open a discussion in GitHub Discussions or comment on related issues.

---

*Last Updated: January 4, 2026*  
*Maintainer: Nerd-Sniped Development Team*  
*Status: Sprint 7 Complete, Sprint 8 Planning*
