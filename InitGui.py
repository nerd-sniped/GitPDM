# -*- coding: utf-8 -*-
"""
GitPDM FreeCAD Addon - GUI Initialization Module
Sprint 0: Register workbench when FreeCAD GUI is available
"""

import os

import FreeCADGui


class GitPDMWorkbench(FreeCADGui.Workbench):
    """
    GitPDM Workbench class - registered with FreeCAD GUI
    """

    MenuText = "Git PDM"
    ToolTip = "Git-based Product Data Management for FreeCAD"
    Icon = os.path.join(os.path.dirname(__file__), "Resources", "icons", "GitPDM.svg")

    def Initialize(self):
        """
        Called when the workbench is first activated
        """
        from freecad_gitpdm import commands

        # Toolbar: just the two genuinely one-click, frequent desktop
        # actions. Everything else lives only in the "Git PDM" menu below --
        # this *is* the "top toolbar GitPDM dropdown" (every active
        # workbench gets a top-level menu-bar entry, distinct from its
        # toolbar), the intended home for dense/rarely-touched actions.
        self._toolbar_commands = ["GitPDM_TogglePanel", "GitPDM_SaveIntoRepo"]
        self.appendToolbar("Git PDM", self._toolbar_commands)

        self._menu_commands = [
            "GitPDM_TogglePanel",
            "GitPDM_SaveIntoRepo",
            "Separator",
            "GitPDM_Connections",
            "Separator",
            "GitPDM_GeneratePreviews",
            "GitPDM_OpenPreviewFolder",
            "GitPDM_ToggleStagePreviews",
            "Separator",
            "GitPDM_ChangeStorageMode",
            "GitPDM_DeepenHistory",
            "GitPDM_RestoreRecoveryCheckpoint",
            "GitPDM_ClearRecoveryCheckpoint",
        ]
        self.appendMenu("Git PDM", self._menu_commands)

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
            from freecad_gitpdm import commands

            # Left-docked, tabbed with Report view/Python console when
            # present (same fallback shape as commands._find_or_create_dock,
            # reused here so the two entry points never disagree on layout).
            dock = commands._find_or_create_dock()
            commands._show_dock(dock)
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
