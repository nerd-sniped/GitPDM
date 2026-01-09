"""
GitPDM FreeCAD Addon - GUI Initialization (Compatibility Shim)
This file exists for FreeCAD addon loading compatibility.
The actual GUI initialization is in freecad/gitpdm/init_gui.py
"""

# Import and execute the workbench registration from the actual module
import sys
from pathlib import Path
import os

# Ensure the freecad package is importable
# Handle cases where __file__ might not be defined
try:
    addon_dir = Path(__file__).parent
except NameError:
    # Fallback: use current working directory or module path
    addon_dir = Path(os.getcwd())
    
if str(addon_dir) not in sys.path:
    sys.path.insert(0, str(addon_dir))

# Import the entire init_gui module to trigger workbench registration
import freecad.gitpdm.init_gui
