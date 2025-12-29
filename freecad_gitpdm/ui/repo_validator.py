# -*- coding: utf-8 -*-
"""
Repository Validation Handler Module
Sprint 4: Extracted from panel.py to manage repository validation and setup operations.
"""

import os

# Qt compatibility layer
try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtWidgets
    except ImportError as e:
        raise ImportError(
            "Neither PySide6 nor PySide2 found. "
            "FreeCAD installation may be incomplete."
        ) from e

from freecad_gitpdm.core import log, settings


class RepoValidationHandler:
    """
    Handles repository validation, creation, and setup operations.
    
    Manages:
    - Repository path validation
    - Repository initialization (git init)
    - Remote connection setup
    - Repository refresh operations
    - Working directory configuration
    - Branch and status fetching
    """
    
    def __init__(self, parent, git_client):
        """
        Initialize repo validation handler.
        
        Args:
            parent: GitPDMDockWidget - parent panel with UI widgets and state
            git_client: GitClient - for git operations
        """
        self._parent = parent
        self._git_client = git_client
    
    # ========== Public API ==========
    
    def validate_repo_path(self, path):
        """
        Validate that path is inside a git repository.
        Run validation in background to keep UI responsive.
        
        Args:
            path: str - path to validate
        """
        if not path:
            self._clear_repo_info()
            return

        # Show "Checking..." status
        self._parent.validate_label.setText("Checking…")
        self._parent.validate_label.setStyleSheet(
            "color: orange; font-style: italic;"
        )

        # Run validation in background
        repo_root = self._git_client.get_repo_root(path)

        if repo_root:
            self._handle_valid_repo(repo_root)
        else:
            self._handle_invalid_repo(path)

    def refresh_clicked(self):
        """
        Handle Refresh Status button click.
        Re-validate current repo path and refresh status.
        """
        current_path = self._parent.repo_path_field.text()
        if not current_path:
            log.warning("No repository path set")
            return
        
        # Show busy feedback immediately
        self._parent._start_busy_feedback("Refreshing…")
        self._parent._update_operation_status("Refreshing…")
        
        # Defer the actual work to keep UI responsive
        QtCore.QTimer.singleShot(50, lambda: self._do_refresh(current_path))

    def create_repo_clicked(self):
        """
        Handle Create Repo button click.
        Initialize a new git repository in the selected path.
        """
        current_path = self._parent.repo_path_field.text()
        if not current_path:
            log.warning("No path specified for repo creation")
            self._parent._show_status_message(
                "Error: Please specify a folder path first",
                is_error=True
            )
            return
        
        # Normalize the path
        current_path = os.path.normpath(os.path.expanduser(current_path))
        
        # Check if path exists
        if not os.path.isdir(current_path):
            log.warning(f"Path does not exist: {current_path}")
            self._parent._show_status_message(
                f"Error: Folder does not exist: {current_path}",
                is_error=True
            )
            return
        
        # Show confirmation dialog
        dlg = QtWidgets.QMessageBox(self._parent)
        dlg.setWindowTitle("Create Repository")
        dlg.setText(f"Create a new git repository at:\n{current_path}")
        dlg.setStandardButtons(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel
        )
        dlg.setDefaultButton(QtWidgets.QMessageBox.Cancel)
        dlg.setIcon(QtWidgets.QMessageBox.Question)
        
        if dlg.exec() != QtWidgets.QMessageBox.Yes:
            log.info("Repository creation cancelled by user")
            return
        
        # Show busy feedback
        self._parent._start_busy_feedback("Creating repository…")
        self._parent._update_operation_status("Creating repository…")
        
        # Perform the actual init in a deferred call to keep UI responsive
        QtCore.QTimer.singleShot(50, lambda: self._do_create_repo(current_path))

    def connect_remote_clicked(self):
        """Entry point for Connect Remote button or prompt."""
        if not self._parent._current_repo_root:
            self._parent._show_status_message(
                "No repository selected", is_error=True
            )
            return
        self._start_connect_remote_flow()

    def fetch_branch_and_status(self, repo_root):
        """
        Fetch current branch and working tree status for repo_root.
        
        Args:
            repo_root: str - repository root path
        """
        branch = self._git_client.current_branch(repo_root)
        self._parent.branch_label.setText(branch)

        self._parent._refresh_status_views(repo_root)

        self._parent._update_upstream_info(repo_root)

        # Display last fetch time
        self._parent._fetch_pull.display_last_fetch()

    # ========== Private Implementation ==========

    def _clear_repo_info(self):
        """Clear all repository information from UI."""
        self._parent.validate_label.setText("Not checked")
        self._parent.validate_label.setStyleSheet(
            "color: gray; font-style: italic;"
        )
        self._parent.repo_root_label.setText("—")
        self._parent.branch_label.setText("—")
        self._parent.working_tree_label.setText("—")
        self._parent.upstream_label.setText("—")
        self._parent.ahead_behind_label.setText("—")
        self._parent.last_fetch_label.setText("—")
        self._parent._set_meta_label(self._parent.branch_label, "gray")
        self._parent._set_strong_label(self._parent.working_tree_label, "black")
        self._parent._set_meta_label(self._parent.upstream_label, "gray")
        self._parent._set_strong_label(self._parent.ahead_behind_label, "gray")
        self._parent._set_meta_label(self._parent.last_fetch_label, "gray")
        self._parent.root_toggle_btn.setEnabled(False)
        self._parent.root_toggle_btn.setChecked(False)
        self._parent.repo_root_row.setVisible(False)
        self._parent.root_toggle_btn.setArrowType(QtCore.Qt.RightArrow)
        self._parent.root_toggle_btn.setText("Show root")
        self._parent.browser_window_btn.setEnabled(False)
        self._parent._update_button_states()

    def _handle_valid_repo(self, repo_root):
        """Handle successful repository validation."""
        # Valid repo
        self._parent.validate_label.setText("OK")
        self._parent.validate_label.setStyleSheet("color: green;")
        self._parent.repo_root_label.setText(repo_root)
        self._parent._current_repo_root = repo_root

        self._parent.root_toggle_btn.setEnabled(True)
        self._parent.repo_root_row.setVisible(
            self._parent.root_toggle_btn.isChecked()
        )
        self._parent.browser_window_btn.setEnabled(True)

        # Set FreeCAD working directory to repo folder
        # This ensures Save As dialog defaults to repo folder
        self._set_freecad_working_directory(repo_root)

        # Fetch branch and status
        self.fetch_branch_and_status(repo_root)
        # Refresh repo browser
        self._parent._file_browser.refresh_files()
        # Update preview status area
        self._parent._update_preview_status_labels()
        
        # Update button states (including branch buttons)
        self._parent._update_button_states()
        
        # Explicitly ensure branch buttons are updated
        QtCore.QTimer.singleShot(100, self._parent._update_branch_button_states)
        
        log.info(f"Validated repo: {repo_root}")

    def _handle_invalid_repo(self, path):
        """Handle invalid repository path."""
        # Invalid repo
        self._parent.validate_label.setText("Invalid")
        self._parent.validate_label.setStyleSheet("color: red;")
        self._parent.repo_root_label.setText("—")
        self._parent.branch_label.setText("—")
        self._parent.working_tree_label.setText("—")
        self._parent.upstream_label.setText("—")
        self._parent.ahead_behind_label.setText("—")
        self._parent.last_fetch_label.setText("—")
        self._parent._set_meta_label(self._parent.branch_label, "gray")
        self._parent._set_strong_label(self._parent.working_tree_label, "black")
        self._parent._set_meta_label(self._parent.upstream_label, "gray")
        self._parent._set_strong_label(self._parent.ahead_behind_label, "gray")
        self._parent._set_meta_label(self._parent.last_fetch_label, "gray")
        self._parent._current_repo_root = None
        self._parent.root_toggle_btn.setEnabled(False)
        self._parent.root_toggle_btn.setChecked(False)
        self._parent.repo_root_row.setVisible(False)
        self._parent.root_toggle_btn.setArrowType(QtCore.Qt.RightArrow)
        self._parent.root_toggle_btn.setText("Show root")
        self._parent.browser_window_btn.setEnabled(False)
        self._parent._update_button_states()
        # Clear browser section
        self._parent._file_browser.clear_browser()
        # Do not overwrite saved path - just show typed text in UI
        log.warning(
            f"Not a git repository: {path}"
        )

    def _set_freecad_working_directory(self, directory: str):
        """
        Set FreeCAD's working directory to ensure Save As dialog defaults to repo folder.
        
        This prevents users from accidentally saving files outside the repo, which would
        cause repo health issues.
        
        Args:
            directory: Absolute path to set as working directory
        """
        if not directory or not os.path.isdir(directory):
            log.debug(f"Cannot set working directory, invalid path: {directory}")
            return
        
        try:
            # Normalize the path
            directory = os.path.abspath(os.path.normpath(directory))
            
            # Method 1: Change Python's current working directory
            # FreeCAD's file dialogs often respect this
            os.chdir(directory)
            log.info(f"Set Python working directory: {directory}")
            
            # Method 2: Set FreeCAD's parameter for last file dialog directory
            try:
                import FreeCAD
                param_grp = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/General")
                if param_grp:
                    param_grp.SetString("FileOpenSavePath", directory)
                    log.info(f"Set FreeCAD file dialog default: {directory}")
            except ImportError:
                # FreeCAD not available (running in test environment)
                log.debug("FreeCAD not available, skipping parameter setting")
            except Exception as e:
                log.warning(f"Failed to set FreeCAD file dialog default: {e}")
                
        except Exception as e:
            log.error(f"Failed to set working directory: {e}")

    def _do_refresh(self, path):
        """Execute the refresh operation (runs after brief delay)."""
        try:
            self.validate_repo_path(path)
        finally:
            self._parent._stop_busy_feedback()
            self._parent._show_status_message("Refresh complete", is_error=False)
            QtCore.QTimer.singleShot(2000, self._parent._clear_status_message)

    def _do_create_repo(self, path):
        """Execute the actual repo creation."""
        try:
            log.info(f"Creating repository at: {path}")
            result = self._git_client.init_repo(path)
            
            if result.ok:
                log.info("Repository created successfully")
                self._parent._show_status_message(
                    "Repository created successfully!",
                    is_error=False
                )
                
                # Show helpful next steps dialog
                dlg = QtWidgets.QMessageBox(self._parent)
                dlg.setWindowTitle("Repository Created")
                dlg.setText(
                    "Your local repository has been created successfully!\n\n"
                    "Next steps:\n"
                    "1. Create a repository on GitHub/GitLab\n"
                    "2. Copy the repository URL\n"
                    "3. Run in a terminal:\n"
                    "   git -C \"" + path + "\" remote add origin <your-repo-url>\n\n"
                    "Then you'll be able to commit and publish your changes."
                )
                dlg.setStandardButtons(
                    QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Yes
                )
                dlg.button(QtWidgets.QMessageBox.Yes).setText(
                    "Connect Remote Now"
                )
                dlg.setIcon(QtWidgets.QMessageBox.Information)
                choice = dlg.exec()
                if choice == QtWidgets.QMessageBox.Yes:
                    # Launch remote connect flow immediately
                    QtCore.QTimer.singleShot(50, self.connect_remote_clicked)
                
                # Refresh the repo validation with the new repo
                QtCore.QTimer.singleShot(500, lambda: self.validate_repo_path(path))
            else:
                log.error(f"Repository creation failed: {result.stderr}")
                self._parent._show_status_message(
                    f"Error: Failed to create repository",
                    is_error=True
                )
        except Exception as e:
            log.error(f"Exception during repo creation: {e}")
            self._parent._show_status_message(
                f"Error: {str(e)}",
                is_error=True
            )
        finally:
            self._parent._stop_busy_feedback()

    def _start_connect_remote_flow(self, url_hint=""):
        """Prompt user for remote URL and start add-remote operation."""
        remote_name = getattr(self._parent, "_remote_name", "origin") or "origin"
        prompt_title = "Connect Remote"
        prompt_label = (
            f"Add remote '{remote_name}'.\n"
            "Paste the repository URL (GitHub Desktop will handle auth):"
        )
        url, ok = QtWidgets.QInputDialog.getText(
            self._parent,
            prompt_title,
            prompt_label,
            text=url_hint
        )
        if not ok:
            log.info("Connect Remote cancelled")
            return

        url = url.strip()
        if not url:
            self._parent._show_status_message("Remote URL required", is_error=True)
            return

        # Run asynchronously to keep UI responsive
        self._parent._start_busy_feedback("Connecting remote…")
        self._parent._update_operation_status("Connecting remote…")
        QtCore.QTimer.singleShot(
            50,
            lambda: self._do_connect_remote(remote_name, url)
        )

    def _do_connect_remote(self, remote_name, url):
        """Execute remote add and refresh UI."""
        try:
            if not self._parent._current_repo_root:
                self._parent._show_status_message(
                    "No repository selected", is_error=True
                )
                return

            result = self._git_client.add_remote(
                self._parent._current_repo_root, remote_name, url
            )

            if result.ok:
                self._parent._show_status_message(
                    "Remote connected. You can publish now.",
                    is_error=False
                )
                self._parent._cached_has_remote = True
                # Refresh labels/status to pick up remote
                self.validate_repo_path(self._parent._current_repo_root)
            else:
                msg = result.stderr or "Failed to add remote"
                QtWidgets.QMessageBox.critical(
                    self._parent,
                    "Connect Remote Failed",
                    msg
                )
                self._parent._show_status_message(
                    f"Error: {msg}", is_error=True
                )
        except Exception as e:
            log.error(f"Exception during connect remote: {e}")
            self._parent._show_status_message(
                f"Error: {str(e)}", is_error=True
            )
        finally:
            self._parent._stop_busy_feedback()
