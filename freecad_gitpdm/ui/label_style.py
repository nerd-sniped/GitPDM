# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
Shared label styling helpers for GitPDM's Qt panels/dialogs.

Extracted from panel.py so both the main dock widget and standalone dialogs
(e.g. connections_dialog.py) can style status labels identically without
duplicating the stylesheet strings.
"""

# FreeCAD's own Qt compatibility shim -- re-exports whichever binding
# (PySide2/PySide6/...) the running FreeCAD was built against, so this
# code doesn't need updating on the next Qt major-version bump.
from PySide import QtCore, QtGui, QtWidgets

META_FONT_SIZE = 9
STRONG_FONT_SIZE = 11

# Identity accent used for the repo name -- distinct from the semantic
# status colors (green/orange/red/gray/#4db6ac used elsewhere for
# clean/dirty/error/neutral/synced state) so the name never reads as a
# status signal, and legible against both light and dark FreeCAD themes
# (unlike the plain black it replaced).
REPO_NAME_ACCENT = "#4aa8ff"


def set_meta_label(label, color="gray", size=META_FONT_SIZE):
    label.setStyleSheet(f"color: {color}; font-size: {size}px;")


def set_strong_label(label, color="black", size=STRONG_FONT_SIZE):
    label.setStyleSheet(f"font-weight: bold; font-size: {size}px; color: {color};")


class ElidedLabel(QtWidgets.QLabel):
    """A single-line QLabel that elides its text with '...' to fit whatever
    width it's given, instead of wrapping (which eats vertical space) or
    overflowing. The untruncated text is always available as a tooltip."""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = ""
        self.setWordWrap(False)
        self.setText(text)

    def setText(self, text):
        self._full_text = text or ""
        self.setToolTip(self._full_text)
        self._apply_elided_text()

    def text(self):
        return self._full_text

    def _apply_elided_text(self):
        width = self.width()
        if width <= 0:
            # Not laid out yet -- show the full text rather than nothing;
            # the first resizeEvent will re-elide once real geometry lands.
            super().setText(self._full_text)
            return
        metrics = QtGui.QFontMetrics(self.font())
        elided = metrics.elidedText(self._full_text, QtCore.Qt.ElideRight, width)
        super().setText(elided)

    def resizeEvent(self, event):
        self._apply_elided_text()
        super().resizeEvent(event)
