"""
Detailed GitCAD initialization debug for FreeCAD console
"""
import os
import sys

print("=" * 70)
print("DETAILED GITCAD DEBUG")
print("=" * 70)

# 1. Check paths
repo_root = r"C:\Factorem\Nerd-Sniped\GitPDM"
automation_dir = os.path.join(repo_root, "FreeCAD_Automation")

print(f"\n1. PATH CHECKS:")
print(f"   Repo root: {repo_root}")
print(f"   Automation dir: {automation_dir}")
print(f"   Automation exists: {os.path.isdir(automation_dir)}")
print(f"   Config exists: {os.path.exists(os.path.join(automation_dir, 'config.json'))}")

# 2. Test is_gitcad_initialized
print(f"\n2. TESTING is_gitcad_initialized:")
try:
    from freecad_gitpdm.gitcad import is_gitcad_initialized
    result = is_gitcad_initialized(repo_root)
    print(f"   Result: {result}")
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

# 3. Test GitCADWrapper creation
print(f"\n3. TESTING GitCADWrapper:")
try:
    from freecad_gitpdm.gitcad import GitCADWrapper
    wrapper = GitCADWrapper(repo_root)
    print(f"   ✓ Wrapper created successfully")
    print(f"   Automation dir: {wrapper.automation_dir}")
    print(f"   Has _bash_path: {hasattr(wrapper, '_bash_path')}")
    if hasattr(wrapper, '_bash_path'):
        print(f"   Bash path: {wrapper._bash_path}")
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
dw = mw.findChild(QtWidgets.QDockWidget, "GitPDMDockWidget")

if dw and dw.widget():
    panel = dw.widget()
    print(f"   Panel found: Yes")
    print(f"   Current repo: {panel._current_repo_root}")
    print(f"   Has _gitcad_lock: {hasattr(panel, '_gitcad_lock')}")
    
    if hasattr(panel, '_gitcad_lock'):
        lock_handler = panel._gitcad_lock
        print(f"   GitCAD available: {lock_handler._gitcad_available}")
        print(f"   GitCAD wrapper: {lock_handler._gitcad_wrapper}")
        
        print(f"\n5. MANUALLY CHECKING AVAILABILITY:")
        result = lock_handler.check_gitcad_availability(repo_root)
        print(f"   check_gitcad_availability result: {result}")
        print(f"   After check - available: {lock_handler._gitcad_available}")
        print(f"   After check - wrapper: {lock_handler._gitcad_wrapper}")
else:
    print(f"   Panel found: No")

print("\n" + "=" * 70)
print("DEBUG COMPLETE")
print("=" * 70)
