# -*- coding: utf-8 -*-
"""
GitPDM Storage Mode Dialog (Phase G3)

Lets the user pick between "delta" and "lfs" storage modes for the active
repo. Switching mode is never a silent flip in either direction: choosing
a different mode than the repo currently has shows a blocking explanation
of what changes and why (R1.1), so the two forbidden states (compression 0
+ LFS, or an LFS filter on `*.FCStd` while claiming delta mode) are
unreachable by construction -- the user always sees and confirms the
consequence before it's applied.
"""

try:
    from PySide6 import QtWidgets
except ImportError:
    try:
        from PySide2 import QtWidgets
    except ImportError as e:
        raise ImportError(
            "Neither PySide6 nor PySide2 found. FreeCAD installation may be incomplete."
        ) from e

from freecad_gitpdm.core import storage_mode


_SWITCH_TO_LFS_WARNING = (
    "Switching to LFS mode will:\n\n"
    "• Restore FreeCAD's normal .FCStd compression (delta mode's "
    "compression=0 and LFS are mutually defeating -- LFS stores every "
    "version in full, so an uncompressed file multiplies storage and "
    "bandwidth for no benefit)\n"
    "• Track *.FCStd with the Git LFS filter, enabling file locking\n"
    "• Use GitHub's LFS storage/bandwidth allowance (~1 GiB free, "
    "metered past that)\n\n"
    "Existing files won't shrink or migrate until you save them again.\n\n"
    "Continue?"
)

_SWITCH_TO_DELTA_WARNING = (
    "Switching to Delta mode will:\n\n"
    "• Set FreeCAD's .FCStd compression to 0 (store) so Git can "
    "actually diff and delta-compress saves\n"
    "• Stop tracking *.FCStd with Git LFS -- file locking will no "
    "longer be available\n"
    "• Keep history free and unmetered (the recommended mode for "
    "solo work)\n\n"
    "Already-committed LFS versions of this file are unaffected; the next "
    "save will start writing plain, delta-friendly commits.\n\n"
    "Continue?"
)


class StorageModeDialog(QtWidgets.QDialog):
    """Dialog to view/change a repo's storage mode."""

    def __init__(self, current_mode: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Storage Mode")
        self.setModal(True)
        self.setMinimumWidth(420)

        self._current_mode = current_mode
        self.selected_mode = current_mode

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        intro = QtWidgets.QLabel(
            "Storage mode controls how *.FCStd files are represented in "
            "Git. Compression=0 and Git LFS are mutually defeating, so "
            "GitPDM keeps them coupled -- exactly one is ever active."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        group = QtWidgets.QButtonGroup(self)

        self._delta_radio = QtWidgets.QRadioButton("Delta (default, free)")
        self._delta_radio.setToolTip(
            storage_mode.describe_mode(storage_mode.MODE_DELTA)
        )
        group.addButton(self._delta_radio)
        layout.addWidget(self._delta_radio)

        delta_desc = QtWidgets.QLabel(
            "  " + storage_mode.describe_mode(storage_mode.MODE_DELTA)
        )
        delta_desc.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(delta_desc)

        self._lfs_radio = QtWidgets.QRadioButton("LFS (opt-in, for teams)")
        self._lfs_radio.setToolTip(storage_mode.describe_mode(storage_mode.MODE_LFS))
        group.addButton(self._lfs_radio)
        layout.addWidget(self._lfs_radio)

        lfs_desc = QtWidgets.QLabel(
            "  " + storage_mode.describe_mode(storage_mode.MODE_LFS)
        )
        lfs_desc.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(lfs_desc)

        if current_mode == storage_mode.MODE_LFS:
            self._lfs_radio.setChecked(True)
        else:
            self._delta_radio.setChecked(True)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_accept(self):
        new_mode = (
            storage_mode.MODE_LFS
            if self._lfs_radio.isChecked()
            else storage_mode.MODE_DELTA
        )

        if new_mode == self._current_mode:
            self.selected_mode = new_mode
            self.accept()
            return

        warning = (
            _SWITCH_TO_LFS_WARNING
            if new_mode == storage_mode.MODE_LFS
            else _SWITCH_TO_DELTA_WARNING
        )
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Confirm Storage Mode Change",
            warning,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if confirm != QtWidgets.QMessageBox.Yes:
            return  # leave dialog open, let user reconsider

        self.selected_mode = new_mode
        self.accept()


__all__ = ["StorageModeDialog"]
