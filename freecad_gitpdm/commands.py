# -*- coding: utf-8 -*-
"""
GitPDM Commands Module
Sprint 0: Register FreeCAD commands
"""

import FreeCAD
import FreeCADGui
from freecad_gitpdm.core import log


class GitPDMTogglePanelCommand:
    """
    Command to toggle the GitPDM dock panel visibility
    """

    def GetResources(self):
        """
        Return command resources (icon, menu text, tooltip)
        """
        return {
            "Pixmap": "",  # No icon for Sprint 0
            "MenuText": "Toggle GitPDM Panel",
            "ToolTip": "Show/hide the GitPDM dock panel",
        }

    def Activated(self):
        """
        Called when the command is executed
        """
        from freecad_gitpdm.ui import panel

        mw = FreeCADGui.getMainWindow()
        dock = mw.findChild(
            panel.QtWidgets.QDockWidget, "GitPDM_DockWidget"
        )

        if dock is None:
            # Create the dock widget if it doesn't exist
            log.info("Creating GitPDM dock panel")
            dock = panel.GitPDMDockWidget()
            mw.addDockWidget(panel.QtCore.Qt.RightDockWidgetArea, dock)
            dock.show()
        else:
            # Toggle visibility
            if dock.isVisible():
                log.info("Hiding GitPDM dock panel")
                dock.hide()
            else:
                log.info("Showing GitPDM dock panel")
                dock.show()

    def IsActive(self):
        """
        Return True if the command should be active/enabled
        """
        return True


# Register the command with FreeCAD
FreeCADGui.addCommand("GitPDM_TogglePanel", GitPDMTogglePanelCommand())
