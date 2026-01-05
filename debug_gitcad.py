"""
Sprint 4: GitPDM Initialization Debug (Native Core)
Run this line by line in the FreeCAD Python console.
"""
import sys
from pathlib import Path
print("Python version:", sys.version)

# Step 1: Check imports (now using native core)
print("\n=== Testing imports ===")
try:
    from freecad.gitpdm.core.config_manager import has_config, load_config
    from freecad.gitpdm.core.lock_manager import LockManager
    from freecad.gitpdm.core.fcstd_tool import export_fcstd, import_fcstd
    print("✓ Native core imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()

# Step 2: Check if GitPDM/GitCAD directory exists
print("\n=== Checking directories ===")
import os
repo_root = Path(r"C:\Factorem\Nerd-Sniped\GitPDM")
automation_dir = repo_root / "FreeCAD_Automation"
config_file = automation_dir / "config.json"

print(f"Repo root: {repo_root}")
print(f"Automation dir exists: {automation_dir.is_dir()}")
print(f"Config file exists: {config_file.exists()}")

# Step 3: Test has_config (simplified check)
print("\n=== Testing has_config ===")
try:
    result = has_config(repo_root)
    print(f"has_config result: {result}")
except Exception as e:
    print(f"✗ has_config failed: {e}")
    import traceback
    traceback.print_exc()

# Step 4: Load configuration (native core)
print("\n=== Testing load_config ===")
try:
    config = load_config(repo_root)
    print(f"✓ Config loaded successfully")
    print(f"  Uncompressed suffix: {config.uncompressed_suffix}")
    print(f"  Subdirectory mode: {config.subdirectory_mode}")
    print(f"  Require lock: {config.require_lock}")
except Exception as e:
    print(f"✗ load_config failed: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Create LockManager (native core)
print("\n=== Testing LockManager ===")
try:
    manager = LockManager(repo_root)
    print(f"✓ LockManager created successfully")
    print(f"  Repo root: {manager.repo_root}")
except Exception as e:
    print(f"✗ LockManager creation failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Debug complete ===")
