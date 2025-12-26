# -*- coding: utf-8 -*-
"""
GitPDM package root
Sprint 0: Package initialization
"""

__version__ = "0.1.0"
__title__ = "GitPDM"

# Import core modules to ensure they're available
from . import core
from . import ui

__all__ = ["core", "ui"]
