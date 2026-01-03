# -*- coding: utf-8 -*-
"""
GitCAD Lock Handler Module
Manages file locking UI and operations for GitCAD integration.
"""

# Qt compatibility layer
try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError as e:
        raise ImportError(
            "Neither PySide6 nor PySide2 found. FreeCAD installation may be incomplete."
        ) from e

import os
from typing import Optional, List, Dict

from freecad_gitpdm.core import log
from freecad_gitpdm.gitcad import (
    GitCADWrapper,
    is_gitcad_initialized,
    check_gitcad_status,
    get_locks,
    LockInfo,
)


class GitCADLockHandler:
    """
    Handles GitCAD file locking functionality in the UI.
    
    Manages:
    - Lock/unlock operations
    - Lock status display
    - Lock indicators in file browser
    - Showing active locks
    """

    def __init__(self, parent, git_client, job_runner):
        """
        Initialize lock handler.
        
        Args:
            parent: GitPDMDockWidget - parent panel
            git_client: GitClient - for git operations
            job_runner: JobRunner - for background operations
        """
        self._parent = parent
        self._git_client = git_client
        self._job_runner = job_runner
        
        # State
        self._gitcad_available = False
        self._gitcad_wrapper = None
        self._current_locks = {}  # Dict[str, LockInfo]
        self._current_username = None

    def check_gitcad_availability(self, repo_root: str) -> bool:
        """
        Check if GitCAD is initialized in the repository.
        
        Args:
            repo_root: Path to repository root
            
        Returns:
            bool: True if GitCAD is available
        """
        if not repo_root:
            self._gitcad_available = False
            self._gitcad_wrapper = None
            if hasattr(self._parent, '_update_gitcad_status'):
                self._parent._update_gitcad_status()
            return False
        
        try:
            is_init = is_gitcad_initialized(repo_root)
            if is_init:
                self._gitcad_wrapper = GitCADWrapper(repo_root)
                self._gitcad_available = True
                log.info("GitCAD detected and initialized")
                
                # Get current git user
                self._current_username = self._git_client.get_config_value(
                    repo_root, "user.name"
                )
                
                # Update UI
                if hasattr(self._parent, '_update_gitcad_status'):
                    self._parent._update_gitcad_status()
                
                return True
            else:
                self._gitcad_available = False
                self._gitcad_wrapper = None
                log.debug("GitCAD not initialized in this repository")
                
                # Update UI
                if hasattr(self._parent, '_update_gitcad_status'):
                    self._parent._update_gitcad_status()
                
                return False
        except Exception as e:
            log.error(f"Error checking GitCAD availability: {e}")
            self._gitcad_available = False
            self._gitcad_wrapper = None
            
            # Update UI
            if hasattr(self._parent, '_update_gitcad_status'):
                self._parent._update_gitcad_status()
            
            return False

    def refresh_lock_status(self):
        """Refresh the current lock status from git LFS."""
        if not self._gitcad_available or not self._gitcad_wrapper:
            self._current_locks = {}
            return
        
        def _get_locks():
            result = self._gitcad_wrapper.get_locks()
            if result.ok:
                return result.value
            else:
                log.warning(f"Failed to get locks: {result.error}")
                return []
        
        self._job_runner.run_callable(
            "get_locks",
            _get_locks,
            on_success=self._on_locks_refreshed,
            on_error=lambda e: log.error(f"Error getting locks: {e}"),
        )

    def _on_locks_refreshed(self, locks: List[LockInfo]):
        """Callback when lock status is refreshed."""
        # Build dict for quick lookup
        self._current_locks = {lock.path: lock for lock in locks}
        log.debug(f"Lock status refreshed: {len(locks)} locked files")
        
        # Update UI
        self._update_lock_indicators()
        
        # Update GitCAD status display in panel
        if hasattr(self._parent, '_update_gitcad_status'):
            self._parent._update_gitcad_status()

    def _update_lock_indicators(self):
        """Update lock indicators in the file browser list."""
        if not hasattr(self._parent, "repo_list"):
            return
        
        list_widget = self._parent.repo_list
        
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if not item:
                continue
            
            file_path = item.text()
            lock_info = self._current_locks.get(file_path)
            
            # Update icon and tooltip
            if lock_info:
                if lock_info.owner == self._current_username:
                    # Locked by current user
                    item.setIcon(self._get_lock_icon("locked_by_me"))
                    item.setToolTip(f"🔒 Locked by you (ID: {lock_info.lock_id})")
                else:
                    # Locked by someone else
                    item.setIcon(self._get_lock_icon("locked_by_other"))
                    item.setToolTip(
                        f"🔒 Locked by {lock_info.owner} (ID: {lock_info.lock_id})"
                    )
            else:
                # Not locked
                item.setIcon(QtGui.QIcon())  # Clear icon
                # Keep existing tooltip or clear it
                if item.toolTip().startswith("🔒"):
                    item.setToolTip("")

    def _get_lock_icon(self, icon_type: str) -> QtGui.QIcon:
        """
        Get lock icon for display.
        
        Args:
            icon_type: "locked_by_me" or "locked_by_other"
            
        Returns:
            QIcon for the lock status
        """
        # For now, use text-based icons
        # TODO: Replace with proper icon resources
        if icon_type == "locked_by_me":
            # Create a simple colored icon
            pixmap = QtGui.QPixmap(16, 16)
            pixmap.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pixmap)
            painter.setBrush(QtGui.QBrush(QtGui.QColor(100, 200, 100)))  # Green
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(2, 2, 12, 12)
            painter.end()
            return QtGui.QIcon(pixmap)
        elif icon_type == "locked_by_other":
            # Create a simple colored icon
            pixmap = QtGui.QPixmap(16, 16)
            pixmap.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pixmap)
            painter.setBrush(QtGui.QBrush(QtGui.QColor(200, 100, 100)))  # Red
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(2, 2, 12, 12)
            painter.end()
            return QtGui.QIcon(pixmap)
        else:
            return QtGui.QIcon()

    def get_file_lock_status(self, file_path: str) -> Optional[LockInfo]:
        """
        Get lock status for a specific file.
        
        Args:
            file_path: Repo-relative path to file
            
        Returns:
            LockInfo if locked, None otherwise
        """
        return self._current_locks.get(file_path)

    def is_locked_by_me(self, file_path: str) -> bool:
        """Check if file is locked by current user."""
        lock_info = self.get_file_lock_status(file_path)
        if not lock_info:
            return False
        return lock_info.owner == self._current_username

    def is_locked_by_other(self, file_path: str) -> bool:
        """Check if file is locked by another user."""
        lock_info = self.get_file_lock_status(file_path)
        if not lock_info:
            return False
        return lock_info.owner != self._current_username

    def lock_file(self, file_path: str, force: bool = False):
        """
        Lock a file using GitCAD.
        
        Args:
            file_path: Repo-relative path to .FCStd file
            force: If True, force lock (steal from other user)
        """
        if not self._gitcad_available or not self._gitcad_wrapper:
            self._show_error("GitCAD not available", 
                           "GitCAD is not initialized in this repository.")
            return
        
        def _do_lock():
            result = self._gitcad_wrapper.lock_file(file_path, force=force)
            error_msg = result.error.message if result.error else "Unknown error"
            return {"success": result.ok, "message": result.value if result.ok else error_msg}
        
        self._job_runner.run_callable(
            f"lock_{file_path}",
            _do_lock,
            on_success=lambda r: self._on_lock_complete(file_path, r),
            on_error=lambda e: self._on_lock_error(file_path, str(e)),
        )

    def _on_lock_complete(self, file_path: str, result: dict):
        """Callback when lock operation completes."""
        if result.get("success"):
            log.info(f"Locked: {file_path}")
            self._show_info("Lock Acquired", result.get("message", "File locked successfully"))
            # Refresh lock status
            self.refresh_lock_status()
        else:
            log.error(f"Lock failed: {result.get('message')}")
            self._show_error("Lock Failed", result.get("message", "Failed to lock file"))

    def _on_lock_error(self, file_path: str, error: str):
        """Callback when lock operation errors."""
        log.error(f"Lock error for {file_path}: {error}")
        self._show_error("Lock Error", f"Failed to lock file:\n{error}")

    def unlock_file(self, file_path: str, force: bool = False):
        """
        Unlock a file using GitCAD.
        
        Args:
            file_path: Repo-relative path to .FCStd file
            force: If True, force unlock (break lock from other user)
        """
        if not self._gitcad_available or not self._gitcad_wrapper:
            self._show_error("GitCAD not available", 
                           "GitCAD is not initialized in this repository.")
            return
        
        def _do_unlock():
            result = self._gitcad_wrapper.unlock_file(file_path, force=force)
            error_msg = result.error.message if result.error else "Unknown error"
            return {"success": result.ok, "message": result.value if result.ok else error_msg}
        
        self._job_runner.run_callable(
            f"unlock_{file_path}",
            _do_unlock,
            on_success=lambda r: self._on_unlock_complete(file_path, r),
            on_error=lambda e: self._on_unlock_error(file_path, str(e)),
        )

    def _on_unlock_complete(self, file_path: str, result: dict):
        """Callback when unlock operation completes."""
        if result.get("success"):
            log.info(f"Unlocked: {file_path}")
            self._show_info("Lock Released", result.get("message", "File unlocked successfully"))
            # Refresh lock status
            self.refresh_lock_status()
        else:
            log.error(f"Unlock failed: {result.get('message')}")
            self._show_error("Unlock Failed", result.get("message", "Failed to unlock file"))

    def _on_unlock_error(self, file_path: str, error: str):
        """Callback when unlock operation errors."""
        log.error(f"Unlock error for {file_path}: {error}")
        self._show_error("Unlock Error", f"Failed to unlock file:\n{error}")

    def show_locks_dialog(self):
        """Show a dialog with all currently locked files."""
        if not self._gitcad_available:
            self._show_info("GitCAD Not Available", 
                          "GitCAD is not initialized in this repository.")
            return
        
        dialog = QtWidgets.QDialog(self._parent)
        dialog.setWindowTitle("Active Locks")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(300)
        
        layout = QtWidgets.QVBoxLayout()
        dialog.setLayout(layout)
        
        # Info label
        info_label = QtWidgets.QLabel(
            f"Currently locked files in this repository.\n"
            f"Your username: {self._current_username or '(not set)'}"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Locks list
        locks_list = QtWidgets.QTreeWidget()
        locks_list.setHeaderLabels(["File", "Owner", "Lock ID"])
        locks_list.setRootIsDecorated(False)
        locks_list.setAlternatingRowColors(True)
        layout.addWidget(locks_list)
        
        # Populate locks
        if self._current_locks:
            for file_path, lock_info in sorted(self._current_locks.items()):
                item = QtWidgets.QTreeWidgetItem([
                    file_path,
                    lock_info.owner,
                    lock_info.lock_id
                ])
                
                # Highlight locks owned by current user
                if lock_info.owner == self._current_username:
                    item.setForeground(0, QtGui.QBrush(QtGui.QColor(100, 200, 100)))
                
                locks_list.addTopLevelItem(item)
        else:
            item = QtWidgets.QTreeWidgetItem(["No files currently locked", "", ""])
            item.setForeground(0, QtGui.QBrush(QtGui.QColor(150, 150, 150)))
            locks_list.addTopLevelItem(item)
        
        locks_list.resizeColumnToContents(0)
        locks_list.resizeColumnToContents(1)
        locks_list.resizeColumnToContents(2)
        
        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Close
        )
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.exec_()

    def _show_info(self, title: str, message: str):
        """Show info message box."""
        msg = QtWidgets.QMessageBox(self._parent)
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()

    def _show_error(self, title: str, message: str):
        """Show error message box."""
        msg = QtWidgets.QMessageBox(self._parent)
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()
