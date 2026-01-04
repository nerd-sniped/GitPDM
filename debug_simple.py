"""
Sprint 4: Simplified Debug - Panel State with Native Core
"""
from PySide6 import QtWidgets
import FreeCADGui as Gui
from pathlib import Path

mw = Gui.getMainWindow()
dw = mw.findChild(QtWidgets.QDockWidget, "GitPDMDockWidget")

if dw and dw.widget():
    panel = dw.widget()
    print(f"Panel found: Yes")
    print(f"Current repo: {panel._current_repo_root}")
    
    if hasattr(panel, '_gitcad_lock'):
        lock = panel._gitcad_lock
        print(f"GitPDM handler exists: Yes")
        print(f"GitPDM available: {lock._gitcad_available}")
        print(f"Lock manager: {lock._lock_manager}")  # Sprint 4: Now LockManager
        
        # Try manual check with native core
        repo = Path(r"C:\Factorem\Nerd-Sniped\GitPDM")
        print(f"\nManually checking with native core: {repo}")
        
        # Import the check functions
        from freecad_gitpdm.core.config_manager import has_config
        from freecad_gitpdm.core.lock_manager import LockManager
        
        print(f"has_config: {has_config(repo)}")
        
        # Now try the handler's method
        try:
            result = lock.check_gitcad_availability(str(repo))
            print(f"check_gitcad_availability returned: {result}")
            print(f"After check - available: {lock._gitcad_available}")
            print(f"After check - lock_manager: {type(lock._lock_manager)}")
        except Exception as e:
            print(f"ERROR in check_gitcad_availability: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"GitPDM handler exists: No")
else:
    print("Panel not found")
