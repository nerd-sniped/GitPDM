"""
Action-based Repository Validation Handler
Phase 2: Uses actions layer instead of direct GitClient calls
"""

import os

# Qt compatibility layer
try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    try:
        from PySide6 import QtCore, QtWidgets
    except ImportError as e:
        raise ImportError(
            "PySide6 not found. FreeCAD installation may be incomplete."
        ) from e

from freecad.gitpdm.core import log, settings
from freecad.gitpdm.actions import validate_repo, init_repo, create_action_context


class ActionValidationHandler:
    """
    Action-based repository validation handler.
    
    Uses actions layer for validation and initialization operations.
    Replaces direct GitClient calls with action functions.
    """

    def __init__(self, parent, git_client, job_runner):
        """
        Initialize action validation handler.

        Args:
            parent: GitPDMDockWidget - parent panel with UI widgets and state
            git_client: GitClient - wrapped by action backend
            job_runner: JobRunner - for background operations
        """
        self._parent = parent
        self._git_client = git_client
        self._job_runner = job_runner

    # ========== Public API ==========

    def validate_repo_path(self, path):
        """
        Validate that path is inside a git repository using actions layer.
        Run validation in background to keep UI responsive.

        Args:
            path: str - path to validate
        """
        if not path:
            self._clear_repo_info()
            return

        # Show "Checking..." status
        self._parent.validate_label.setText("Checking…")
        self._parent.validate_label.setStyleSheet("color: orange; font-style: italic;")

        # Run validation via actions layer in background
        def _run_validation():
            ctx = create_action_context(self._git_client, path)
            result = validate_repo(ctx, path)
            return {"result": result, "original_path": path}

        # Use job_runner for async operation
        self._job_runner.run_callable(
            "validate_repo",
            _run_validation,
            on_success=self._on_validation_complete,
            on_error=self._on_validation_error,
        )

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
        Handle Create Repo button click using actions layer.
        Initialize a new git repository in the selected path.
        """
        current_path = self._parent.repo_path_field.text()
        if not current_path:
            log.warning("No path specified for repo creation")
            self._parent._show_status_message(
                "Error: Please specify a folder path first", is_error=True
            )
            return

        # Normalize the path
        current_path = os.path.normpath(os.path.expanduser(current_path))

        # Check if path exists
        if not os.path.isdir(current_path):
            log.warning(f"Path does not exist: {current_path}")
            self._parent._show_status_message(
                f"Error: Folder does not exist: {current_path}", is_error=True
            )
            return

        # Show confirmation dialog
        dlg = QtWidgets.QMessageBox(self._parent)
        dlg.setWindowTitle("Create Repository")
        dlg.setText(f"Create a new git repository at:\n{current_path}")
        dlg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)
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
            self._parent._show_status_message("No repository selected", is_error=True)
            return
        self._start_connect_remote_flow()

    # ========== Private Implementation ==========

    def _on_validation_complete(self, data):
        """Callback when async repo validation completes."""
        try:
            result = data.get("result")
            original_path = data.get("original_path")

            repo_root = result.details.get("repo_root")
            if result.ok and repo_root:
                self._handle_valid_repo(repo_root)
            else:
                self._handle_invalid_repo(original_path)
        except Exception as e:
            log.error(f"Error processing validation result: {e}")
            self._parent.validate_label.setText("Error")
            self._parent.validate_label.setStyleSheet("color: red;")

    def _on_validation_error(self, error_message):
        """Callback when async validation encounters an error."""
        log.error(f"Validation error: {error_message}")
        self._parent.validate_label.setText("Error")
        self._parent.validate_label.setStyleSheet("color: red;")
        
        # Stop busy feedback
        if hasattr(self._parent, '_stop_busy_feedback'):
            self._parent._stop_busy_feedback()

    def _handle_valid_repo(self, repo_root):
        """Handle successful repository validation."""
        self._parent.validate_label.setText("✓ Valid Repository")
        self._parent.validate_label.setStyleSheet("color: green;")
        
        # Display repo root
        self._parent.repo_root_label.setText(repo_root)
        
        # Update internal state
        self._parent._current_repo_root = repo_root
        
        # Save path
        settings.save_repo_path(repo_root)
        
        # Enable buttons
        self._parent.create_repo_btn.setEnabled(False)
        self._parent.connect_remote_btn.setEnabled(True)
        
        # Fetch branch and status
        self.fetch_branch_and_status(repo_root)
        
        log.info(f"Repository validated: {repo_root}")

    def _handle_invalid_repo(self, path):
        """Handle invalid repository validation."""
        self._parent.validate_label.setText("Not a repository")
        self._parent.validate_label.setStyleSheet("color: red;")
        
        # Clear repo root display
        self._parent.repo_root_label.setText("")
        
        # Update internal state
        self._parent._current_repo_root = None
        
        # Enable create button
        self._parent.create_repo_btn.setEnabled(True)
        self._parent.connect_remote_btn.setEnabled(False)
        
        log.info(f"Not a repository: {path}")

    def _clear_repo_info(self):
        """Clear all repository information."""
        self._parent.validate_label.setText("")
        self._parent.repo_root_label.setText("")
        self._parent._current_repo_root = None
        self._parent.create_repo_btn.setEnabled(False)
        self._parent.connect_remote_btn.setEnabled(False)

    def _do_refresh(self, current_path):
        """
        Perform actual refresh operation using actions layer.
        """
        try:
            # Re-validate the path
            ctx = create_action_context(self._git_client, current_path)
            result = validate_repo(ctx, current_path)
            
            repo_root = result.details.get("repo_root")
            if result.ok and repo_root:
                # Refresh status views
                self._parent._refresh_status_views(repo_root)
                self._parent._update_upstream_info(repo_root)
                
                # Display last fetch time
                if hasattr(self._parent, '_fetch_pull'):
                    self._parent._fetch_pull.display_last_fetch()
                
                self._parent._show_status_message("Refreshed", is_error=False)
                log.info("Repository status refreshed")
            else:
                self._parent._show_status_message(
                    f"Error: {result.message}", is_error=True
                )
        except Exception as e:
            log.error(f"Refresh failed: {e}")
            self._parent._show_status_message(
                f"Refresh failed: {e}", is_error=True
            )
        finally:
            self._parent._stop_busy_feedback()

    def _do_create_repo(self, path):
        """
        Perform actual repository creation using actions layer.
        """
        try:
            # Create context and run init action
            ctx = create_action_context(self._git_client, path)
            result = init_repo(ctx, path)
            
            if result.ok:
                self._parent._show_status_message(
                    "Repository created successfully", is_error=False
                )
                log.info(f"Repository initialized at: {path}")
                
                # Trigger validation to update UI
                self.validate_repo_path(path)
            else:
                self._parent._show_status_message(
                    f"Failed to create repository: {result.message}", is_error=True
                )
                log.error(f"Repository init failed: {result.message}")
        except Exception as e:
            log.error(f"Repository creation failed: {e}")
            self._parent._show_status_message(
                f"Error: {e}", is_error=True
            )
        finally:
            self._parent._stop_busy_feedback()

    def _start_connect_remote_flow(self):
        """Start the connect remote flow (delegates to parent)."""
        # This is a complex multi-step wizard that we'll keep as-is for now
        # It involves dialogs and GitHub API calls
        if hasattr(self._parent, '_start_connect_remote_flow'):
            self._parent._start_connect_remote_flow()
        else:
            log.warning("Connect remote flow not available")

    def fetch_branch_and_status(self, repo_root):
        """
        Fetch current branch and working tree status for repo_root.
        This delegates to existing panel methods for now.

        Args:
            repo_root: str - repository root path
        """
        # Get current branch (direct call for now - can be action later)
        branch = self._git_client.current_branch(repo_root)
        self._parent.branch_label.setText(branch)

        # Refresh status views
        self._parent._refresh_status_views(repo_root)
        self._parent._update_upstream_info(repo_root)

        # Display last fetch time
        if hasattr(self._parent, '_fetch_pull'):
            self._parent._fetch_pull.display_last_fetch()
