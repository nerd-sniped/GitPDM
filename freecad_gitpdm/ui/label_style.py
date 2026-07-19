# -*- coding: utf-8 -*-
"""
Shared label styling helpers for GitPDM's Qt panels/dialogs.

Extracted from panel.py so both the main dock widget and standalone dialogs
(e.g. connections_dialog.py) can style status labels identically without
duplicating the stylesheet strings.
"""

META_FONT_SIZE = 9
STRONG_FONT_SIZE = 11


def set_meta_label(label, color="gray", size=META_FONT_SIZE):
    label.setStyleSheet(f"color: {color}; font-size: {size}px;")


def set_strong_label(label, color="black", size=STRONG_FONT_SIZE):
    label.setStyleSheet(f"font-weight: bold; font-size: {size}px; color: {color};")
