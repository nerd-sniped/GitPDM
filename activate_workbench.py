"""
Activate GitPDM workbench and open panel
"""
import FreeCADGui as Gui

print("Activating GitPDM workbench...")
try:
    Gui.activateWorkbench("GitPDMWorkbench")
    print("✓ Workbench activated")
except Exception as e:
    print(f"✗ Failed to activate workbench: {e}")
    import traceback
    traceback.print_exc()
    print("\nAvailable workbenches:")
    print(Gui.listWorkbenches())
