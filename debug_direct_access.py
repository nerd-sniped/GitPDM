"""
Access GitPDMDockWidget directly
"""
try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets
import FreeCADGui as Gui

mw = Gui.getMainWindow()
dw = mw.findChild(QtWidgets.QDockWidget, "GitPDM_DockWidget")

print(f"Found: {type(dw)}")
print(f"Has _current_repo_root: {hasattr(dw, '_current_repo_root')}")
print(f"Has _gitcad_lock: {hasattr(dw, '_gitcad_lock')}")

if hasattr(dw, '_current_repo_root'):
    print(f"\nCurrent repo: {dw._current_repo_root}")
    
if hasattr(dw, '_gitcad_lock'):
    lock = dw._gitcad_lock
    print(f"GitCAD available: {lock._gitcad_available}")
    print(f"GitCAD wrapper: {lock._gitcad_wrapper}")
    
    # Try manual check
    repo = r"C:\Factorem\Nerd-Sniped\GitPDM"
    print(f"\nManually checking: {repo}")
    
    from freecad_gitpdm.gitcad import is_gitcad_initialized, GitCADWrapper
    print(f"is_gitcad_initialized: {is_gitcad_initialized(repo)}")
    
    try:
        print(f"Creating GitCADWrapper...")
        wrapper = GitCADWrapper(repo)
        print(f"✓ Wrapper created")
    except Exception as e:
        print(f"✗ Failed: {e}")
    
    print(f"\nCalling check_gitcad_availability...")
    result = lock.check_gitcad_availability(repo)
    print(f"Result: {result}")
    print(f"After check - available: {lock._gitcad_available}")
    print(f"After check - wrapper: {lock._gitcad_wrapper}")
