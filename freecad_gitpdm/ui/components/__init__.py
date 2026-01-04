# -*- coding: utf-8 -*-
"""
UI Components Package
Sprint 5 Phase 1: Modular UI components for GitPDM panel

This package contains reusable UI widgets that make up the GitPDM panel.
Each component is focused, testable, and maintainable (<500 lines).
"""

from .base_widget import BaseWidget
from .document_observer import DocumentObserver
from .status_widget import StatusWidget
from .repository_widget import RepositoryWidget
from .changes_widget import ChangesWidget

__all__ = [
    "BaseWidget",
    "DocumentObserver",
    "StatusWidget",
    "RepositoryWidget",
    "ChangesWidget",
]
