# -*- coding: utf-8 -*-
"""
GitPDM FreeCAD Addon - GUI Initialization Module
Sprint 0: Register workbench when FreeCAD GUI is available
"""

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
            dock = mw.findChild(
                QtWidgets.QDockWidget, "GitPDM_DockWidget"
            )
            
            if dock is None:
                dock = panel.GitPDMDockWidget(services=get_services())
                
                # Try to tab with the Task panel for better integration
                task_panel = mw.findChild(QtWidgets.QDockWidget, "Tasks")
                if task_panel:
                    mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
                    mw.tabifyDockWidget(task_panel, dock)
                else:
                    # Fallback: just add to right area
                    mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
            
            # Show and bring to front
            if not dock.isVisible():
                dock.show()
            
            # Bring GitPDM to front of its tab group
            dock.raise_()
            
            # Also bring repository browser to front if it exists
            repo_browser = mw.findChild(
                QtWidgets.QDockWidget, "GitPDM_RepoBrowserDock"
            )
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
