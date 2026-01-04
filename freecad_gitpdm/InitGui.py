# -*- coding: utf-8 -*-
"""
GitPDM FreeCAD Addon - GUI Initialization Module
Sprint 0: Register workbench when FreeCAD GUI is available
"""

import os
import sys
import FreeCAD

# Add the module directory to Python path so imports work
mod_path = None
for path in FreeCAD.getResourceDir().split(";"):
    test_path = os.path.join(path, "Mod", "GitPDM")
    if os.path.exists(test_path):
        mod_path = test_path
        break

# Also check user Mod directory
if mod_path is None:
    user_mod_path = os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "GitPDM")
    if os.path.exists(user_mod_path):
        mod_path = user_mod_path

if mod_path and mod_path not in sys.path:
    sys.path.insert(0, mod_path)

# Make imports work by creating a module alias
# This allows "from freecad_gitpdm.core import log" to work
# even though the directory is just "GitPDM" in the Mod folder
import types
freecad_gitpdm = types.ModuleType('freecad_gitpdm')
sys.modules['freecad_gitpdm'] = freecad_gitpdm
# Add all submodules to the package
if mod_path:
    freecad_gitpdm.__path__ = [mod_path]
    freecad_gitpdm.__file__ = os.path.join(mod_path, '__init__.py')

import FreeCADGui


class GitPDMWorkbench(FreeCADGui.Workbench):
    """
    GitPDM Workbench class - registered with FreeCAD GUI
    """

    MenuText = "Git PDM"
    ToolTip = "Git-based Product Data Management for FreeCAD"
    Icon = ""  # No icon for Sprint 0

    def Initialize(self):
        """
        Called when the workbench is first activated
        """
        from freecad_gitpdm import commands

        # List of command names to register
        self._commands = ["GitPDM_TogglePanel"]

        # Create toolbar
        self.appendToolbar("Git PDM", self._commands)

        # Create menu
        self.appendMenu("Git PDM", self._commands)

    def Activated(self):
        """
        Called when the workbench is activated (switched to)
        """
        from freecad_gitpdm.core import log

        log.info("GitPDM workbench activated")

        # Auto-show panel when workbench is activated
        try:
            from PySide6 import QtCore
        except ImportError:
            from PySide2 import QtCore

        # Defer panel opening to avoid blocking UI
        QtCore.QTimer.singleShot(100, self._open_panel_deferred)

    def _open_panel_deferred(self):
        """Open panel after brief delay to keep UI responsive."""
        try:
            import FreeCADGui
            from freecad_gitpdm.ui import panel
            from freecad_gitpdm.core.services import get_services

            try:
                from PySide6 import QtCore, QtWidgets
            except ImportError:
                from PySide2 import QtCore, QtWidgets

            mw = FreeCADGui.getMainWindow()
            dock = mw.findChild(QtWidgets.QDockWidget, "GitPDM_DockWidget")

            if dock is None:
                dock = panel.GitPDMDockWidget(services=get_services())
                
            # Always ensure it's not floating
            dock.setFloating(False)
            
            # Get current dock area (returns 0 if not docked or wrong area)
            current_area = mw.dockWidgetArea(dock)
            
            # If not in right area, move it there
            if current_area != QtCore.Qt.RightDockWidgetArea:
                # Remove from current position if docked
                if current_area != 0:
                    mw.removeDockWidget(dock)
                
                # Add to right area
                mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
                
                # Try to tab with the Task panel for better integration
                task_panel = mw.findChild(QtWidgets.QDockWidget, "Tasks")
                if task_panel:
                    mw.tabifyDockWidget(task_panel, dock)
            
            # Show and bring to front
            if not dock.isVisible():
                dock.show()

            # Bring GitPDM to front of its tab group
            dock.raise_()

            # Also bring repository browser to front if it exists
            repo_browser = mw.findChild(QtWidgets.QDockWidget, "GitPDM_RepoBrowserDock")
            if repo_browser:
                if not repo_browser.isVisible():
                    repo_browser.show()
                repo_browser.raise_()
        except Exception as e:
            from freecad_gitpdm.core import log

            log.error(f"Failed to auto-open panel: {e}")

    def Deactivated(self):
        """
        Called when switching away from this workbench
        """
        pass

    def ContextMenu(self, recipient):
        """
        Right-click context menu setup
        """
        pass

    def GetClassName(self):
        """
        Return the C++ class name for this workbench
        """
        return "Gui::PythonWorkbench"


# Register the workbench with FreeCAD
FreeCADGui.addWorkbench(GitPDMWorkbench())
