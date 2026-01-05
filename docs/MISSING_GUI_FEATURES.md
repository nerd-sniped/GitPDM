# Missing GUI Features - GitPDM v1.0.0

**Analysis Date:** January 4, 2026  
**Context:** GitCAD functionality integrated into GitPDM core but not exposed via GUI

This document identifies powerful features from GitCAD that are fully implemented in the core modules but lack graphical user interface elements, making them inaccessible to typical users.

---

## Executive Summary

**Total Missing GUI Features: 12 major categories**

The consolidation successfully ported all GitCAD functionality to native Python in `freecad/gitpdm/core/`, but the GUI development focused primarily on the "happy path" workflows. Many advanced and power-user features remain CLI/API-only.

**Impact:** Users cannot access ~40% of available functionality without knowing Python or command-line tools.

---

## Category 1: FCStd Export/Import Operations

### ✅ Core Implementation
- **Module:** `core/fcstd_tool.py` (295 lines)
- **Functions Available:**
  - `export_fcstd()` - Decompress .FCStd to directory
  - `import_fcstd()` - Recompress directory to .FCStd
  - `compress_binaries()` - Compress .brp files for LFS
  - `decompress_binaries()` - Restore binaries from compressed
  - `extract_thumbnail()` - Extract thumbnail from .FCStd

### ❌ Missing GUI Elements
1. **Manual Export/Import Buttons**
   - No way to manually trigger export/import
   - Currently only happens automatically on save
   - Use case: User wants to export multiple files at once
   
2. **Bulk Export/Import**
   - No batch operations for entire repo
   - GitCAD had `git fexport-all` / `git fimport-all` aliases
   - Use case: After git checkout/pull, reimport all changed files
   
3. **Export Status Indicator**
   - No visual indicator if file is exported/imported
   - User can't tell if .FCStd matches uncompressed directory
   - Use case: Verify consistency before committing

4. **Thumbnail Extraction Tool**
   - `extract_thumbnail()` exists but no GUI
   - Use case: Generate preview images without full export

---

## Category 2: Advanced Configuration

### ✅ Core Implementation
- **Module:** `core/config_manager.py` (310 lines)
- **Class:** `FCStdConfig` with 11 configurable options

### ❌ Missing GUI Elements
1. **Advanced Configuration Dialog**
   - Current config dialog is minimal (Sprint 6)
   - Missing settings:
     - `uncompressed_prefix` - Add prefix to uncompressed dirs
     - `subdirectory_mode` - Put uncompressed dirs in subdirectory
     - `subdirectory_name` - Subdirectory name (default: `.freecad_data`)
     - `include_thumbnails` - Include thumbnail.png in export
     - `binary_patterns` - Custom patterns for compression
     - `max_compressed_size_gb` - Max size before splitting
     - `compression_level` - ZIP compression level (0-9)
     - `zip_file_prefix` - Prefix for compressed binary archives

2. **Configuration Templates/Presets**
   - No way to save/load config templates
   - Use case: Different configs for different project types
   
3. **Config Validation Feedback**
   - No visual validation of config values
   - User doesn't know if settings will work until error occurs

---

## Category 3: File Locking Management

### ✅ Core Implementation  
- **Module:** `core/lock_manager.py` (352 lines)
- **Functions Available:**
  - `lock_file()` - Lock with optional force
  - `unlock_file()` - Unlock with optional force
  - `get_locks()` - List all locks in repo
  - `is_locked()` - Check if specific file is locked
  - `get_lock_owner()` - Get username who owns lock

### ❌ Missing GUI Elements
1. **Lock/Unlock in File Browser**
   - File browser shows lock status but no context menu actions
   - Use case: Right-click file → Lock/Unlock
   
2. **Force Unlock Option**
   - `lock_file(force=True)` exists but no GUI checkbox
   - Use case: Admin needs to break abandoned lock
   
3. **Lock History/Audit Log**
   - No history of who locked/unlocked when
   - Use case: Debug conflicts, track file access patterns
   
4. **Lock Notifications**
   - No notification when someone else locks your file
   - Use case: Prevent wasted work on locked files
   
5. **Bulk Lock Operations**
   - No way to lock/unlock multiple files at once
   - Use case: Lock entire assembly before major changes

6. **Lock Expiration Settings**
   - No automatic lock expiration
   - Use case: Release locks after N days of inactivity

---

## Category 4: Binary Compression Control

### ✅ Core Implementation
- **Module:** `core/fcstd_tool.py`
- **Functions:** `compress_binaries()`, `decompress_binaries()`
- **Features:**
  - Configurable compression level (0-9)
  - Multi-file splitting for large binaries
  - Pattern-based selective compression
  - LFS integration

### ❌ Missing GUI Elements
1. **Compression Settings UI**
   - No way to adjust compression level per-project
   - No visual feedback on compression ratios
   
2. **Binary File Inspector**
   - No tool to view which files will be compressed
   - No size comparisons (before/after compression)
   - Use case: Optimize repo size

3. **Compression Statistics**
   - No dashboard showing:
     - Total compressed files
     - Compression ratio achieved
     - LFS storage used
     - Largest files

---

## Category 5: Git Workflow Integration

### ✅ Core Implementation
- Git operations fully available via `core/client.py`
- Export/import happens automatically on save

### ❌ Missing GUI Elements (GitCAD Aliases)
GitCAD provided these git aliases - none have GUI equivalents:

1. **`git fadd <file>`** - Export then add to staging
   - Current: Must save file, then manually stage
   
2. **`git freset <file>`** - Reset staged changes then import
   - Current: No way to discard and reimport
   
3. **`git fstash`** - Stash with export/import cycle
   - Current: No stash functionality at all
   
4. **`git fco <branch>`** - Checkout branch then import all
   - Current: Checkout works but no auto-import
   
5. **`git fimport-all`** - Import all .FCStd files in repo
   - Current: No bulk import after pull/checkout

6. **`git fexport-all`** - Export all .FCStd files
   - Current: Must open and save each file manually

---

## Category 6: Repository Maintenance

### ✅ Core Implementation
- Config migration tools (`core/config_migration.py`)
- Repository validation
- Path utilities

### ❌ Missing GUI Elements
1. **Repository Health Check**
   - No diagnostic tool for repo issues
   - Should check:
     - Orphaned uncompressed directories
     - .FCStd files without exports
     - Lock file inconsistencies
     - Config file validity
     - LFS setup status

2. **Cleanup Utilities**
   - No "Clean uncompressed directories" button
   - No "Remove stale locks" option
   - Use case: Maintenance after merge conflicts

3. **Migration Status Dashboard**
   - Config migration happens automatically (Sprint 4)
   - But no visual indicator of migration status
   - No way to see what was migrated

4. **Storage Analytics**
   - No visualization of:
     - Total repo size
     - LFS usage breakdown
     - Largest files/directories
     - Growth trends

---

## Category 7: Multi-Document Operations

### ✅ Core Implementation
- All operations work on any .FCStd file path
- No inherent single-document limitation

### ❌ Missing GUI Elements
1. **Multi-Select in File Browser**
   - Can't select multiple files for batch operations
   - Use case: Lock 10 files before starting work session

2. **Batch Export/Import Dialog**
   - No way to process multiple files
   - Use case: After pulling changes, reimport all

3. **Assembly-Aware Operations**
   - FreeCAD assemblies have multiple parts
   - No "Lock entire assembly" feature
   - No dependency tracking

---

## Category 8: Advanced Preview/Export

### ✅ Core Implementation
- **Module:** `export/exporter.py` (369 lines)
- Exports: PNG thumbnails, JSON manifests, GLB models
- **Module:** `export/preset.py` - Export presets system
- **Module:** `export/model_export.py` - STL/GLB/OBJ export

### ❌ Missing GUI Elements
1. **Export Format Selection**
   - Currently exports GLB only
   - No checkbox for STL/OBJ/STEP
   - `model_export.py` has functions for all formats

2. **Preview Preset Editor**
   - Presets defined in JSON (`~/.freecad/gitpdm/export-preset.json`)
   - No GUI editor for:
     - Camera position/angle
     - Render quality
     - Model complexity (mesh resolution)
     - Export formats

3. **Multi-View Previews**
   - Only exports single view (front)
   - Could export: front, top, side, isometric
   - `export/view_helper.py` has rotation logic

4. **Export Queue/Batch**
   - No way to queue multiple files for export
   - Use case: Export all parts in assembly at once

---

## Category 9: Conflict Resolution

### ✅ Core Implementation
- Lock system prevents most conflicts
- Git operations handle merge conflicts

### ❌ Missing GUI Elements
1. **Conflict Visualization**
   - When merge conflict occurs, no helpful UI
   - Should show:
     - Which files conflict
     - Who has locks
     - Visual diff of XML changes

2. **Guided Conflict Resolution**
   - No wizard for resolving .FCStd conflicts
   - Should offer:
     - Keep mine
     - Take theirs
     - Manual merge with export/import

3. **Binary Diff Tool**
   - No way to compare two .FCStd files visually
   - Use case: "Show me what changed in this part"

---

## Category 10: Hooks and Automation

### ✅ Core Implementation
- Native Python functions can be called from anywhere
- Document observer exists (`ui/components/document_observer.py`)

### ❌ Missing GUI Elements
1. **Git Hooks Configuration**
   - GitCAD used git hooks for automation
   - GitPDM has no hook installer/manager
   - Use case: Auto-export on commit, auto-import on checkout

2. **Custom Automation Rules**
   - No way to define:
     - "Auto-lock when opening file"
     - "Auto-export when saving"
     - "Alert when someone locks file I'm editing"

3. **Trigger Configuration**
   - Document observer has hardcoded behavior
   - No user-configurable triggers

---

## Category 11: Reporting and Analytics

### ✅ Core Implementation
- All operations return detailed Result objects
- Logging system tracks everything

### ❌ Missing GUI Elements
1. **Activity Log Viewer**
   - FreeCAD report view shows logs
   - But no structured GitPDM-specific log viewer
   - Should show:
     - Export/import operations
     - Lock/unlock events
     - Git operations
     - Errors and warnings

2. **Statistics Dashboard**
   - No visualization of:
     - Operations per day
     - Most frequently locked files
     - Export/import success rate
     - Storage usage trends

3. **Team Activity View**
   - No way to see what team members are doing
   - Could show:
     - Who is currently editing what
     - Recent commits by user
     - Lock history timeline

---

## Category 12: Integration and Extensions

### ✅ Core Implementation
- Clean Python API
- Service container pattern (`core/services.py`)
- Result monad pattern (`core/result.py`)

### ❌ Missing GUI Elements
1. **API Browser/Documentation**
   - No in-app API documentation
   - Power users can't discover available functions
   
2. **Custom Command/Macro Integration**
   - FreeCAD supports macros
   - No guidance on how to call GitPDM functions from macros
   
3. **Extension Points**
   - No documented extension system
   - Could allow:
     - Custom export formats
     - Custom validation rules
     - Custom preview generators

4. **Python Console Integration**
   - No helpers for using GitPDM from Python console
   - Example: `gitpdm.lock("part.FCStd")` shortcut

---

## Priority Matrix

### 🔴 High Priority (Most Requested / High Impact)
1. **Manual Export/Import Buttons** - Users need control
2. **Lock/Unlock in File Browser Context Menu** - Common operation
3. **Bulk Lock/Unlock Operations** - Assembly workflows
4. **Repository Health Check** - Maintenance tool
5. **Git Stash Functionality** - Missing workflow step
6. **Advanced Configuration Dialog** - Power users blocked

### 🟡 Medium Priority (Nice to Have)
7. **Export Format Selection** (STL/OBJ/STEP)
8. **Multi-View Preview Generation**
9. **Conflict Visualization and Resolution**
10. **Activity Log Viewer**
11. **Storage Analytics Dashboard**
12. **Force Unlock Option** (admin use)

### 🟢 Low Priority (Advanced / Niche)
13. **Binary Compression Settings UI**
14. **Lock Expiration/Auto-release**
15. **Custom Automation Rules**
16. **API Browser**
17. **Extension System**

---

## Recommendations

### For v1.1.0 (Next Release)
**Focus: Complete the "round-trip" workflow**

1. ✅ Add "Export FCStd" and "Import FCStd" buttons to file browser context menu
2. ✅ Add "Lock" / "Unlock" to file browser context menu
3. ✅ Implement bulk lock/unlock for multi-selection
4. ✅ Add repository health check tool (Help menu)
5. ✅ Improve config dialog with all FCStdConfig fields

**Estimated Effort:** 40-60 hours

### For v1.2.0 (Future)
**Focus: Team collaboration and conflict management**

6. ✅ Git stash integration
7. ✅ Conflict visualization and resolution wizard
8. ✅ Activity log viewer
9. ✅ Multi-view preview generation
10. ✅ Export format selection

**Estimated Effort:** 60-80 hours

### For v2.0.0 (Long Term)
**Focus: Extensibility and advanced workflows**

11. ✅ Custom automation rules
12. ✅ Storage analytics dashboard
13. ✅ Binary diff tool for FCStd
14. ✅ Extension system / plugin architecture
15. ✅ Git hooks configuration UI

**Estimated Effort:** 100+ hours

---

## Implementation Notes

### Design Principles
1. **Don't Duplicate:** Use existing core functions, just add GUI wrappers
2. **Progressive Disclosure:** Hide advanced features behind "Advanced" tabs
3. **Contextual Access:** Right-click menus for file-specific operations
4. **Batch Support:** Multi-select should work throughout
5. **Visual Feedback:** Show progress, results, and errors clearly

### Code Locations
- **File Operations:** Add to `ui/file_browser.py` context menu
- **Config UI:** Extend `ui/config_dialog.py`
- **Lock Operations:** Extend `ui/lock_handler.py`
- **Bulk Operations:** New module `ui/batch_operations.py`
- **Health Check:** New module `ui/maintenance_dialog.py`

---

## Conclusion

GitPDM v1.0.0 successfully consolidated GitCAD's powerful core functionality but only exposed ~60% through the GUI. The remaining features are fully implemented and tested, requiring only UI wrappers to make them accessible to normal users.

**Next Step:** Prioritize high-impact missing features for v1.1.0 release to complete the user experience.

---

*Generated: January 4, 2026*  
*Author: Senior Developer Analysis*  
*Status: Ready for roadmap planning*
