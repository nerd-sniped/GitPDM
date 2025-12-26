# -*- coding: utf-8 -*-
"""
GitPDM package root
Sprint 1: Package initialization
"""

__version__ = "0.1.0"
__title__ = "GitPDM"

# Import core modules to ensure they're available
from . import core

# UI is imported only when needed (lazy load for FreeCAD compatibility)
__all__ = ["core"]
