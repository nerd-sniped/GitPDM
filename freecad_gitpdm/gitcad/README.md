# GitCAD Integration Module

This module provides a Python interface to GitCAD's bash-based git automation system, enabling the GitPDM GUI to interact with GitCAD's core functionality.

## Overview

GitCAD uses bash scripts and git hooks to automate the workflow for managing FreeCAD `.FCStd` files in git. This module bridges the gap between GitPDM's Python/Qt GUI and GitCAD's bash scripts.

## Components

### `wrapper.py`
Core wrapper for executing GitCAD bash scripts from Python:
- `GitCADWrapper` - Main class for interacting with GitCAD
- `lock_file()` - Lock a .FCStd file using GitCAD's LFS-based locking
- `unlock_file()` - Unlock a .FCStd file
- `export_fcstd()` - Decompress a .FCStd file to its uncompressed directory
- `import_fcstd()` - Compress uncompressed directory back to .FCStd
- `get_locks()` - Get list of currently locked files
- `is_gitcad_initialized()` - Check if GitCAD is set up in a repository

### `config.py`
Configuration management for GitCAD's `config.json`:
- `GitCADConfig` - Dataclass representing GitCAD configuration
- `load_gitcad_config()` - Load config from `FreeCAD_Automation/config.json`
- `save_gitcad_config()` - Save config to disk
- `create_default_config()` - Create a new default configuration
- `get_uncompressed_dir_path()` - Calculate uncompressed directory path for a .FCStd file

### `detector.py`
Repository detection and validation utilities:
- `check_gitcad_status()` - Get detailed status of GitCAD setup
- `find_fcstd_files()` - Find all .FCStd files in a repository
- `get_fcstd_uncompressed_dir()` - Get uncompressed directory for a .FCStd file
- `is_fcstd_exported()` - Check if a .FCStd file has been exported

## Usage Examples

### Check if GitCAD is initialized
```python
from freecad_gitpdm.gitcad import is_gitcad_initialized

if is_gitcad_initialized("/path/to/repo"):
    print("GitCAD is set up!")
```

### Lock/Unlock files
```python
from freecad_gitpdm.gitcad import lock_file, unlock_file

result = lock_file("/path/to/repo", "mypart.FCStd")
if result.ok:
    print(f"Success: {result.value}")
else:
    print(f"Error: {result.error}")

unlock_file("/path/to/repo", "mypart.FCStd")
```

### Get lock status
```python
from freecad_gitpdm.gitcad import get_locks

result = get_locks("/path/to/repo")
if result.ok:
    locks = result.value
    for lock in locks:
        print(f"{lock.path} locked by {lock.owner}")
```

### Load configuration
```python
from freecad_gitpdm.gitcad import load_gitcad_config

result = load_gitcad_config("/path/to/repo")
if result.ok:
    config = result.value
    print(f"FreeCAD Python: {config.freecad_python_instance_path}")
    print(f"Require locks: {config.require_lock_to_modify_freecad_files}")
```

### Check repository status
```python
from freecad_gitpdm.gitcad import check_gitcad_status

result = check_gitcad_status("/path/to/repo")
if result.ok:
    status = result.value
    print(f"Initialized: {status.is_initialized}")
    print(f"Git hooks installed: {status.has_git_hooks}")
    if status.warnings:
        for warning in status.warnings:
            print(f"Warning: {warning}")
```

### Using the wrapper class
```python
from freecad_gitpdm.gitcad import GitCADWrapper

try:
    wrapper = GitCADWrapper("/path/to/repo")
    
    # Lock a file
    result = wrapper.lock_file("parts/bracket.FCStd")
    
    # Export (decompress) a file
    result = wrapper.export_fcstd("parts/bracket.FCStd")
    
    # Get all locks
    result = wrapper.get_locks()
    
except ValueError as e:
    print(f"GitCAD not found: {e}")
```

## Platform Support

The wrapper automatically detects and uses the appropriate bash executable:
- **Windows**: Searches for Git Bash in common locations
- **Linux/macOS**: Uses system bash

## Dependencies

- Python 3.7+
- Bash (Git Bash on Windows)
- Git with Git LFS (required by GitCAD)
- GitCAD installed in the repository (`FreeCAD_Automation/` directory)

## Testing

Run the test script to verify functionality:
```bash
python freecad_gitpdm/gitcad/test_gitcad.py
```

This will test:
- GitCAD detection
- Configuration loading
- Status checking
- Lock listing
- .FCStd file discovery

## Integration with GitPDM GUI

The next phase will integrate these functions into the GitPDM Qt interface:
- Lock/unlock buttons in file browser
- Visual lock status indicators
- Repository initialization wizard
- Configuration editor panel
- Export status display
