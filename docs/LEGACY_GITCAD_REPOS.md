# Legacy GitCAD Repository Support

This document provides guidance for users who have existing repositories initialized with the original bash-based GitCAD system and want to use GitPDM.

---

## Overview

If you have an existing repository that was set up with the original GitCAD bash scripts, you have two options:

1. **Continue using GitCAD** - Your existing setup will keep working
2. **Migrate to GitPDM** - Get GUI support and native Python implementation

---

## Option 1: Continue Using GitCAD

### When to Choose This
- You're comfortable with command-line git workflows
- Your team already knows the GitCAD aliases
- You don't need GUI support
- "If it ain't broke, don't fix it"

### What You Need
- Keep your `FreeCAD_Automation/` directory
- Continue using bash scripts and git aliases
- Original GitCAD documentation applies

### Compatibility
GitPDM can coexist with GitCAD bash scripts in the same repository. The configuration format is compatible.

---

## Option 2: Migrate to GitPDM

### Benefits
- **GUI Interface** - Visual panels in FreeCAD workbench
- **No Bash Dependency** - Pure Python implementation
- **Better Cross-Platform** - Works identically on Windows/Mac/Linux  
- **GitHub Integration** - OAuth, repo creation, etc.
- **Modern FreeCAD** - Native support for FreeCAD 1.2+

### Migration Process

#### Step 1: Backup Your Repository
```bash
# Create a backup branch
git checkout -b backup-before-gitpdm-migration
git push origin backup-before-gitpdm-migration

# Return to main branch
git checkout main
```

#### Step 2: Install GitPDM
1. Open FreeCAD 1.2.0 or newer
2. Go to **Tools → Addon Manager**
3. Search for "GitPDM"
4. Click **Install**
5. Restart FreeCAD

#### Step 3: Open Your Repository in GitPDM
1. Activate **Git PDM** workbench
2. Click **"Toggle GitPDM Panel"**
3. Browse to your existing repository
4. GitPDM will detect it's a git repository

#### Step 4: Configuration Migration (Automatic)
GitPDM will automatically detect your `FreeCAD_Automation/config.json` and:
- Migrate settings to `.gitpdm/config.json` (new native format)
- Preserve all your configuration choices
- Create a backup of the original

**What Gets Migrated:**
- Uncompressed directory naming (prefix/suffix)
- Subdirectory mode settings
- Binary compression settings
- File patterns for compression
- Lock requirements

#### Step 5: Test Basic Operations
Test that everything still works:

1. **Open an existing .FCStd file** in your repository
2. **Make a small change** and save
3. **Check git status** - file should be tracked
4. **Commit** using GitPDM panel
5. **Verify** uncompressed directory updated correctly

#### Step 6: (Optional) Remove Bash Scripts
If everything works, you can optionally remove the bash components:

```bash
# The FreeCAD_Automation directory can be removed
# GitPDM no longer needs it
rm -rf FreeCAD_Automation/

# Or move it to a backup location
mv FreeCAD_Automation/ FreeCAD_Automation.backup/
```

**Note:** Keep `FreeCAD_Automation/` if:
- Other team members still using bash GitCAD
- You want to keep git hooks for now
- You're not sure yet

---

## Configuration Comparison

### Legacy (GitCAD - FreeCAD_Automation/config.json)
```json
{
  "freecad-python-instance-path": "/path/to/python",
  "require-lock-to-modify-FreeCAD-files": true,
  "uncompressed-directory-structure": {
    "uncompressed-directory-suffix": "_uncompressed",
    "uncompressed-directory-prefix": "",
    "subdirectory": {
      "put-uncompressed-directory-in-subdirectory": false,
      "subdirectory-name": ".freecad_data"
    }
  },
  "compress-non-human-readable-FreeCAD-files": {
    "enabled": true,
    "files-to-compress": ["*.brp", "*.Map.*", "no_extension/*"],
    "max-compressed-file-size-gigabyte": 2.0,
    "compression-level": 6,
    "zip-file-prefix": "binaries_"
  }
}
```

### New (GitPDM - .gitpdm/config.json)
```json
{
  "uncompressed_suffix": "_uncompressed",
  "uncompressed_prefix": "",
  "subdirectory_mode": false,
  "subdirectory_name": ".freecad_data",
  "include_thumbnails": false,
  "require_lock": true,
  "compress_binaries": true,
  "binary_patterns": ["*.brp", "*.Map.*", "no_extension/*"],
  "max_compressed_size_gb": 2.0,
  "compression_level": 6,
  "zip_file_prefix": "binaries_"
}
```

**Key Differences:**
- Simpler, flatter structure
- Python naming conventions (underscores, not hyphens)
- No `freecad-python-instance-path` (not needed in addon)
- No `require-GitCAD-activation` (GUI-based, always active)

---

## Git Hooks & Filters

### What GitCAD Used
GitCAD installed several git hooks:
- **Clean filter** - Export `.FCStd` on `git add`
- **Pre-commit** - Verify locks, enforce policies
- **Post-merge** - Auto-import to `.FCStd`
- **Post-checkout** - Sync working directory

### GitPDM Approach
GitPDM uses **on-demand operations** instead of automatic hooks:
- **GUI Actions** trigger export/import explicitly
- **More predictable** behavior (no surprises)
- **Better error handling** with user feedback

### Migration Notes
- Existing git hooks will remain but won't interfere
- GitPDM doesn't auto-install hooks (GUI-driven workflow)
- You can remove hooks if desired: `rm -rf .git/hooks/*`

---

## File Locking

### Compatibility
File locking is **100% compatible** between GitCAD and GitPDM:
- Both use Git LFS locking
- Lock the same `.lockfile` in uncompressed directory
- Locks are per-repo, not per-client

### GitCAD Command Line
```bash
git lock path/to/file.FCStd
git unlock path/to/file.FCStd
git locks  # List locks
```

### GitPDM GUI
1. Right-click file in panel
2. Select **"Lock File"** or **"Unlock File"**
3. View locks in lock panel

**Note:** You can use both! Command-line locks work with GUI and vice versa.

---

## Uncompressed Directory Structure

### Unchanged
The on-disk structure is **identical** between GitCAD and GitPDM:

```
MyPart.FCStd
MyPart_uncompressed/
  ├── Document.xml         # XML document data
  ├── GuiDocument.xml      # GUI view data
  ├── .lockfile            # Lock file (if locked)
  ├── binaries_0.zip       # Compressed binary files
  └── no_extension/        # Files without extensions
```

This means:
- ✅ Existing repos work as-is
- ✅ Git history preserved
- ✅ Can switch between GitCAD and GitPDM
- ✅ Team members can use different tools

---

## Common Migration Issues

### Issue 1: "FreeCAD_Automation not found"
**Symptom:** Warning about missing FreeCAD_Automation  
**Solution:** This is expected. GitPDM no longer needs it. Configuration has been migrated to `.gitpdm/`

### Issue 2: "Config file not migrated"
**Symptom:** Using defaults instead of your settings  
**Solution:**
1. Check if `.gitpdm/config.json` exists
2. If not, manually migrate:
   ```python
   from freecad.gitpdm.core.config_migration import migrate_config
   migrate_config(Path("/path/to/repo"))
   ```

### Issue 3: "Git hooks not working"
**Symptom:** `.FCStd` files not auto-updating  
**Solution:** GitPDM uses GUI-triggered operations, not automatic hooks. Use the panel to commit/push.

### Issue 4: "Can't find my old config"
**Symptom:** Where did my configuration go?  
**Solution:** Check `.gitpdm/config.json` (new location). Original backed up as `FreeCAD_Automation/config.json.backup`

---

## Team Migration Strategies

### Strategy 1: Gradual (Recommended)
1. One person migrates and tests thoroughly
2. Document any issues or differences
3. Other team members migrate one-by-one
4. Keep `FreeCAD_Automation/` until everyone migrated

### Strategy 2: All-at-Once
1. Schedule migration during low-activity period
2. Everyone migrates together in video call
3. Test collectively
4. Rollback plan ready if issues

### Strategy 3: Hybrid (Long-term)
1. Some team members use GitCAD (command-line preference)
2. Others use GitPDM (GUI preference)
3. Both coexist peacefully (configs compatible)
4. Eventually everyone on GitPDM

---

## Rollback Procedure

If you need to go back to GitCAD:

1. **Restore backup branch:**
   ```bash
   git checkout backup-before-gitpdm-migration
   ```

2. **Restore FreeCAD_Automation:**
   ```bash
   mv FreeCAD_Automation.backup/ FreeCAD_Automation/
   ```

3. **Reinstall git hooks:**
   ```bash
   ./FreeCAD_Automation/user_scripts/init-repo
   ```

4. **Remove .gitpdm directory (optional):**
   ```bash
   rm -rf .gitpdm/
   ```

---

## FAQ

### Q: Will my git history be preserved?
**A:** Yes, 100%. GitPDM uses the same uncompressed directory structure. Your entire git history remains intact.

### Q: Can I use both GitCAD and GitPDM?
**A:** Yes! They're compatible. Some team members can use CLI (GitCAD) while others use GUI (GitPDM).

### Q: Do I have to migrate?
**A:** No. GitCAD continues to work. Migration is optional for GUI benefits.

### Q: What about performance?
**A:** GitPDM's native Python implementation is faster than bash subprocess calls. Most operations are quicker.

### Q: Will GitPDM break my existing setup?
**A:** No. GitPDM reads your existing config and structure. It doesn't modify anything unless you explicitly commit changes.

### Q: Can I go back to GitCAD after migrating?
**A:** Yes, see "Rollback Procedure" above. The on-disk format is identical.

### Q: What happens to my git aliases?
**A:** Git aliases continue to work. GitPDM doesn't remove or modify them. Use whatever you prefer.

### Q: Do I need FreeCAD 1.2?
**A:** Yes, GitPDM requires FreeCAD 1.2.0+. If you're on older FreeCAD, stick with GitCAD or upgrade FreeCAD first.

---

## Getting Help

### For GitCAD (Legacy) Issues
- Original GitCAD README (see `docs/GITCAD_HISTORY.md`)
- GitCAD video tutorials (links in history doc)

### For GitPDM Issues
- GitHub Issues: https://github.com/nerd-sniped/GitPDM/issues
- Documentation: `/docs/README.md`
- FreeCAD Forums: Tag @GitPDM

### For Migration Help
- Check this document first
- Create GitHub issue with "migration" label
- Include error messages and config files

---

## Technical Details

### Configuration Migration Logic
```python
# Automatic detection
needs_migration = (
    legacy_config_exists and
    not new_config_exists
)

# Migration process
1. Load FreeCAD_Automation/config.json
2. Parse into FCStdConfig dataclass
3. Save to .gitpdm/config.json (native format)
4. Create backup of original
5. Leave migration marker file
```

### File Operation Compatibility
| Operation | GitCAD (Bash) | GitPDM (Python) | Compatible |
|-----------|---------------|-----------------|------------|
| Export FCStd | `FCStdFileTool.py` | `core/fcstd_tool.py` | ✅ Yes |
| Import FCStd | `FCStdFileTool.py` | `core/fcstd_tool.py` | ✅ Yes |
| Lock file | `git lock` alias | `core/lock_manager.py` | ✅ Yes |
| Unlock file | `git unlock` alias | `core/lock_manager.py` | ✅ Yes |
| Compression | Bash script | Native Python | ✅ Yes |

### Uncompressed Directory Calculation
Both systems use identical logic:
```python
uncompressed_dir = (
    parent_dir /
    (prefix + base_name + suffix)
)

# Example: "part.FCStd" → "part_uncompressed/"
```

---

## Summary Checklist

Before migrating:
- [ ] Repository backed up (backup branch created)
- [ ] Team informed of migration plan
- [ ] Current config documented
- [ ] FreeCAD 1.2.0+ installed
- [ ] GitPDM addon installed

During migration:
- [ ] GitPDM detects existing repo
- [ ] Config migrated automatically
- [ ] Settings verified in `.gitpdm/config.json`
- [ ] Test operations (open, edit, commit)

After migration:
- [ ] All team members can access repo
- [ ] Locking works correctly
- [ ] Commits create proper uncompressed dirs
- [ ] (Optional) Remove `FreeCAD_Automation/`

---

**Migration Status: Sprint 4 (January 2026)**  
**Backward Compatibility: 100%**  
**Recommended Approach: Gradual team migration**

---

*For the full project history and consolidation story, see [GITCAD_HISTORY.md](GITCAD_HISTORY.md)*
