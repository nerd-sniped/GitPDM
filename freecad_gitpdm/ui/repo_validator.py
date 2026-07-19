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
            "Neither PySide6 nor PySide2 found. FreeCAD installation may be incomplete."
        ) from e

from freecad_gitpdm.core import log, session_lock, settings, storage_mode, checkpoint


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
        Run validation in background to keep UI responsive (Sprint PERF-2).

        Args:
            path: str - path to validate
        """
        if not path:
            self._clear_repo_info()
            return

        # Show "Checking..." status
        self._parent.validate_label.setText("Checking…")
        self._parent.validate_label.setStyleSheet("color: orange; font-style: italic;")

        # Sprint PERF-2: Run validation in background via job_runner
        def _run_validation():
            repo_root = self._git_client.get_repo_root(path)
            return {"repo_root": repo_root, "original_path": path}

        # Use job_runner for async operation
        if hasattr(self._parent, "_job_runner"):
            self._parent._job_runner.run_callable(
                "validate_repo",
                _run_validation,
                on_success=self._on_validation_complete,
                on_error=self._on_validation_error,
            )
        else:
            # Fallback to synchronous for unit tests
            result = _run_validation()
            self._on_validation_complete(result)

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

    def change_storage_mode_clicked(self):
        """Handle the Storage Mode 'Change…' button click (G3)."""
        from freecad_gitpdm.ui.storage_mode_dialog import StorageModeDialog

        if not self._parent._current_repo_root:
            self._parent._show_status_message("No repository selected", is_error=True)
            return

        current_mode = self._parent._current_storage_mode
        dlg = StorageModeDialog(current_mode, parent=self._parent)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            log.info("Storage mode change cancelled")
            return

        new_mode = dlg.selected_mode
        if new_mode == current_mode:
            return

        result = storage_mode.apply_storage_mode(
            self._parent._current_repo_root, new_mode, git_client=self._git_client
        )
        if not result.ok:
            self._parent._show_status_message(f"Error: {result.message}", is_error=True)
            return

        self._parent._current_storage_mode = new_mode
        self._parent._update_storage_mode_label()
        self._parent._show_status_message(
            f"Storage mode set to '{new_mode}'. Review and commit "
            ".gitattributes / .freecad-pdm/config.json to share it.",
            is_error=False,
        )
        log.info(f"Storage mode changed to '{new_mode}'")

    def connect_remote_clicked(self):
        """Entry point for Connect Remote button or prompt."""
        if not self._parent._current_repo_root:
            self._parent._show_status_message("No repository selected", is_error=True)
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

    # Sprint PERF-2: Async validation callbacks
    def _on_validation_complete(self, result):
        """Callback when async repo validation completes (Sprint PERF-2)."""
        try:
            repo_root = result.get("repo_root")
            original_path = result.get("original_path")

            if repo_root:
                self._handle_valid_repo(repo_root)
            else:
                self._handle_invalid_repo(original_path)
        except Exception as e:
            log.error(f"Error processing validation result: {e}")
            self._parent.validate_label.setText("Error")
            self._parent.validate_label.setStyleSheet("color: red;")

    def _on_validation_error(self, error):
        """Callback when async repo validation fails (Sprint PERF-2)."""
        log.warning(f"Validation error: {error}")
        self._parent.validate_label.setText("Error")
        self._parent.validate_label.setStyleSheet("color: red;")

    # ========== Private Implementation ==========

    def _clear_repo_info(self):
        """Clear all repository information from UI."""
        self._parent.validate_label.setText("Not checked")
        self._parent.validate_label.setStyleSheet("color: gray; font-style: italic;")
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
        self._parent._current_storage_mode = storage_mode.DEFAULT_MODE
        self._parent._update_storage_mode_label()
        self._parent._update_button_states()
        self._parent._check_shallow_clone_status(None)

    def _handle_valid_repo(self, repo_root):
        """Handle successful repository validation."""
        if not self._acquire_session_lock(repo_root):
            return

        # Valid repo
        self._parent.validate_label.setText("OK")
        self._parent.validate_label.setStyleSheet("color: green;")
        self._parent.repo_root_label.setText(repo_root)
        self._parent._current_repo_root = repo_root
        self._parent._first_run_hint.setVisible(False)

        self._parent.root_toggle_btn.setEnabled(True)
        self._parent.repo_root_row.setVisible(self._parent.root_toggle_btn.isChecked())

        # Set FreeCAD working directory to repo folder
        # This ensures Save As dialog defaults to repo folder
        self._set_freecad_working_directory(repo_root)

        # G3: cache the repo's storage mode for display and for the
        # document observer's save-time compression scoping (settings.py).
        # This is read-only here -- it never touches the global FreeCAD
        # compression preference just because a repo was opened; that was
        # the R1.2 regression this replaces.
        self._parent._current_storage_mode = storage_mode.get_storage_mode(repo_root)
        self._parent._update_storage_mode_label()

        # Fetch branch and status
        self.fetch_branch_and_status(repo_root)
        # Update preview status area
        self._parent._update_preview_status_labels()
        # Show/hide shallow-clone banner (Phase G5 / R2.4)
        self._parent._check_shallow_clone_status(repo_root)

        # Update button states (including branch buttons)
        self._parent._update_button_states()

        # Explicitly ensure branch buttons are updated
        QtCore.QTimer.singleShot(100, self._parent._update_branch_button_states)

        # Phase G6 (R2.5): offer to restore a checkpoint left over from an
        # interrupted previous session, once the rest of activation settles.
        QtCore.QTimer.singleShot(
            200, lambda: self._maybe_offer_recovery_restore(repo_root)
        )

        log.info(f"Validated repo: {repo_root}")

    def _maybe_offer_recovery_restore(self, repo_root):
        """
        Phase G6 (R2.5) restore-on-start: if refs/heads/gitpdm/recovery is
        ahead of HEAD, offer to restore it. Only offered when no FreeCAD
        document is currently open -- restoring writes files into the
        working tree, the same class of operation the "close ALL documents"
        guard around branch switching exists for (see CLAUDE.md).
        """
        try:
            if self._parent._current_repo_root != repo_root:
                return  # repo was switched again before this fired
            status = checkpoint.recovery_branch_status(self._git_client, repo_root)
            if not status.available:
                return

            open_docs = self._parent._branch_ops._get_all_open_fcstd_documents()
            if open_docs:
                log.debug(
                    "Recovery checkpoint available but documents are open; "
                    "not prompting to restore"
                )
                return

            reply = QtWidgets.QMessageBox.question(
                self._parent,
                "Recovery Checkpoint Available",
                "GitPDM found work checkpointed before this session started "
                "(possibly from a crash or an interrupted shutdown).\n\n"
                f"Recovery snapshot: {status.recovery_sha[:8]}\n\n"
                "Restore it into your working files now?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                log.info("User declined recovery-checkpoint restore")
                return

            result = checkpoint.restore_recovery_checkpoint(
                self._git_client, repo_root, status.recovery_sha
            )
            if result.ok:
                QtWidgets.QMessageBox.information(
                    self._parent,
                    "Recovery Restored",
                    "Recovery checkpoint restored into your working files.",
                )
                log.info(f"Restored recovery checkpoint {status.recovery_sha[:8]}")
            else:
                QtWidgets.QMessageBox.warning(
                    self._parent,
                    "Restore Failed",
                    f"Could not restore recovery checkpoint:\n{result.stderr}",
                )
        except Exception as e:
            log.debug(f"Recovery restore check failed: {e}")

    def _acquire_session_lock(self, repo_root) -> bool:
        """
        Acquire the advisory cross-process session lock for repo_root
        (Phase G5 / R2.3). Releases any lock we hold on a *different*
        previously-active repo first (switching repos in the same panel).

        Returns True if activation should proceed, False if the user
        declined to steal a lock held by another live session.
        """
        previous_root = self._parent._current_repo_root
        if previous_root and previous_root != repo_root:
            session_lock.release_lock(previous_root)

        result = session_lock.acquire_lock(repo_root)
        if result.ok:
            return True

        existing = result.existing
        detail = (
            f"PID {existing.pid} on {existing.hostname or 'unknown host'}, "
            f"opened {existing.timestamp}"
            if existing
            else "another session"
        )
        choice = QtWidgets.QMessageBox.warning(
            self._parent,
            "Repository Already Open",
            "This repository appears to be open in another GitPDM session "
            f"({detail}).\n\n"
            "Opening it here too risks both sessions writing to the same "
            "working tree at once. Continue anyway?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if choice != QtWidgets.QMessageBox.Yes:
            log.info(f"Declined to open repo locked by another session: {repo_root}")
            self._parent.validate_label.setText("Locked by another session")
            self._parent.validate_label.setStyleSheet("color: red;")
            return False

        session_lock.acquire_lock(repo_root, force=True)
        log.warning(f"Overrode session lock held by another instance: {repo_root}")
        return True

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
        if self._parent._current_repo_root:
            session_lock.release_lock(self._parent._current_repo_root)
        self._parent._current_repo_root = None
        self._parent._current_storage_mode = storage_mode.DEFAULT_MODE
        self._parent._update_storage_mode_label()
        self._parent.root_toggle_btn.setEnabled(False)
        self._parent.root_toggle_btn.setChecked(False)
        self._parent.repo_root_row.setVisible(False)
        self._parent.root_toggle_btn.setArrowType(QtCore.Qt.RightArrow)
        self._parent.root_toggle_btn.setText("Show root")
        self._parent._update_button_states()
        self._parent._check_shallow_clone_status(None)
        # Do not overwrite saved path - just show typed text in UI
        log.warning(f"Not a git repository: {path}")

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

            # Method 2: Set multiple FreeCAD parameters for file dialog directory
            # FreeCAD uses different parameters depending on context
            try:
                import FreeCAD

                # Main file dialog path parameter
                param_grp = FreeCAD.ParamGet(
                    "User parameter:BaseApp/Preferences/General"
                )
                if param_grp:
                    param_grp.SetString("FileOpenSavePath", directory)
                    log.info(f"Set FreeCAD FileOpenSavePath: {directory}")

                # Force Qt's own file dialog instead of the OS-native one.
                # The native Windows Save dialog keeps its own persisted
                # "last folder used" (in the registry) that silently overrides
                # whatever directory FreeCAD/GitPDM passes in; Qt's dialog
                # honors FileOpenSavePath/DefaultPath directly.
                try:
                    dlg_param = FreeCAD.ParamGet(
                        "User parameter:BaseApp/Preferences/Dialog"
                    )
                    if dlg_param:
                        dlg_param.SetBool("DontUseNativeDialog", True)
                except Exception as e:
                    log.debug(f"Could not set DontUseNativeDialog: {e}")

                # Also set document-specific parameters
                try:
                    doc_param = FreeCAD.ParamGet(
                        "User parameter:BaseApp/Preferences/Document"
                    )
                    if doc_param:
                        doc_param.SetString("DefaultPath", directory)
                        log.debug(f"Set FreeCAD Document DefaultPath: {directory}")
                except Exception as e:
                    log.debug(f"Could not set Document DefaultPath: {e}")

                # Set the last path used for FCStd files specifically
                try:
                    app_param = FreeCAD.ParamGet("User parameter:BaseApp")
                    if app_param:
                        app_param.SetString("LastPath", directory)
                        log.debug(f"Set FreeCAD LastPath: {directory}")
                except Exception as e:
                    log.debug(f"Could not set LastPath: {e}")

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
                    "Repository created successfully!", is_error=False
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
                    '   git -C "' + path + '" remote add origin <your-repo-url>\n\n'
                    "Then you'll be able to commit and publish your changes."
                )
                dlg.setStandardButtons(
                    QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Yes
                )
                dlg.button(QtWidgets.QMessageBox.Yes).setText("Connect Remote Now")
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
                    f"Error: Failed to create repository", is_error=True
                )
        except Exception as e:
            log.error(f"Exception during repo creation: {e}")
            self._parent._show_status_message(f"Error: {str(e)}", is_error=True)
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
            self._parent, prompt_title, prompt_label, text=url_hint
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
        QtCore.QTimer.singleShot(50, lambda: self._do_connect_remote(remote_name, url))

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
                    "Remote connected. You can publish now.", is_error=False
                )
                self._parent._cached_has_remote = True
                # Refresh labels/status to pick up remote
                self.validate_repo_path(self._parent._current_repo_root)
            else:
                msg = result.stderr or "Failed to add remote"
                QtWidgets.QMessageBox.critical(
                    self._parent, "Connect Remote Failed", msg
                )
                self._parent._show_status_message(f"Error: {msg}", is_error=True)
        except Exception as e:
            log.error(f"Exception during connect remote: {e}")
            self._parent._show_status_message(f"Error: {str(e)}", is_error=True)
        finally:
            self._parent._stop_busy_feedback()
