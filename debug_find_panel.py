"""
Find the actual GitPDM panel widget
"""
try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets
import FreeCADGui as Gui

mw = Gui.getMainWindow()

# Find all dock widgets
print("All dock widgets:")
for child in mw.findChildren(QtWidgets.QDockWidget):
    print(f"  - {child.objectName()}: {type(child)}")
    if child.widget():
        print(f"    Widget: {type(child.widget())}")
        w = child.widget()
        if hasattr(w, 'widget'):
            inner = w.widget()
            print(f"    Inner widget: {type(inner)}")
            if hasattr(inner, '_current_repo_root'):
                print(f"    ✓ This is the GitPDM panel!")
                print(f"    Has _gitcad_lock: {hasattr(inner, '_gitcad_lock')}")
                print(f"    Current repo: {inner._current_repo_root}")
