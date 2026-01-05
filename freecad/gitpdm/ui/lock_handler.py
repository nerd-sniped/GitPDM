"""
File Lock Handler Module
Manages file locking UI and operations for GitPDM.

Sprint 6: Renamed from GitPDM_lock.py, standardized naming.
"""

# Qt compatibility layer
try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError as e:
        raise ImportError(
            "PySide6 not found. FreeCAD installation may be incomplete."
        ) from e

import os
from typing import Optional, List, Dict
from pathlib import Path

from freecad.gitpdm.core import log
from freecad.gitpdm.core.lock_manager import LockManager, LockInfo
from freecad.gitpdm.core.config_manager import has_config


class LockHandler:
    """
    Handles file locking functionality in the UI.
    
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
        self._available = False
        self._lock_manager = None
        self._current_locks = {}  # Dict[str, LockInfo]
        self._current_username = None

    def check_availability(self, repo_root: str) -> bool:
        """
        Check if GitPDM is initialized in the repository.
        
        Sprint 6: Renamed from check_availability.
        
        Args:
            repo_root: Path to repository root
            
        Returns:
            bool: True if GitPDM is available
        """
        if not repo_root:
            self._available = False
            self._lock_manager = None
            if hasattr(self._parent, '_update_status'):
                self._parent._update_status()
            return False
        
        try:
            is_init = has_config(Path(repo_root))
            if is_init:
                # Initialize native LockManager (Sprint 4)
                self._lock_manager = LockManager(Path(repo_root))
                self._available = True
                log.info("GitPDM/GitPDM detected and initialized (native core)")
                
                # Get current git user (must read from repository config, not global)
                self._current_username = self._git_client.get_config(
                    repo_root, "user.name", local=False
                )
                log.info(f"Current git user.name: '{self._current_username}'")
                
                # Refresh lock status immediately (async, non-blocking)
                self.refresh_lock_status()
                
                # Update UI
                if hasattr(self._parent, '_update_status'):
                    self._parent._update_status()
                
                return True
            else:
                self._available = False
                self._lock_manager = None
                log.debug("GitPDM/GitPDM not initialized in this repository")
                
                # Update UI
                if hasattr(self._parent, '_update_status'):
                    self._parent._update_status()
                
                return False
        except Exception as e:
            log.error(f"Error checking GitPDM/GitPDM availability: {e}")
            self._available = False
            self._lock_manager = None
            
            # Update UI
            if hasattr(self._parent, '_update_status'):
                self._parent._update_status()
            
            return False

    def refresh_lock_status(self):
        """Refresh the current lock status from git LFS."""
        if not self._available or not self._lock_manager:
            self._current_locks = {}
            return
        
        def _get_locks():
            result = self._lock_manager.get_locks()
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
        # Build dict for quick lookup (use fcstd_path from LockInfo)
        self._current_locks = {lock.fcstd_path: lock for lock in locks}
        
        # Direct console output for debugging
        try:
            import FreeCAD
            FreeCAD.Console.PrintError(f"[GitPDM DEBUG] Lock refresh complete: {len(locks)} locks\n")
            if locks:
                for fcstd_path, lock in self._current_locks.items():
                    FreeCAD.Console.PrintError(f"[GitPDM DEBUG]   '{fcstd_path}' locked by {lock.owner}\n")
            else:
                FreeCAD.Console.PrintError(f"[GitPDM DEBUG] No locks in repository!\n")
        except:
            pass
        
        log.info(f"Lock status refreshed: {len(locks)} locked files")
        if locks:
            for fcstd_path, lock in self._current_locks.items():
                log.info(f"  Cached lock: '{fcstd_path}' locked by {lock.owner} (lockfile: {lock.lockfile_path})")
        else:
            log.warning("No locks found in repository")
        
        # Update UI
        self._update_lock_indicators()
        
        # Update GitPDM status display in panel
        if hasattr(self._parent, '_update_status'):
            self._parent._update_status()
        
        # Update UI
        self._update_lock_indicators()
        
        # Update GitPDM status display in panel
        if hasattr(self._parent, '_update_status'):
            self._parent._update_status()

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
        result = self._current_locks.get(file_path)
        
        # Direct console output for debugging
        try:
            import FreeCAD
            FreeCAD.Console.PrintError(f"[GitPDM DEBUG] Lock query for '{file_path}': {'FOUND' if result else 'NOT FOUND'}\n")
            if result is None and self._current_locks:
                FreeCAD.Console.PrintError(f"[GitPDM DEBUG] Available keys: {list(self._current_locks.keys())}\n")
        except:
            pass
        
        log.debug(f"Lock status query for '{file_path}': {result}")
        if result is None and self._current_locks:
            log.debug(f"Available keys: {list(self._current_locks.keys())}")
        return result

    def is_locked_by_me(self, file_path: str) -> bool:
        """Check if file is locked by current user."""
        lock_info = self.get_file_lock_status(file_path)
        if not lock_info:
            return False
        is_mine = lock_info.owner == self._current_username
        
        # Direct console output for debugging
        try:
            import FreeCAD
            FreeCAD.Console.PrintError(f"[GitPDM DEBUG] Ownership check: lock.owner='{lock_info.owner}' vs current_user='{self._current_username}' -> {is_mine}\n")
        except:
            pass
        
        log.debug(f"Lock ownership check: '{file_path}' locked by '{lock_info.owner}' vs current user '{self._current_username}' -> {is_mine}")
        return is_mine

    def is_locked_by_other(self, file_path: str) -> bool:
        """Check if file is locked by another user."""
        lock_info = self.get_file_lock_status(file_path)
        if not lock_info:
            return False
        return lock_info.owner != self._current_username

    def lock_file(self, file_path: str, force: bool = False):
        """
        Lock a file using native LockManager.
        
        Args:
            file_path: Repo-relative path to .FCStd file
            force: If True, force lock (steal from other user)
        """
        if not self._available or not self._lock_manager:
            self._show_error("GitPDM not available", 
                           "GitPDM/GitPDM is not initialized in this repository.")
            return
        
        def _do_lock():
            result = self._lock_manager.lock_file(file_path, force=force)
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
        Unlock a file using native LockManager.
        
        Args:
            file_path: Repo-relative path to .FCStd file
            force: If True, force unlock (break lock from other user)
        """
        if not self._available or not self._lock_manager:
            self._show_error("GitPDM not available", 
                           "GitPDM/GitPDM is not initialized in this repository.")
            return
        
        def _do_unlock():
            result = self._lock_manager.unlock_file(file_path, force=force)
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

    def lock_files_bulk(self, file_paths: List[str], force: bool = False):
        """
        Lock multiple files in bulk.
        
        Args:
            file_paths: List of repo-relative paths to .FCStd files
            force: If True, force lock (steal from other users)
        """
        if not self._available or not self._lock_manager:
            self._show_error("GitPDM not available", 
                           "GitPDM/GitPDM is not initialized in this repository.")
            return
        
        total = len(file_paths)
        log.info(f"Bulk lock: {total} files")
        
        def _do_bulk_lock():
            results = []
            for file_path in file_paths:
                result = self._lock_manager.lock_file(file_path, force=force)
                results.append({
                    "file": file_path,
                    "success": result.ok,
                    "message": result.value if result.ok else (result.error.message if result.error else "Unknown error")
                })
            return results
        
        self._job_runner.run_callable(
            "bulk_lock",
            _do_bulk_lock,
            on_success=lambda r: self._on_bulk_lock_complete(r, total),
            on_error=lambda e: self._show_error("Bulk Lock Error", f"Failed to lock files:\n{str(e)}"),
        )

    def _on_bulk_lock_complete(self, results: List[dict], total: int):
        """Callback when bulk lock operation completes."""
        successes = [r for r in results if r["success"]]
        failures = [r for r in results if not r["success"]]
        
        log.info(f"Bulk lock complete: {len(successes)}/{total} succeeded")
        
        if failures:
            error_summary = "\n".join([f"• {r['file']}: {r['message']}" for r in failures[:5]])
            if len(failures) > 5:
                error_summary += f"\n...and {len(failures) - 5} more"
            
            self._show_error(
                "Bulk Lock Partially Failed",
                f"Locked {len(successes)} of {total} files.\n\n"
                f"Failed files:\n{error_summary}"
            )
        else:
            self._show_info(
                "Bulk Lock Complete",
                f"Successfully locked {total} file(s)"
            )
        
        # Refresh lock status
        self.refresh_lock_status()

    def unlock_files_bulk(self, file_paths: List[str], force: bool = False):
        """
        Unlock multiple files in bulk.
        
        Args:
            file_paths: List of repo-relative paths to .FCStd files
            force: If True, force unlock (break locks from other users)
        """
        if not self._available or not self._lock_manager:
            self._show_error("GitPDM not available", 
                           "GitPDM/GitPDM is not initialized in this repository.")
            return
        
        total = len(file_paths)
        log.info(f"Bulk unlock: {total} files")
        
        def _do_bulk_unlock():
            results = []
            for file_path in file_paths:
                result = self._lock_manager.unlock_file(file_path, force=force)
                results.append({
                    "file": file_path,
                    "success": result.ok,
                    "message": result.value if result.ok else (result.error.message if result.error else "Unknown error")
                })
            return results
        
        self._job_runner.run_callable(
            "bulk_unlock",
            _do_bulk_unlock,
            on_success=lambda r: self._on_bulk_unlock_complete(r, total),
            on_error=lambda e: self._show_error("Bulk Unlock Error", f"Failed to unlock files:\n{str(e)}"),
        )

    def _on_bulk_unlock_complete(self, results: List[dict], total: int):
        """Callback when bulk unlock operation completes."""
        successes = [r for r in results if r["success"]]
        failures = [r for r in results if not r["success"]]
        
        log.info(f"Bulk unlock complete: {len(successes)}/{total} succeeded")
        
        if failures:
            error_summary = "\n".join([f"• {r['file']}: {r['message']}" for r in failures[:5]])
            if len(failures) > 5:
                error_summary += f"\n...and {len(failures) - 5} more"
            
            self._show_error(
                "Bulk Unlock Partially Failed",
                f"Unlocked {len(successes)} of {total} files.\n\n"
                f"Failed files:\n{error_summary}"
            )
        else:
            self._show_info(
                "Bulk Unlock Complete",
                f"Successfully unlocked {total} file(s)"
            )
        
        # Refresh lock status
        self.refresh_lock_status()

    def show_locks_dialog(self):
        """Show a dialog with all currently locked files."""
        if not self._available:
            self._show_info("GitPDM Not Available", 
                          "GitPDM is not initialized in this repository.")
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


