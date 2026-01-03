"""
Simplified debug - just check panel state
"""
from PySide6 import QtWidgets
import FreeCADGui as Gui

mw = Gui.getMainWindow()
dw = mw.findChild(QtWidgets.QDockWidget, "GitPDMDockWidget")

if dw and dw.widget():
    panel = dw.widget()
    print(f"Panel found: Yes")
    print(f"Current repo: {panel._current_repo_root}")
    
    if hasattr(panel, '_gitcad_lock'):
        lock = panel._gitcad_lock
        print(f"GitCAD handler exists: Yes")
        print(f"GitCAD available: {lock._gitcad_available}")
        print(f"GitCAD wrapper: {lock._gitcad_wrapper}")
        
        # Try manual check
        repo = r"C:\Factorem\Nerd-Sniped\GitPDM"
        print(f"\nManually checking: {repo}")
        
        # Import the check function
        from freecad_gitpdm.gitcad import is_gitcad_initialized
        print(f"is_gitcad_initialized: {is_gitcad_initialized(repo)}")
        
        # Now try the handler's method
        try:
            result = lock.check_gitcad_availability(repo)
            print(f"check_gitcad_availability returned: {result}")
            print(f"After check - available: {lock._gitcad_available}")
            print(f"After check - wrapper: {lock._gitcad_wrapper}")
        except Exception as e:
            print(f"ERROR in check_gitcad_availability: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"GitCAD handler exists: No")
else:
    print("Panel not found")
