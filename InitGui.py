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
