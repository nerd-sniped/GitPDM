"""
Sprint 4: Access GitPDMDockWidget directly (Native Core Check)
"""
try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets
import FreeCADGui as Gui
from pathlib import Path

mw = Gui.getMainWindow()
dw = mw.findChild(QtWidgets.QDockWidget, "GitPDM_DockWidget")

print(f"Found: {type(dw)}")
print(f"Has _current_repo_root: {hasattr(dw, '_current_repo_root')}")
print(f"Has _gitcad_lock: {hasattr(dw, '_gitcad_lock')}")

if hasattr(dw, '_current_repo_root'):
    print(f"\nCurrent repo: {dw._current_repo_root}")
    
if hasattr(dw, '_gitcad_lock'):
    lock = dw._gitcad_lock
    print(f"GitPDM available: {lock._gitcad_available}")
    print(f"Lock manager: {lock._lock_manager}")  # Sprint 4: Now uses LockManager
    
    # Try manual check with native core
    repo = Path(r"C:\Factorem\Nerd-Sniped\GitPDM")
    print(f"\nManually checking with native core: {repo}")
    
    from freecad_gitpdm.core.config_manager import has_config
    from freecad_gitpdm.core.lock_manager import LockManager
    
    print(f"has_config: {has_config(repo)}")
    
    try:
        print(f"Creating LockManager...")
        manager = LockManager(repo)
        print(f"✓ LockManager created")
        
        # Try to get locks
        result = manager.get_locks()
        if result.ok:
            print(f"  Current locks: {len(result.value)}")
        else:
            print(f"  Lock query: {result.error}")
    except Exception as e:
        print(f"✗ Failed: {e}")
    
    print(f"\nCalling check_gitcad_availability...")
    result = lock.check_gitcad_availability(str(repo))
    print(f"Result: {result}")
    print(f"After check - available: {lock._gitcad_available}")
    print(f"After check - lock_manager: {lock._lock_manager}")
