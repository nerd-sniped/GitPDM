# -*- coding: utf-8 -*-
"""
GitPDM Commands Module
Sprint 1: Register FreeCAD commands
"""

import os

import FreeCAD
import FreeCADGui
from freecad_gitpdm.core import log, settings

# Qt compatibility layer - try PySide6 first, then PySide2
try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtWidgets
    except ImportError:
        raise ImportError(
            "Neither PySide6 nor PySide2 found. FreeCAD installation may be incomplete."
        )


class GitPDMTogglePanelCommand:
    """
    Command to toggle the GitPDM dock panel visibility
    """

    def GetResources(self):
        """
        Return command resources (icon, menu text, tooltip)
        """
        return {
            "Pixmap": "",  # No icon for Sprint 1
            "MenuText": "Toggle GitPDM Panel",
            "ToolTip": "Show/hide the GitPDM dock panel",
        }

    def Activated(self):
        """
        Called when the command is executed
        """
        from freecad_gitpdm.ui import panel

        mw = FreeCADGui.getMainWindow()
        dock = mw.findChild(QtWidgets.QDockWidget, "GitPDM_DockWidget")

        if dock is None:
            # Create the dock widget if it doesn't exist
            log.info("Creating GitPDM dock panel")
            from freecad_gitpdm.core.services import get_services

            dock = panel.GitPDMDockWidget(services=get_services())
            mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
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


class GitPDMSaveIntoRepoCommand:
    """
    Save the active document into the current GitPDM repository.

    FreeCAD's native Save/Save As dialog for a never-saved document can't be
    reliably steered from Python: its starting folder comes from an in-memory
    C++ static (Gui::FileDialog's workingDirectory) that's only seeded once at
    startup, not re-read from preferences per dialog. This command sidesteps
    that entirely by showing our own Qt file dialog, pre-pointed at the repo's
    cad/ folder, and saving directly via Document.saveAs().
    """

    def GetResources(self):
        """
        Return command resources (icon, menu text, tooltip)
        """
        return {
            "Pixmap": "",
            "MenuText": "Save Into Repo",
            "ToolTip": "Save the active document into the current GitPDM repository",
        }

    def Activated(self):
        """
        Called when the command is executed
        """
        mw = FreeCADGui.getMainWindow()
        doc = FreeCAD.ActiveDocument

        if not doc:
            QtWidgets.QMessageBox.information(
                mw, "Save Into Repo", "No active document to save."
            )
            return

        repo_root = settings.load_repo_path()
        if not repo_root or not os.path.isdir(repo_root):
            QtWidgets.QMessageBox.information(
                mw,
                "Save Into Repo",
                "No GitPDM repository is configured. Select or create one in "
                "the GitPDM panel first.",
            )
            return

        current_file = doc.FileName
        if current_file:
            start_dir = os.path.dirname(current_file)
        else:
            cad_dir = os.path.join(repo_root, "cad")
            start_dir = cad_dir if os.path.isdir(cad_dir) else repo_root

        suggested_name = f"{doc.Label or doc.Name or 'Unnamed'}.FCStd"
        start_path = os.path.join(start_dir, suggested_name)

        # Force Qt's own (non-native) dialog. The native Windows dialog keeps
        # its own persisted "last folder used" that silently overrides
        # whatever directory we pass in here, the same issue we hit with
        # FreeCAD's native Save command.
        dont_use_native = getattr(
            QtWidgets.QFileDialog, "Option", QtWidgets.QFileDialog
        ).DontUseNativeDialog

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            mw,
            "Save Into Repo",
            start_path,
            "FreeCAD document (*.FCStd)",
            options=dont_use_native,
        )
        if not path:
            log.debug("Save Into Repo cancelled")
            return

        if not path.lower().endswith(".fcstd"):
            path += ".FCStd"

        try:
            doc.saveAs(path)
            log.info(f"Saved document into repo: {path}")
        except Exception as e:
            log.error(f"Save Into Repo failed: {e}")
            QtWidgets.QMessageBox.critical(mw, "Save Into Repo", f"Save failed: {e}")

    def IsActive(self):
        """
        Return True if the command should be active/enabled
        """
        return FreeCAD.ActiveDocument is not None


# Register the commands with FreeCAD
FreeCADGui.addCommand("GitPDM_TogglePanel", GitPDMTogglePanelCommand())
FreeCADGui.addCommand("GitPDM_SaveIntoRepo", GitPDMSaveIntoRepoCommand())
