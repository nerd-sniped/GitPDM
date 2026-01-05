# GitPDM Testing Guide

**Version 0.2.0 - FreeCAD 1.2.0+ Required**

This guide provides instructions for testing GitPDM functionality with the new FreeCAD 1.2.0+ module structure.

## Prerequisites

1. **FreeCAD 1.2.0+** (required for PySide6 support)
2. **Python 3.10+** installed and available in PATH
3. **Git** with Git LFS installed
4. **Git Bash** (Windows) or bash (Linux/macOS) for GitCAD features

## Important: Module Structure Changes

GitPDM v0.2.0+ uses the new FreeCAD addon structure:
- Module path: `freecad.gitpdm` (was `freecad_gitpdm`)
- Entry points: `__init__.py`, `init_gui.py` (was `Init.py`, `InitGui.py`)
- Requires: FreeCAD 1.2.0+, Python 3.10+, PySide6

## Test Files Available

- **`test_wrapper_quick.py`** - Python script for quick automated testing
- **`freecad/gitpdm/gitcad/test_gitcad.py`** - Comprehensive test script
- **`test_gitcad_manual.ps1`** - PowerShell script that displays all test commands

## Quick Start Testing

### Option 1: Run the Quick Test Script (Easiest)

If you have Python working in your terminal:

```powershell
cd C:\Factorem\Nerd-Sniped\GitPDM
python test_wrapper_quick.py
```

This will run all basic tests automatically and show you:
- ✓ Module imports successfully
- ✓ GitCAD is detected
- ✓ Status of all components
- ✓ List of .FCStd files found
- ✓ Bash executable location
- ⚠ Config status (expected to be missing initially)

### Option 2: Run Individual Tests Manually

Display the test guide:
```powershell
.\test_gitcad_manual.ps1
```

Then copy/paste the individual test commands shown.

## Detailed Test Scenarios

### Test 1: GitCAD Detection ✅ (Should Pass)

**What it tests:** Verifies GitCAD automation folder is detected

**Command:**
```powershell
python -c "from freecad.gitpdm.gitcad import is_gitcad_initialized; print('GitCAD Initialized:', is_gitcad_initialized(r'C:\Factorem\Nerd-Sniped\GitPDM\GitCAD-main'))"
```

**Expected output:**
```
GitCAD Initialized: True
```

**What this proves:** The wrapper can find the FreeCAD_Automation folder and key scripts.

---

### Test 2: Status Check ✅ (Should Pass with Warnings)

**What it tests:** Detailed component detection

**Command:**
```powershell
python -c "from freecad.gitpdm.gitcad import check_gitcad_status; result = check_gitcad_status(r'C:\Factorem\Nerd-Sniped\GitPDM\GitCAD-main'); status = result.value; print('Initialized:', status.is_initialized); print('Has Config:', status.has_config); print('Has FCStdTool:', status.has_fcstd_tool); print('Has InitScript:', status.has_init_script); print('Missing:', status.missing_components); print('Warnings:', status.warnings)"
```

**Expected output:**
```
Initialized: True
Has Config: False
Has FCStdTool: True
Has InitScript: True
Missing: ['config.json']
Warnings: ['GitCAD not fully configured']
```

**What this proves:** The detector correctly identifies which components are present.

---

### Test 3: Find .FCStd Files ✅ (Should Pass)

**What it tests:** File discovery functionality

**Command:**
```powershell
python -c "from freecad.gitpdm.gitcad import find_fcstd_files; files = find_fcstd_files(r'C:\Factorem\Nerd-Sniped\GitPDM\GitCAD-main'); print(f'Found {len(files)} files:'); [print(f'  - {f}') for f in files]"
```

**Expected output:**
```
Found 2 files:
  - AssemblyExample.FCStd
  - BIMExample.FCStd
```

**What this proves:** The wrapper can scan and find .FCStd files in the repo.

---

### Test 4: Bash Detection ✅ (Should Pass on Windows with Git)

**What it tests:** Platform-specific bash executable discovery

**Command:**
```powershell
python -c "from freecad.gitpdm.gitcad.wrapper import _find_bash_executable; bash = _find_bash_executable(); print(f'Bash: {bash}' if bash else 'ERROR: Bash not found')"
```

**Expected output (Windows):**
```
Bash: C:\Program Files\Git\bin\bash.exe
```

**Expected output (Linux/macOS):**
```
Bash: /bin/bash
```

**What this proves:** The wrapper can find Git Bash (required for executing GitCAD scripts).

---

### Test 5: Create Default Config ✅ (Creates File)

**What it tests:** Configuration file creation

**Command:**
```powershell
python -c "from freecad.gitpdm.gitcad import create_default_config; result = create_default_config(r'C:\Factorem\Nerd-Sniped\GitPDM\GitCAD-main', ''); config = result.value if result.ok else None; print('SUCCESS' if result.ok else f'ERROR: {result.error}'); print(f'Config created with suffix: {config.uncompressed_directory_structure.uncompressed_directory_suffix}' if config else '')"
```

**Expected output:**
```
SUCCESS
Config created with suffix: _uncompressed
```

**Verify:**
```powershell
Test-Path "C:\Factorem\Nerd-Sniped\GitPDM\GitCAD-main\FreeCAD_Automation\config.json"
# Should return: True
```

**What this proves:** The wrapper can create and write GitCAD's config.json file.

---

### Test 6: Load Configuration ✅ (After Test 5)

**What it tests:** Configuration reading and parsing

**Command:**
```powershell
python -c "from freecad.gitpdm.gitcad import load_gitcad_config; result = load_gitcad_config(r'C:\Factorem\Nerd-Sniped\GitPDM\GitCAD-main'); config = result.value; print('Python Path:', config.freecad_python_instance_path or '(empty)'); print('Require Locks:', config.require_lock_to_modify_freecad_files); print('Suffix:', config.uncompressed_directory_structure.uncompressed_directory_suffix)"
```

**Expected output:**
```
Python Path: (empty)
Require Locks: True
Suffix: _uncompressed
```

**What this proves:** The wrapper correctly reads and parses GitCAD's config format.

---

### Test 7: Get Locks ⚠️ (May Fail - Expected)

**What it tests:** Git LFS lock querying

**Command:**
```powershell
python -c "from freecad.gitpdm.gitcad import get_locks; result = get_locks(r'C:\Factorem\Nerd-Sniped\GitPDM\GitCAD-main'); locks = result.value if result.ok else []; print(f'Found {len(locks)} locks') if result.ok else print(f'Error: {result.error}')"
```

**Expected output (if not a git repo):**
```
Error: Failed to get locks: ...
```

**Expected output (if git repo with LFS):**
```
Found 0 locks
```

**What this proves:** The wrapper can query git LFS for lock information.

---

### Test 8: Create Wrapper Instance ✅ (Should Pass)

**What it tests:** Wrapper class initialization

**Command:**
```powershell
python -c "from freecad.gitpdm.gitcad import GitCADWrapper; wrapper = GitCADWrapper(r'C:\Factorem\Nerd-Sniped\GitPDM\GitCAD-main'); print('SUCCESS'); print(f'Bash: {wrapper._bash_exe}'); print(f'Config exists: {wrapper.paths.config_file.exists()}')"
```

**Expected output:**
```
SUCCESS
Bash: C:\Program Files\Git\bin\bash.exe
Config exists: True
```

**What this proves:** The wrapper can be instantiated and has access to all GitCAD components.

---

## Advanced Tests (Require Full Setup)

These tests require:
- GitCAD initialized (run `init-repo` script)
- Git repository with LFS
- FreeCAD Python path configured
- Valid .FCStd files

### Test 9: Lock a File

```python
from freecad.gitpdm.gitcad import lock_file

result = lock_file(
    r"C:\Factorem\Nerd-Sniped\GitPDM\GitCAD-main",
    "AssemblyExample.FCStd"
)
print(result.value if result.ok else result.error)
```

### Test 10: Unlock a File

```python
from freecad.gitpdm.gitcad import unlock_file

result = unlock_file(
    r"C:\Factorem\Nerd-Sniped\GitPDM\GitCAD-main",
    "AssemblyExample.FCStd"
)
print(result.value if result.ok else result.error)
```

### Test 11: Export (Decompress) a .FCStd File

```python
from freecad.gitpdm.gitcad import export_fcstd

result = export_fcstd(
    r"C:\Factorem\Nerd-Sniped\GitPDM\GitCAD-main",
    "AssemblyExample.FCStd"
)
print(result.value if result.ok else result.error)
```

**Note:** This requires FreeCAD Python path to be configured in config.json.

---

## Troubleshooting

### "Python not found"
- Install Python from python.org or Microsoft Store
- Make sure it's in your PATH
- Try `py` instead of `python` on Windows

### "Bash not found"
- Install Git for Windows (includes Git Bash)
- Standard location: `C:\Program Files\Git\bin\bash.exe`

### "Module not found"
- Make sure you're running from the GitPDM root directory
- The wrapper expects to be imported from `freecad_gitpdm.gitcad`

### "GitCAD not found"
- Verify GitCAD-main folder exists
- Check that FreeCAD_Automation folder is present
- Run Test 1 to verify detection

---

## Success Criteria

✅ **Tests 1-6 should all pass** - These verify core functionality  
⚠️ **Test 7 may fail** - Normal if GitCAD-main isn't a git repo yet  
✅ **Test 8 should pass** - Wrapper instance creation  

If Tests 1-6 and 8 pass, the wrapper is working correctly and ready for Phase 2 GUI integration!

---

## What to Test Next (Optional)

If you want to fully test the wrapper before GUI integration:

1. **Initialize GitCAD-main as a git repo:**
   ```powershell
   cd GitCAD-main
   git init
   git lfs install
   ```

2. **Run the init-repo script:**
   ```bash
   bash FreeCAD_Automation/user_scripts/init-repo
   ```

3. **Configure FreeCAD Python path in config.json**

4. **Test lock/unlock operations** (Tests 9-10)

5. **Test export/import operations** (Test 11)

However, these aren't strictly necessary - the basic wrapper functionality is proven by Tests 1-6!
