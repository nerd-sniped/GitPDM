"""
GitPDM FreeCAD Addon - GUI Initialization Module
Requires FreeCAD 1.2.0+
"""

import FreeCADGui


class GitPDMWorkbench(FreeCADGui.Workbench):
    """
    GitPDM Workbench class - registered with FreeCAD GUI
    """

    MenuText = "Git PDM"
    ToolTip = "Git-based Product Data Management for FreeCAD"
    Icon = ""  # No icon for now

    def Initialize(self):
        """
        Called when the workbench is first activated
        """
        from freecad.gitpdm import commands

        # List of command names to register
        self._commands = ["GitPDM_TogglePanel"]

        # Create toolbar
        self.appendToolbar("Git PDM", self._commands)

        # Create menu
        self.appendMenu("Git PDM", self._commands)
        
        # Sprint 7: Auto-create and dock panel on first initialization
        # This ensures the panel is available even when switching workbenches
        from PySide6 import QtCore
        QtCore.QTimer.singleShot(500, self._ensure_panel_exists)

    def Activated(self):
        """
        Called when the workbench is activated (switched to)
        """
        from freecad.gitpdm.core import log
        from PySide6 import QtCore

        log.info("GitPDM workbench activated")

        # Defer panel opening to avoid blocking UI
        QtCore.QTimer.singleShot(100, self._open_panel_deferred)

    def _open_panel_deferred(self):
        """Open panel after brief delay to keep UI responsive."""
        try:
            import FreeCADGui
            from freecad.gitpdm.ui import panel
            from freecad.gitpdm.core.services import get_services
            from PySide6 import QtCore, QtWidgets

            mw = FreeCADGui.getMainWindow()
            dock = mw.findChild(QtWidgets.QDockWidget, "GitPDM_DockWidget")

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
            repo_browser = mw.findChild(QtWidgets.QDockWidget, "GitPDM_RepoBrowserDock")
            if repo_browser:
                if not repo_browser.isVisible():
                    repo_browser.show()
                repo_browser.raise_()
        except Exception as e:
            from freecad.gitpdm.core import log

            log.error(f"Failed to auto-open panel: {e}")
    
    def _ensure_panel_exists(self):
        """
        Ensure the GitPDM panel is created and docked on startup.
        Sprint 7: Auto-dock to right side for persistent availability.
        """
        try:
            import FreeCADGui
            from freecad.gitpdm.ui import panel
            from freecad.gitpdm.core.services import get_services
            from PySide6 import QtCore, QtWidgets

            mw = FreeCADGui.getMainWindow()
            dock = mw.findChild(QtWidgets.QDockWidget, "GitPDM_DockWidget")

            if dock is None:
                from freecad.gitpdm.core import log
                log.info("Auto-creating GitPDM dock panel on startup")
                
                dock = panel.GitPDMDockWidget(services=get_services())

                # Dock to right side, attempt to tab with Task panel
                task_panel = mw.findChild(QtWidgets.QDockWidget, "Tasks")
                mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
                
                if task_panel:
                    mw.tabifyDockWidget(task_panel, dock)
                
                # Show the panel
                dock.show()
                
                # Optional: Bring to front (comment out if you prefer Task panel in front)
                # dock.raise_()
        except Exception as e:
            from freecad.gitpdm.core import log
            log.error(f"Failed to auto-create panel on startup: {e}")

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
