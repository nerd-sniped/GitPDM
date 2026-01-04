"""
Sprint 4: Detailed GitPDM Initialization Debug (Native Core)
"""
import os
import sys
from pathlib import Path

print("=" * 70)
print("DETAILED GITPDM DEBUG (NATIVE CORE - SPRINT 4)")
print("=" * 70)

# 1. Check paths
repo_root = Path(r"C:\Factorem\Nerd-Sniped\GitPDM")
automation_dir = repo_root / "FreeCAD_Automation"
config_file = automation_dir / "config.json"

print(f"\n1. PATH CHECKS:")
print(f"   Repo root: {repo_root}")
print(f"   Automation dir: {automation_dir}")
print(f"   Automation exists: {automation_dir.is_dir()}")
print(f"   Config exists: {config_file.exists()}")

# 2. Test has_config (simplified initialization check)
print(f"\n2. TESTING has_config:")
try:
    from freecad_gitpdm.core.config_manager import has_config
    result = has_config(repo_root)
    print(f"   Result: {result}")
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

# 3. Test native core modules
print(f"\n3. TESTING NATIVE CORE MODULES:")
try:
    from freecad_gitpdm.core.config_manager import load_config
    from freecad_gitpdm.core.lock_manager import LockManager
    
    config = load_config(repo_root)
    print(f"   ✓ Config loaded successfully")
    print(f"   Uncompressed suffix: {config.uncompressed_suffix}")
    print(f"   Require lock: {config.require_lock}")
    
    manager = LockManager(repo_root)
    print(f"   ✓ LockManager created successfully")
    print(f"   Repo root: {manager.repo_root}")
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

# 4. Check if panel is loaded and its state
print(f"\n4. CHECKING GITPDM PANEL STATE:")
try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets
    
import FreeCADGui as Gui
mw = Gui.getMainWindow()
dw = mw.findChild(QtWidgets.QDockWidget, "GitPDM_DockWidget")

if dw:
    print(f"   Panel found: Yes")
    if hasattr(dw, '_gitcad_lock'):
        lock = dw._gitcad_lock
        print(f"   GitPDM handler: Yes")
        print(f"   Available: {lock._gitcad_available}")
        print(f"   Lock manager type: {type(lock._lock_manager)}")
    else:
        print(f"   GitPDM handler: No")
else:
    print(f"   Panel found: No")

print("\n" + "=" * 70)
print("DEBUG COMPLETE")
print("=" * 70)
