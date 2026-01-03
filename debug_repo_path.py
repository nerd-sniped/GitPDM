"""
Debug script to check what repository is loaded in GitPDM panel
Run in FreeCAD Python console
"""
import sys
import FreeCADGui as Gui

# Get the dock widget
mw = Gui.getMainWindow()
dw = mw.findChild(QtWidgets.QDockWidget, "GitPDMDockWidget")

if dw and dw.widget():
    panel = dw.widget()
    print(f"Current repo root: {panel._current_repo_root}")
    print(f"GitCAD available: {panel._gitcad_lock._gitcad_available}")
    
    # Try checking GitCAD-main explicitly
    gitcad_path = r"C:\Factorem\Nerd-Sniped\GitPDM\GitCAD-main"
    print(f"\nTrying to check GitCAD at: {gitcad_path}")
    result = panel._gitcad_lock.check_gitcad_availability(gitcad_path)
    print(f"Result: {result}")
    print(f"GitCAD available after check: {panel._gitcad_lock._gitcad_available}")
else:
    print("GitPDM panel not found or not initialized")
