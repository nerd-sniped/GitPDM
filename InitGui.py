# -*- coding: utf-8 -*-
"""
GitPDM FreeCAD Addon - GUI Initialization Module
Sprint 0: Register workbench when FreeCAD GUI is available
"""

import os

import FreeCAD
import FreeCADGui


class GitPDMWorkbench(FreeCADGui.Workbench):
    """
    GitPDM Workbench class - registered with FreeCAD GUI
    """

    MenuText = "Git PDM"
    ToolTip = "Git-based Product Data Management for FreeCAD"
    # Three real-environment failures (2026-07-20) mapped out what FreeCAD's
    # workbench-selector scan actually evaluates when it reads Icon here
    # (it needs Icon/MenuText/ToolTip for every *installed* addon up front,
    # before the user picks one, without running each one's full
    # Init/InitGui): (1) __file__ is never defined in the scope FreeCAD
    # execs InitGui.py in (Init.py/InitGui.py are exec'd, never imported).
    # (2) A module-level variable assigned via try/except one line above
    # the class ("_ADDON_ICON = ...") wasn't visible either, even though
    # plain `import os` / `import FreeCADGui` above it resolved fine - so
    # this scan replays plain top-level imports but not other statement
    # shapes. (3) Even a plain, unconditional `import freecad_gitpdm` at
    # module scope wasn't enough - unlike `os`/`FreeCADGui` (already-loaded
    # embedded modules), freecad_gitpdm is a real filesystem package, and
    # this scan apparently runs before the addon's own directory is added
    # to sys.path, so the import silently failed and the name was never
    # bound. Net effect: nothing that depends on *this addon's own files*
    # being importable/on-disk-relative can work here - only FreeCAD's own
    # already-loaded modules are reliably available. So this derives the
    # path from FreeCAD's own user data directory instead (matches this
    # project's documented install location, Mod/GitPDM), with a same-
    # scope try/except *inside* the class body (proven safe - MenuText/
    # ToolTip/Icon assignments already run sequentially in this same
    # class-body namespace across all three failures) falling back to ""
    # if that guess is ever wrong (non-standard install location) rather
    # than blocking registration.
    try:
        _icon_candidate = os.path.join(
            FreeCAD.getUserAppDataDir(),
            "Mod",
            "GitPDM",
            "Resources",
            "icons",
            "GitPDM.svg",
        )
        Icon = _icon_candidate if os.path.isfile(_icon_candidate) else ""
    except Exception:
        Icon = ""

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
