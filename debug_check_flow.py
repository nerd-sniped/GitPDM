"""
Sprint 4: Test the full check_gitcad_availability flow (Native Core)
"""
try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets
import FreeCADGui as Gui
from pathlib import Path

mw = Gui.getMainWindow()
dw = mw.findChild(QtWidgets.QDockWidget, "GitPDM_DockWidget")

if dw and dw.widget():
    scroll_area = dw.widget()
    panel = scroll_area.widget() if hasattr(scroll_area, 'widget') else scroll_area
    print(f"Panel found: Yes")
    print(f"Panel type: {type(panel)}")
    print(f"Current repo: {panel._current_repo_root if hasattr(panel, '_current_repo_root') else 'N/A'}")
    
    if hasattr(panel, '_gitcad_lock'):
        lock = panel._gitcad_lock
        repo = Path(r"C:\Factorem\Nerd-Sniped\GitPDM")
        
        print(f"\nTesting native core flow...")
        
        # Step through using native core modules
        from freecad.gitpdm.core.config_manager import has_config
        from freecad.gitpdm.core.lock_manager import LockManager
        
        print(f"1. has_config: {has_config(repo)}")
        
        try:
            print(f"2. Creating LockManager...")
            manager = LockManager(repo)
            print(f"   ✓ LockManager created")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
        
        try:
            print(f"3. Getting git user.name...")
            username = lock._git_client.get_config_value(str(repo), "user.name")
            print(f"   Username: {username}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n4. Calling lock.check_gitcad_availability...")
        result = lock.check_gitcad_availability(str(repo))
        print(f"   Result: {result}")
        print(f"   Available: {lock._gitcad_available}")
        print(f"   Lock manager: {type(lock._lock_manager)}")
    else:
        print("GitPDM lock handler not found")
else:
    print("Panel not found")
