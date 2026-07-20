# -*- coding: utf-8 -*-
"""
GitPDM Commands Module
Sprint 1: Register FreeCAD commands

Extended for the bottom-dock UI simplification pass: most of these commands
are thin entry points from the "Git PDM" menu-bar dropdown into logic that
already lives on the panel/handlers -- no new business logic here, just
find-or-create-then-delegate, following GitPDMTogglePanelCommand's original
pattern.
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


def _find_or_create_dock():
    """Find the GitPDM dock widget, creating (but not showing) it if needed.

    Docks in the left dock area, tabbed with Report view/Python console when
    either is present -- user-identified as the best default spot (2026-07-19
    screenshot: bottom-left corner of the left dock, tabbed alongside those
    two, using the least screen space) after living at the bottom since the
    original bottom-dock UI simplification pass. If neither Report view nor
    Python console is present yet (e.g. a fresh install with both hidden),
    the dock still lands in the left area on its own -- typically as its own
    split below Tree view -- rather than falling back to the old bottom
    placement, so the default stays consistent either way.
    """
    from freecad_gitpdm.ui import panel

    mw = FreeCADGui.getMainWindow()
    dock = mw.findChild(QtWidgets.QDockWidget, "GitPDM_DockWidget")

    if dock is None:
        log.info("Creating GitPDM dock panel")
        from freecad_gitpdm.core.services import get_services

        dock = panel.GitPDMDockWidget(services=get_services())

        tab_target = None
        for name in ["Report view", "Python console"]:
            tab_target = mw.findChild(QtWidgets.QDockWidget, name)
            if tab_target:
                break

        mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)
        if tab_target:
            mw.tabifyDockWidget(tab_target, dock)

    return dock


def _show_dock(dock):
    """Show and raise the dock so a menu action's result is always visible,
    even when the bottom panel's tab wasn't already focused."""
    if not dock.isVisible():
        dock.show()
    dock.raise_()


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
        mw = FreeCADGui.getMainWindow()
        dock = mw.findChild(QtWidgets.QDockWidget, "GitPDM_DockWidget")

        if dock is None:
            dock = _find_or_create_dock()
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


class GitPDMConnectionsCommand:
    """Open the GitHub/other-host connections dialog (moved off the panel
    into the GitPDM menu since credentials are touched rarely)."""

    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Connections…",
            "ToolTip": "Connect or manage GitHub and other Git host accounts",
        }

    def Activated(self):
        dock = _find_or_create_dock()
        _show_dock(dock)
        dock.open_connections_dialog()

    def IsActive(self):
        return True


class GitPDMGeneratePreviewsCommand:
    """Run the deterministic camera-angle preview export (feeds the
    GitHub-facing docs gallery manifest) for the active document."""

    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Generate Previews",
            "ToolTip": "Export a deterministic preview PNG + manifest for the active document",
        }

    def Activated(self):
        dock = _find_or_create_dock()
        _show_dock(dock)
        dock._on_generate_previews_clicked()

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None


class GitPDMOpenPreviewFolderCommand:
    """Open the folder containing the most recently generated previews."""

    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Open Preview Folder",
            "ToolTip": "Open the folder containing the most recently generated previews",
        }

    def Activated(self):
        dock = _find_or_create_dock()
        dock._on_open_preview_folder_clicked()

    def IsActive(self):
        return bool(settings.load_last_preview_dir())


class GitPDMToggleStagePreviewsCommand:
    """Toggle "stage preview files after export" on/off from the menu.

    Not a checkable QAction (FreeCAD's GetResources doesn't reliably support
    that across versions without more Qt-level wiring than is worth the risk
    here) -- it just flips the setting and reports the new state via a
    status message. The real checkbox on the panel (kept, just hidden along
    with the rest of the Previews sub-group) remains the source of truth and
    still shows a live checked/unchecked state if ever surfaced.
    """

    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Toggle Stage Previews After Export",
            "ToolTip": "When generating previews, also 'git add' the output files",
        }

    def Activated(self):
        dock = _find_or_create_dock()
        new_state = not dock.stage_previews_checkbox.isChecked()
        # Setting the real checkbox also persists the setting (its own
        # stateChanged handler calls settings.save_stage_previews) -- that's
        # the source of truth.
        dock.stage_previews_checkbox.setChecked(new_state)
        log.info(f"Stage previews after export: {'on' if new_state else 'off'}")

    def IsActive(self):
        return True


class GitPDMDeepenHistoryCommand:
    """Fetch older history into a shallow clone."""

    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Deepen History (Shallow Clone)",
            "ToolTip": "Fetch older history so log/diff/blame views aren't truncated",
        }

    def Activated(self):
        dock = _find_or_create_dock()
        _show_dock(dock)
        dock._on_deepen_clicked()

    def IsActive(self):
        return bool(settings.load_repo_path())


class GitPDMClearRecoveryCheckpointCommand:
    """Manually clear the continuous-checkpointing recovery branch (G6)."""

    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Clear Recovery Checkpoint",
            "ToolTip": "Delete the gitpdm/recovery auto-checkpoint branch, if any",
        }

    def Activated(self):
        dock = _find_or_create_dock()
        _show_dock(dock)
        dock._clear_recovery_checkpoint_clicked()

    def IsActive(self):
        return bool(settings.load_repo_path())


class GitPDMRestoreRecoveryCheckpointCommand:
    """Manually check for and restore a checkpoint from the recovery branch
    on demand (G6 follow-up) -- for when the automatic restore-on-start
    offer didn't catch it (e.g. a document was already open when the repo
    activated), a user needs a way to ask for recovery explicitly rather
    than being stuck after losing unsaved work to a crash/force-quit."""

    def GetResources(self):
        return {
            "Pixmap": "",
            "MenuText": "Restore Recovery Checkpoint…",
            "ToolTip": (
                "Check for a gitpdm/recovery checkpoint newer than your last "
                "commit and restore it into your working files"
            ),
        }

    def Activated(self):
        dock = _find_or_create_dock()
        _show_dock(dock)
        dock._restore_recovery_checkpoint_clicked()

    def IsActive(self):
        return bool(settings.load_repo_path())


# Register the commands with FreeCAD
FreeCADGui.addCommand("GitPDM_TogglePanel", GitPDMTogglePanelCommand())
FreeCADGui.addCommand("GitPDM_SaveIntoRepo", GitPDMSaveIntoRepoCommand())
FreeCADGui.addCommand("GitPDM_Connections", GitPDMConnectionsCommand())
FreeCADGui.addCommand("GitPDM_GeneratePreviews", GitPDMGeneratePreviewsCommand())
FreeCADGui.addCommand("GitPDM_OpenPreviewFolder", GitPDMOpenPreviewFolderCommand())
FreeCADGui.addCommand("GitPDM_ToggleStagePreviews", GitPDMToggleStagePreviewsCommand())
FreeCADGui.addCommand("GitPDM_DeepenHistory", GitPDMDeepenHistoryCommand())
FreeCADGui.addCommand(
    "GitPDM_ClearRecoveryCheckpoint", GitPDMClearRecoveryCheckpointCommand()
)
FreeCADGui.addCommand(
    "GitPDM_RestoreRecoveryCheckpoint", GitPDMRestoreRecoveryCheckpointCommand()
)
