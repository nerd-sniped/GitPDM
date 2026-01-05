"""
GitPDM Git Module
Sprint 1: Git operations
Sprint 2: Native Python hooks
"""

from . import client
from .hooks_manager import (
    HooksManager,
    install_hooks_in_repo,
    uninstall_hooks_from_repo,
)

__all__ = [
    "client",
    "HooksManager",
    "install_hooks_in_repo",
    "uninstall_hooks_from_repo",
]
