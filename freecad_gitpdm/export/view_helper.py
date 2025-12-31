# -*- coding: utf-8 -*-
"""
FreeCAD view and document helper functions for GitPDM.

Utilities for accessing FreeCAD documents and views safely,
handling various FreeCAD API versions.
"""

from typing import Any, Tuple


def doc_and_view() -> Tuple[Any, Any]:
    """
    Get active FreeCAD document and view.

    Returns:
        Tuple of (document, view). Either may be None if unavailable.
    """
    try:
        import FreeCAD, FreeCADGui

        doc = FreeCAD.ActiveDocument
        view = None
        try:
            view = FreeCADGui.ActiveDocument.ActiveView
        except Exception:
            try:
                view = FreeCADGui.ActiveDocument.ActiveView
            except Exception:
                view = None
        return doc, view
    except Exception:
        return None, None
