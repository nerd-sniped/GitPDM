# -*- coding: utf-8 -*-
"""
Branch Operations Handler Module
Sprint 4: Extracted from panel.py to manage branch operations and worktree management.
"""

import os
import sys
import glob
import subprocess

# Qt compatibility layer
try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtWidgets
    except ImportError as e:
        raise ImportError(
            "Neither PySide6 nor PySide2 found. FreeCAD installation may be incomplete."
        ) from e

from freecad_gitpdm.core import log, settings
from freecad_gitpdm.ui import dialogs


class BranchOperationsHandler:
    """
    Handles branch operations and worktree management.

    Manages:
    - Branch creation
    - Branch switching (with worktree support)
    - Branch deletion
    - Worktree creation and management
    - Open file detection for corruption prevention
    - Branch list refresh
    """

    def __init__(self, parent, git_client, job_runner):
        """
        Initialize branch operations handler.

        Args:
            parent: GitPDMDockWidget - parent panel with UI widgets and state
            git_client: GitClient - for git operations
            job_runner: JobRunner - for background operations
        """
        self._parent = parent
        self._git_client = git_client
        self._job_runner = job_runner

        # Operation state
        self._is_switching_branch = False
        self._local_branches = []
        self._branch_combo_updating = False
        self._pending_publish_new_branch = None
        self._is_loading_branches = False  # Sprint PERF-3: Track async branch loading

    # ========== Public API ==========

    def new_branch_clicked(self):
        """Handle New Branch button click - show dialog and create branch."""
        if not self._parent._current_repo_root:
            return

        if self._is_switching_branch or self._job_runner.is_busy():
            log.debug("Job running, new branch ignored")
            return

        # CRITICAL: Check for ANY open .FCStd files (not just from current repo)
        # Git operations can corrupt files in other worktrees too
        open_docs = self._get_all_open_fcstd_documents()
        lock_files = self._find_repo_lock_files()

        # Get default branch as start point
        default_upstream = self._git_client.default_upstream_ref(
            self._parent._current_repo_root, self._parent._remote_name
        )
        if not default_upstream:
            default_upstream = "HEAD"

        # Show dialog with open files information
        dialog = dialogs.NewBranchDialog(
            parent=self._parent,
            default_start_point=default_upstream,
            open_docs=open_docs,
            lock_files=lock_files,
        )
        if not dialog.exec():
            return

        branch_name = dialog.branch_name
        start_point = dialog.start_point

        if not branch_name:
            return

        # Double-check before actual branch creation (user might have opened files after dialog)
        open_docs_recheck = self._get_all_open_fcstd_documents()
        lock_files_recheck = self._find_repo_lock_files()
        if open_docs_recheck or lock_files_recheck:
            QtWidgets.QMessageBox.critical(
                self._parent,
                "Files Opened",
                "FreeCAD files were opened after the dialog. Please close ALL documents "
                "and try again to prevent corruption.",
            )
            return

        # Validate branch name
        if not self._validate_branch_name(branch_name):
            return

        # Sprint PERF-3: Create branch asynchronously
        log.info(f"Creating branch: {branch_name} from {start_point}")

        def _create_branch():
            """Background job to create branch."""
            result = self._git_client.create_branch(
                self._parent._current_repo_root, branch_name, start_point
            )
            return {"ok": result.ok, "stderr": result.stderr}

        # Store context for callback
        self._pending_publish_new_branch = branch_name

        self._job_runner.run_callable(
            "create_branch",
            _create_branch,
            on_success=lambda result: self._on_branch_created(result, branch_name),
            on_error=lambda error: self._on_branch_create_error(error, branch_name),
        )

    def _on_branch_created(self, result, branch_name):
        """Callback when branch creation completes (Sprint PERF-3)."""
        if not result.get("ok", False):
            stderr = result.get("stderr", "Unknown error")
            QtWidgets.QMessageBox.warning(
                self._parent,
                "Couldn't Create Work Version",
                f"We couldn't create the work version '{branch_name}'.\n\n"
                f"This might be because:\n"
                f"  \u2022 A version with that name already exists\n"
                f"  \u2022 The name contains invalid characters\n\n"
                f"Technical details: {stderr}",
            )
            self._pending_publish_new_branch = None
            return

        log.info(f"Branch '{branch_name}' created, now switching to it")

        # Switch to new branch (pending_publish_new_branch already set)
        self.switch_to_branch(branch_name)

    def _on_branch_create_error(self, error_msg, branch_name):
        """Callback when branch creation fails (Sprint PERF-3)."""
        log.error(f"Failed to create branch '{branch_name}': {error_msg}")
        QtWidgets.QMessageBox.warning(
            self._parent,
            "Couldn't Create Work Version",
            f"We couldn't create the work version '{branch_name}'.\n\n"
            f"Try using a different name or ask someone familiar with Git for help.\n\n"
            f"Technical details: {error_msg}",
        )
        self._pending_publish_new_branch = None

    def switch_branch_clicked(self):
        """Handle Switch button click - switch to selected branch."""
        if not self._parent._current_repo_root:
            return

        selected_idx = self._parent.branch_combo.currentIndex()
        if selected_idx < 0 or selected_idx >= len(self._local_branches):
            return

        target_branch = self._local_branches[selected_idx]
        current_branch = self._git_client.current_branch(
            self._parent._current_repo_root
        )

        if target_branch == current_branch:
            log.debug("Already on selected branch")
            return

        self.switch_to_branch(target_branch)

    def delete_branch_clicked(self):
        """Handle Delete Branch button click."""
        if not self._parent._current_repo_root:
            return

        selected_idx = self._parent.branch_combo.currentIndex()
        if selected_idx < 0 or selected_idx >= len(self._local_branches):
            return

        branch_name = self._local_branches[selected_idx]
        current_branch = self._git_client.current_branch(
            self._parent._current_repo_root
        )

        if branch_name == current_branch:
            QtWidgets.QMessageBox.warning(
                self._parent,
                "Can't Delete Current Version",
                f"You can't delete the work version you're currently using.\n\n"
                f"To delete '{branch_name}':\n"
                f"1. Switch to a different work version first\n"
                f"2. Then come back and delete this one",
            )
            return

        # Confirm deletion
        reply = QtWidgets.QMessageBox.question(
            self._parent,
            "Delete Work Version?",
            f"Are you sure you want to permanently delete '{branch_name}'?\n\n"
            f"<b>Warning:</b> This cannot be undone!\n\n"
            f"Any work you've done in this version that hasn't been shared\n"
            f"to GitHub will be lost forever.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        # Sprint PERF-3: Delete branch asynchronously
        log.info(f"Deleting branch: {branch_name}")

        def _delete_branch():
            """Background job to delete branch."""
            result = self._git_client.delete_local_branch(
                self._parent._current_repo_root, branch_name, force=False
            )
            return {
                "ok": result.ok,
                "stderr": result.stderr,
                "branch_name": branch_name,
            }

        self._job_runner.run_callable(
            "delete_branch",
            _delete_branch,
            on_success=self._on_branch_deleted,
            on_error=lambda error: self._on_branch_delete_error(error, branch_name),
        )

    def _on_branch_deleted(self, result):
        """Callback when branch deletion completes (Sprint PERF-3)."""
        branch_name = result.get("branch_name", "")

        if not result.get("ok", False):
            stderr = result.get("stderr", "")
            # Check if branch needs force delete
            if "not fully merged" in stderr.lower():
                reply = QtWidgets.QMessageBox.question(
                    self._parent,
                    "This Version Has Unshared Work",
                    f"The work version '{branch_name}' contains changes that haven't\n"
                    f"been shared to GitHub or merged with your main version.\n\n"
                    f"<b>If you delete it now, those changes will be lost forever.</b>\n\n"
                    f"Do you still want to delete it?\n\n"
                    f"(If you're not sure, click No and ask someone familiar with Git for help)",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No,
                )
                if reply == QtWidgets.QMessageBox.Yes:
                    # Retry with force
                    self._force_delete_branch(branch_name)
                return
            else:
                QtWidgets.QMessageBox.warning(
                    self._parent,
                    "Delete Branch Failed",
                    f"Failed to delete branch '{branch_name}':\n\n{stderr}",
                )
                return

        log.info(f"Deleted branch: {branch_name}")

        # Refresh branch list
        self.refresh_branch_list()

    def _on_branch_delete_error(self, error_msg, branch_name):
        """Callback when branch deletion fails (Sprint PERF-3)."""
        log.error(f"Failed to delete branch '{branch_name}': {error_msg}")
        QtWidgets.QMessageBox.warning(
            self._parent,
            "Delete Branch Failed",
            f"Failed to delete branch '{branch_name}':\n\n{error_msg}",
        )

    def _force_delete_branch(self, branch_name):
        """Force delete a branch (Sprint PERF-3: async helper)."""

        def _force_delete():
            """Background job to force delete branch."""
            result = self._git_client.delete_local_branch(
                self._parent._current_repo_root, branch_name, force=True
            )
            return {
                "ok": result.ok,
                "stderr": result.stderr,
                "branch_name": branch_name,
            }

        self._job_runner.run_callable(
            "force_delete_branch",
            _force_delete,
            on_success=self._on_force_delete_completed,
            on_error=lambda error: self._on_branch_delete_error(error, branch_name),
        )

    def _on_force_delete_completed(self, result):
        """Callback when force delete completes (Sprint PERF-3)."""
        branch_name = result.get("branch_name", "")

        if not result.get("ok", False):
            stderr = result.get("stderr", "")
            QtWidgets.QMessageBox.warning(
                self._parent,
                "Delete Branch Failed",
                f"Failed to force delete branch '{branch_name}':\n\n{stderr}",
            )
            return

        log.info(f"Force deleted branch: {branch_name}")

        # Refresh branch list
        self.refresh_branch_list()

    def worktree_help_clicked(self):
        """Show quick guidance for setting up per-branch git worktrees."""
        example_path = os.path.normpath(
            os.path.join(self._parent._current_repo_root or "..", "repo-feature")
        )
        msg = (
            "<b>What are Work Version Folders?</b>\n\n"
            "Instead of switching between work versions in the same folder \n"
            "(which can corrupt open files), you can give each work version \n"
            "its own separate folder.\n\n"
            "<b>Why use them?</b>\n"
            "  \u2022 Each version has its own folder\n"
            "  \u2022 No risk of corrupting files when switching\n"
            "  \u2022 You can have multiple versions open at once\n\n"
            "<b>How to set up:</b>\n"
            "This requires some Git knowledge. Ask a team member who knows Git \n"
            "to help you set up worktrees, or see the documentation.\n\n"
            f"<i>Git term: 'worktree' - a linked working directory for a branch</i>\n\n"
            f"<i>Example command (for Git users):</i>\n"
            f"  git worktree add {example_path} feature"
        )
        QtWidgets.QMessageBox.information(
            self._parent, "About Work Version Folders", msg
        )

    def branch_combo_changed(self, index):
        """Handle branch combo box selection change."""
        if self._branch_combo_updating:
            return
        # Just update delete button state
        self.update_branch_button_states()

    def refresh_branch_list(self):
        """Refresh the list of local branches in the combo box (Sprint PERF-3: async)."""
        if not self._parent._current_repo_root:
            self._local_branches = []
            self._parent.branch_combo.clear()
            return

        # Sprint PERF-3: Prevent multiple simultaneous refreshes
        if self._is_loading_branches:
            log.debug("Branch list already loading, skipping refresh")
            return

        self._is_loading_branches = True

        # Show loading state
        self._branch_combo_updating = True
        old_text = self._parent.branch_combo.currentText()
        self._parent.branch_combo.clear()
        self._parent.branch_combo.addItem("Loading branches…")
        self._branch_combo_updating = False

        # Sprint PERF-3: Load branches in background
        def _load_branches():
            """Background job to load branch list."""
            branches = self._git_client.list_local_branches(
                self._parent._current_repo_root
            )
            current = self._git_client.current_branch(self._parent._current_repo_root)
            return {"branches": branches, "current": current}

        self._job_runner.run_callable(
            "load_branch_list",
            _load_branches,
            on_success=self._on_branch_list_loaded,
            on_error=self._on_branch_list_load_error,
        )

    def update_branch_button_states(self):
        """Update enabled/disabled state of branch action buttons."""
        # Safety check: ensure widgets exist
        if not hasattr(self._parent, "new_branch_btn"):
            return

        repo_ok = self._parent._current_repo_root is not None
        has_branches = len(self._local_branches) > 0
        busy = (
            self._parent._fetch_pull.is_busy()
            or self._parent._commit_push.is_busy()
            or self._is_switching_branch
            or self._is_loading_branches  # Sprint PERF-3: Include branch loading
            or self._job_runner.is_busy()
        )

        log.debug(
            f"Branch button states - repo_ok: {repo_ok}, busy: {busy}, has_branches: {has_branches}"
        )

        self._parent.new_branch_btn.setEnabled(repo_ok and not busy)
        self._parent.switch_branch_btn.setEnabled(repo_ok and has_branches and not busy)

        # Can't delete current branch
        current_branch = (
            self._git_client.current_branch(self._parent._current_repo_root)
            if self._parent._current_repo_root
            else None
        )
        selected_idx = self._parent.branch_combo.currentIndex()
        selected_branch = (
            self._local_branches[selected_idx]
            if 0 <= selected_idx < len(self._local_branches)
            else None
        )
        can_delete = (
            repo_ok
            and has_branches
            and not busy
            and selected_branch
            and selected_branch != current_branch
        )
        self._parent.delete_branch_btn.setEnabled(can_delete)

    def refresh_after_branch_operation(self):
        """Refresh UI after branch operations (switch, create, etc.)."""
        if not self._parent._current_repo_root:
            return

        # Update branch name display
        branch = self._git_client.current_branch(self._parent._current_repo_root)
        self._parent.branch_label.setText(branch)

        # Refresh branch list
        self.refresh_branch_list()

        # Refresh status and upstream
        self._parent._refresh_status_views(self._parent._current_repo_root)
        self._parent._update_upstream_info(self._parent._current_repo_root)

        # Refresh repo browser
        self._parent._refresh_repo_browser_files()

    def is_busy(self):
        """Check if branch operation is in progress."""
        return self._is_switching_branch

    def switch_to_branch(self, branch_name):
        """
        Switch to the specified branch, with dirty working tree check.

        Args:
            branch_name: str - branch to switch to
        """
        if not self._parent._current_repo_root:
            return

        if self._is_switching_branch or self._job_runner.is_busy():
            log.debug("Job running, branch switch ignored")
            return

        # CRITICAL Guard: block ALL branch operations while ANY FreeCAD files are open
        open_docs = self._get_all_open_fcstd_documents()
        lock_files = self._find_repo_lock_files()
        if open_docs or lock_files:
            details_lines = []
            if open_docs:
                details_lines.append("Open documents:")
                details_lines.extend([f"  - {p}" for p in open_docs])
            if lock_files:
                details_lines.append("Lock files (close FreeCAD):")
                details_lines.extend([f"  - {p}" for p in lock_files])

            advice = (
                "CRITICAL: Close ALL FreeCAD documents before any branch operations!\n\n"
                "Git operations can corrupt .FCStd files that are currently open in FreeCAD, "
                "even if they're in a different worktree folder. This is a known limitation "
                "of how FreeCAD handles binary files.\n\n"
                "Please close ALL FreeCAD documents (File -> Close All) and try again."
            )
            QtWidgets.QMessageBox.critical(
                self._parent,
                "Close ALL Files First",
                advice + ("\n\n" + "\n".join(details_lines) if details_lines else ""),
            )
            log.warning("Branch switch blocked - open FreeCAD documents detected")
            return

        # Check for uncommitted changes
        has_changes = self._git_client.has_uncommitted_changes(
            self._parent._current_repo_root
        )

        if has_changes:
            reply = QtWidgets.QMessageBox.question(
                self._parent,
                "Uncommitted Changes",
                "You have uncommitted changes in your working tree.\n\n"
                "Switching branches may fail or overwrite your changes.\n"
                "Consider committing or stashing your changes first.\n\n"
                "Do you want to switch anyway?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                log.info("User cancelled branch switch due to uncommitted changes")
                return

        # Prefer per-branch worktree to avoid FCStd corruption
        worktree_path = self._compute_worktree_path_for_branch(branch_name)
        if worktree_path:
            create_msg = (
                "To avoid CAD file corruption, GitPDM can create a per-branch worktree "
                "folder and open it instead of switching in-place.\n\n"
                f"Worktree path:\n  {worktree_path}\n\n"
                "Proceed to create and open the worktree?"
            )
            reply = QtWidgets.QMessageBox.question(
                self._parent,
                "Use Per-Branch Worktree",
                create_msg,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes,
            )
            if reply == QtWidgets.QMessageBox.Yes:
                self._create_and_open_worktree(branch_name, worktree_path)
                return

        # Fallback: perform in-place checkout (riskier)
        self._is_switching_branch = True
        self._parent._start_busy_feedback(f"Switching to {branch_name}…")
        self.update_branch_button_states()

        log.info(f"Switching to branch: {branch_name}")

        git_cmd = self._git_client._get_git_command()
        args = [git_cmd, "-C", self._parent._current_repo_root, "switch", branch_name]

        self._job_runner.run_job(
            "switch_branch",
            args,
            callback=lambda job: self._on_switch_branch_completed(job, branch_name),
        )

    # ========== Private Implementation ==========

    def _validate_branch_name(self, name):
        """
        Validate branch name according to git rules.
        Returns True if valid, shows error and returns False otherwise.
        """
        if not name:
            QtWidgets.QMessageBox.warning(
                self._parent, "Invalid Branch Name", "Branch name cannot be empty."
            )
            return False

        if name.startswith("-"):
            QtWidgets.QMessageBox.warning(
                self._parent,
                "Invalid Branch Name",
                "Branch name cannot start with a dash.",
            )
            return False

        if " " in name:
            QtWidgets.QMessageBox.warning(
                self._parent,
                "Invalid Branch Name",
                "Branch name cannot contain spaces.",
            )
            return False

        # Check for invalid characters
        invalid_chars = ["~", "^", ":", "?", "*", "[", "\\", "..", "@{"]
        for char in invalid_chars:
            if char in name:
                QtWidgets.QMessageBox.warning(
                    self._parent,
                    "Invalid Branch Name",
                    f"Branch name cannot contain '{char}'.",
                )
                return False

        return True

    def _on_branch_list_loaded(self, result):
        """Callback when branch list loading completes (Sprint PERF-3)."""
        self._is_loading_branches = False

        branches = result.get("branches", [])
        current_branch = result.get("current", "")

        # Store branches
        self._local_branches = branches

        # Update combo box
        self._branch_combo_updating = True
        self._parent.branch_combo.clear()
        self._parent.branch_combo.addItems(self._local_branches)

        # Select current branch
        if current_branch and current_branch in self._local_branches:
            idx = self._local_branches.index(current_branch)
            self._parent.branch_combo.setCurrentIndex(idx)

        self._branch_combo_updating = False

        # Update button states
        self.update_branch_button_states()

        log.debug(f"Branch list loaded: {len(branches)} branches")

    def _on_branch_list_load_error(self, error_msg):
        """Callback when branch list loading fails (Sprint PERF-3)."""
        self._is_loading_branches = False

        log.error(f"Failed to load branch list: {error_msg}")

        # Show error in combo
        self._branch_combo_updating = True
        self._parent.branch_combo.clear()
        self._parent.branch_combo.addItem("Error loading branches")
        self._branch_combo_updating = False

        # Clear branches
        self._local_branches = []

        # Update button states
        self.update_branch_button_states()

    def _on_switch_branch_completed(self, job, branch_name):
        """Callback when branch switch completes."""
        result = job.get("result", {})
        success = result.get("success", False)
        stderr = result.get("stderr", "")

        self._is_switching_branch = False
        self._parent._stop_busy_feedback()

        if not success:
            # Check if 'switch' is not recognized and retry with checkout
            if "switch" in stderr.lower() and "not a git command" in stderr.lower():
                log.debug("'git switch' not available, retrying with checkout")
                self._switch_to_branch_with_checkout(branch_name)
                return

            QtWidgets.QMessageBox.warning(
                self._parent,
                "Switch Branch Failed",
                f"Failed to switch to branch '{branch_name}':\n\n{stderr}",
            )
            self.update_branch_button_states()
            return

        log.info(f"Switched to branch: {branch_name}")

        # Show success message for new branch creation
        self._parent._show_status_message(
            f"Switched to '{branch_name}'", is_error=False
        )
        QtCore.QTimer.singleShot(3000, self._parent._clear_status_message)

        # If this switch follows a new branch creation, publish it to origin
        if self._pending_publish_new_branch == branch_name:
            log.info(f"Publishing new branch to remote: {branch_name}")
            # Clear flag before pushing to avoid re-entrancy
            self._pending_publish_new_branch = None
            # Use explicit branch name to ensure remote branch is created
            # and set as upstream regardless of HEAD state.
            self._parent._commit_push._retry_push_with_branch_name()

        # Refresh UI
        if self._parent._current_repo_root:
            self.refresh_after_branch_operation()

    def _switch_to_branch_with_checkout(self, branch_name):
        """Fallback to git checkout if git switch is not available."""
        if not self._parent._current_repo_root:
            return

        self._is_switching_branch = True
        self._parent._start_busy_feedback(f"Switching to {branch_name}…")

        git_cmd = self._git_client._get_git_command()
        args = [git_cmd, "-C", self._parent._current_repo_root, "checkout", branch_name]

        self._job_runner.run_job(
            "checkout_branch",
            args,
            callback=lambda job: self._on_switch_branch_completed(job, branch_name),
        )

    def _compute_worktree_path_for_branch(self, branch_name: str) -> str:
        """Compute a suggested worktree path for the given branch."""
        try:
            base = os.path.basename(
                os.path.normpath(self._parent._current_repo_root or "")
            )
            parent = os.path.dirname(
                os.path.normpath(self._parent._current_repo_root or "")
            )
            if not parent:
                return ""
            candidate = f"{base}-{branch_name}"
            return os.path.join(parent, candidate)
        except Exception:
            return ""

    def _create_and_open_worktree(self, branch_name: str, worktree_path: str):
        """Create git worktree and open it as the active repo root."""
        git_cmd = self._git_client._get_git_command()
        if not git_cmd:
            QtWidgets.QMessageBox.warning(
                self._parent,
                "Git Not Found",
                "Git is not available. Install Git or GitHub Desktop and retry.",
            )
            return

        self._is_switching_branch = True
        self._parent._start_busy_feedback(f"Creating worktree for {branch_name}…")
        self.update_branch_button_states()

        args = [
            git_cmd,
            "-C",
            self._parent._current_repo_root,
            "worktree",
            "add",
            worktree_path,
            branch_name,
        ]
        self._job_runner.run_job(
            "add_worktree",
            args,
            callback=lambda job: self._on_worktree_created(
                job, worktree_path, branch_name
            ),
        )

    def _on_worktree_created(self, job, worktree_path: str, branch_name: str):
        """Handle completion of adding a worktree."""
        result = job.get("result", {})
        success = result.get("success", False)
        stderr = result.get("stderr", "")
        self._is_switching_branch = False
        self._parent._stop_busy_feedback()

        if not success:
            QtWidgets.QMessageBox.warning(
                self._parent,
                "Worktree Creation Failed",
                f"Failed to create worktree for '{branch_name}':\n\n{stderr}",
            )
            self.update_branch_button_states()
            return

        # Update repo root to new worktree and refresh
        log.info(f"Worktree created: {worktree_path}")
        settings.save_repo_path(worktree_path)
        self._parent._repo_validator.validate_repo_path(worktree_path)

        # Show success dialog with "Open Folder" button
        self._show_worktree_success_dialog(worktree_path, branch_name)

    def _show_worktree_success_dialog(self, worktree_path: str, branch_name: str):
        """Show success dialog with option to open worktree folder."""
        msg_box = QtWidgets.QMessageBox(self._parent)
        msg_box.setWindowTitle("Worktree Created Successfully")
        msg_box.setIcon(QtWidgets.QMessageBox.Information)

        msg = (
            f"✓ Worktree created for '{branch_name}'\n\n"
            f"Path: {worktree_path}\n\n"
            "⚠️ IMPORTANT: To avoid file corruption, you must now "
            "open files from this new worktree folder, not from the main repo.\n\n"
            "Click 'Open Folder' below to view the worktree directory in File Explorer."
        )
        msg_box.setText(msg)

        # Add custom buttons
        open_btn = msg_box.addButton("Open Folder", QtWidgets.QMessageBox.AcceptRole)
        close_btn = msg_box.addButton("Close", QtWidgets.QMessageBox.RejectRole)
        msg_box.setDefaultButton(open_btn)

        msg_box.exec_()

        if msg_box.clickedButton() == open_btn:
            self._open_folder_in_explorer(worktree_path)

        # Show persistent status
        self._parent._show_status_message(
            f"Opened worktree: {os.path.basename(worktree_path)}", is_error=False
        )
        QtCore.QTimer.singleShot(5000, self._parent._clear_status_message)

    def _open_folder_in_explorer(self, folder_path: str):
        """Open folder in Windows Explorer or equivalent."""
        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
            log.info(f"Opened folder in explorer: {folder_path}")
        except Exception as e:
            log.error(f"Failed to open folder: {e}")
            QtWidgets.QMessageBox.warning(
                self._parent,
                "Cannot Open Folder",
                f"Could not open folder in file explorer:\n{e}",
            )

    def _get_all_open_fcstd_documents(self):
        """
        Return list of ALL open .FCStd files in FreeCAD, regardless of location.

        This is used for worktree safety - we need to ensure NO FreeCAD files are open
        when performing any git operations, since git worktree operations can affect
        files in other worktrees indirectly.

        Returns:
            List of absolute paths to open .FCStd files
        """
        try:
            import FreeCAD

            list_docs = getattr(FreeCAD, "listDocuments", None)
            if not callable(list_docs):
                return []
        except Exception:
            return []

        open_paths = []
        try:
            for doc in list_docs().values():
                path = getattr(doc, "FileName", "") or ""
                if path and path.lower().endswith(".fcstd"):
                    try:
                        open_paths.append(os.path.abspath(os.path.normpath(path)))
                    except Exception:
                        continue
        except Exception:
            return []
        return open_paths

    def _find_repo_lock_files(self):
        """Return list of FreeCAD lock files inside the current repo."""
        if not self._parent._current_repo_root:
            return []
        pattern = os.path.join(self._parent._current_repo_root, "*.FCStd.lock")
        try:
            return glob.glob(pattern)
        except Exception:
            return []
