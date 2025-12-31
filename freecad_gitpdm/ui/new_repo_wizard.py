# -*- coding: utf-8 -*-
"""
GitPDM New Repository Wizard
Sprint OAUTH-4: Dialog to create GitHub repo + local scaffold + push
Sprint OAUTH-6: Error handling, token invalidation detection

Guides user through:
  1. Selecting local folder
  2. Entering repo name + visibility
  3. Choosing scaffolding options
  4. Executing creation steps with progress
"""

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
import re
from typing import Optional, Tuple, Callable

from freecad_gitpdm.core import log, scaffold
from freecad_gitpdm.github.create_repo import (
    create_user_repo,
    CreateRepoRequest,
)
from freecad_gitpdm.github.api_client import GitHubApiClient
from freecad_gitpdm.github.errors import GitHubApiError
from freecad_gitpdm.git import client as git_client_module


class NewRepoWizard(QtWidgets.QWizard):
    """Multi-step wizard to create a new GitHub repo + local scaffold."""

    def __init__(
        self,
        api_client: Optional[GitHubApiClient] = None,
        parent=None,
        on_session_expired: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Create New Repository")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._api_client = api_client
        self._git_client = git_client_module.GitClient()
        self._on_session_expired = on_session_expired

        # Wizard steps
        self._input_page = _InputPage(self)
        self._options_page = _OptionsPage(self)
        self._progress_page = _ProgressPage(self)

        self.addPage(self._input_page)
        self.addPage(self._options_page)
        self.addPage(self._progress_page)

        # Results
        self._created_repo_path = None
        self._created_repo_name = None

        # Hook finish
        self.finished.connect(self._on_finished)

    def _on_finished(self):
        """Called when wizard is accepted or rejected."""
        if self.result() == QtWidgets.QDialog.Accepted:
            log.info("New repo wizard completed successfully")
        else:
            log.info("New repo wizard cancelled")

    def accept(self):
        """Override to allow auto-execution on progress page."""
        # Workflow auto-starts when progress page is shown (initializePage)
        # Just proceed with normal wizard acceptance
        super().accept()

    def get_created_repo_path(self) -> Optional[str]:
        """Return local path of created repo, or None if failed."""
        return self._created_repo_path

    def get_created_repo_name(self) -> Optional[str]:
        """Return name of created repo (github username/repo), or None if failed."""
        return self._created_repo_name


class _InputPage(QtWidgets.QWizardPage):
    """Page 1: Select folder and enter repo details."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle("Repository Details")
        self.setSubTitle("Choose a folder and name for your new repository")

        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        # Local folder
        folder_layout = QtWidgets.QHBoxLayout()
        self._folder_edit = QtWidgets.QLineEdit()
        self._folder_edit.setPlaceholderText("Select a folder...")
        self._folder_edit.textChanged.connect(self._on_field_changed)
        folder_btn = QtWidgets.QPushButton("Browse...")
        folder_btn.clicked.connect(self._on_browse_folder)
        folder_layout.addWidget(self._folder_edit)
        folder_layout.addWidget(folder_btn)
        layout.addRow("Local Folder:", folder_layout)

        # Repo name
        self._name_edit = QtWidgets.QLineEdit()
        self._name_edit.setPlaceholderText("e.g., my-awesome-project")
        self._name_edit.textChanged.connect(self._on_field_changed)
        layout.addRow("Repository Name:", self._name_edit)

        # Visibility
        self._private_check = QtWidgets.QCheckBox("Private (not visible to public)")
        self._private_check.stateChanged.connect(self._on_field_changed)
        layout.addRow("Visibility:", self._private_check)

        # Description (optional)
        self._desc_edit = QtWidgets.QLineEdit()
        self._desc_edit.setPlaceholderText(
            "Optional description (can be edited on GitHub)"
        )
        layout.addRow("Description:", self._desc_edit)

        # Status label
        self._status_label = QtWidgets.QLabel("")
        self._status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addRow("", self._status_label)

    def _on_field_changed(self):
        """Trigger validation update when any field changes."""
        self.completeChanged.emit()

    def _on_browse_folder(self):
        """Show folder selection dialog."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Repository Folder",
            "",
            QtWidgets.QFileDialog.ShowDirsOnly,
        )
        if folder:
            self._folder_edit.setText(folder)
            # Explicitly trigger validation update
            self.completeChanged.emit()

    def get_inputs(self) -> dict:
        """Return dict with folder, name, private, description."""
        selected_folder = self._folder_edit.text().strip()
        repo_name = self._name_edit.text().strip()

        # Create subfolder with repo name inside selected folder
        if selected_folder and repo_name:
            # Normalize paths to handle spaces and special characters properly
            repo_folder = os.path.normpath(os.path.join(selected_folder, repo_name))
        else:
            repo_folder = selected_folder

        return {
            "folder": repo_folder,
            "name": repo_name,
            "private": self._private_check.isChecked(),
            "description": self._desc_edit.text().strip() or None,
        }

    def isComplete(self) -> bool:
        """Validate inputs before allowing next."""
        inputs_folder = self._folder_edit.text().strip()
        name = self._name_edit.text().strip()

        # Validate base folder
        if not inputs_folder:
            self._status_label.setText("")
            return False

        inputs_folder_abs = os.path.normpath(os.path.abspath(inputs_folder))
        if not os.path.isdir(inputs_folder_abs):
            self._status_label.setText("Folder does not exist")
            return False

        # Validate name
        if not name:
            self._status_label.setText("")
            return False

        if not re.match(r"^[a-zA-Z0-9._-]+$", name):
            self._status_label.setText(
                "Invalid name. Use letters, numbers, dash, dot, underscore."
            )
            return False

        # Check if target subfolder already exists
        target_folder = os.path.normpath(os.path.join(inputs_folder_abs, name))
        if os.path.exists(target_folder):
            self._status_label.setText(
                f"Folder '{name}' already exists. Choose a different name."
            )
            return False

        # All checks passed
        self._status_label.setText(f"Will create: {name}/")
        return True


class _OptionsPage(QtWidgets.QWizardPage):
    """Page 2: Configure scaffolding and LFS options."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle("Scaffolding Options")
        self.setSubTitle("Configure your repository structure")

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Scaffolding checkbox
        self._scaffold_check = QtWidgets.QCheckBox(
            "Add recommended CAD scaffolding (cad/, previews/, .freecad-pdm/)"
        )
        self._scaffold_check.setChecked(True)
        layout.addWidget(self._scaffold_check)

        # LFS checkbox
        self._lfs_check = QtWidgets.QCheckBox(
            "Enable Git LFS tracking for CAD files (*.FCStd, *.glb)"
        )
        self._lfs_check.setChecked(True)
        layout.addWidget(self._lfs_check)

        # Info box
        info_text = QtWidgets.QLabel(
            "• Scaffolding: Creates folder structure and initial config\n"
            "• Git LFS: Optimizes large binary files (install Git LFS if not present)\n\n"
            "You can modify these settings later in your repository."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #666;")
        layout.addWidget(info_text)

        layout.addStretch()

    def get_options(self) -> dict:
        """Return dict with scaffold and lfs options."""
        return {
            "enable_scaffold": self._scaffold_check.isChecked(),
            "enable_lfs": self._lfs_check.isChecked(),
        }


class _ProgressPage(QtWidgets.QWizardPage):
    """Page 3: Execute creation steps with real-time progress display."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle("Creating Repository")
        self.setSubTitle("Setting up your repository…")

        self._parent_wizard = parent
        self._workflow_running = False
        self._api_client = None
        self._git_client = None
        self._inputs = None
        self._options = None

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Progress list (will be populated dynamically)
        layout.addWidget(QtWidgets.QLabel("Progress:"))
        self._progress_list = QtWidgets.QListWidget()
        self._progress_list.setMaximumHeight(300)
        layout.addWidget(self._progress_list)

        # Status/error display
        self._status_text = QtWidgets.QTextEdit()
        self._status_text.setReadOnly(True)
        self._status_text.setMaximumHeight(150)
        self._status_text.setFont(QtGui.QFont("Courier", 9))
        layout.addWidget(QtWidgets.QLabel("Details:"))
        layout.addWidget(self._status_text)

        # Result banner
        self._result_label = QtWidgets.QLabel("")
        self._result_label.setWordWrap(True)
        self._result_label.setStyleSheet(
            "background: #f0f0f0; padding: 8px; border-radius: 4px;"
        )
        layout.addWidget(self._result_label)

        layout.addStretch()

    def initializePage(self):
        """Called when page is shown - start the workflow automatically."""
        super().initializePage()
        log.info("=== Progress page initialized ===")
        if not self._workflow_running:
            # Get values from parent wizard
            self._api_client = self._parent_wizard._api_client
            self._git_client = self._parent_wizard._git_client
            self._inputs = self._parent_wizard._input_page.get_inputs()
            self._options = self._parent_wizard._options_page.get_options()

            log.info(f"API client available: {self._api_client is not None}")
            log.info(f"Git client available: {self._git_client is not None}")
            log.info(f"Inputs received: {self._inputs}")
            log.info(f"Options received: {self._options}")

            # Start workflow in a deferred way (after UI renders)
            QtCore.QTimer.singleShot(100, self._start_workflow)

    def _start_workflow(self):
        """Begin the creation workflow."""
        log.info("=== NEW REPO WIZARD: Starting workflow ===")
        self._workflow_running = True
        self._progress_list.clear()
        self._status_text.clear()
        self._result_label.setText("")

        log.info(f"Inputs: {self._inputs}")
        log.info(f"Options: {self._options}")

        self.run_workflow(
            self._api_client,
            self._git_client,
            self._inputs,
            self._options,
        )

    def run_workflow(
        self,
        api_client,
        git_client: git_client_module.GitClient,
        inputs: dict,
        options: dict,
    ):
        """Execute the full creation workflow with real-time progress."""
        folder = inputs["folder"]
        name = inputs["name"]
        private = inputs["private"]
        description = inputs["description"]
        enable_scaffold = options["enable_scaffold"]
        enable_lfs = options["enable_lfs"]

        if not api_client:
            self._add_step_error(0, "API client not available")
            return

        # Normalize the path to handle spaces and special characters
        folder_abs = os.path.normpath(os.path.abspath(folder))
        log.info(f"=== run_workflow START ===")
        log.info(f"folder input: {folder}")
        log.info(f"folder_abs after normpath: {folder_abs}")
        log.info(f"name: {name}")

        try:
            # Check parent directory exists BEFORE trying to create anything
            parent_dir = os.path.dirname(folder_abs)
            log.info(f"Parent directory: {parent_dir}")
            log.info(f"Parent exists: {os.path.exists(parent_dir)}")

            if not os.path.exists(parent_dir):
                msg = f"Parent directory does not exist: {parent_dir}"
                log.error(msg)
                self._add_step(f"Creating folder: {name}/")
                self._update_step_error(0, msg)
                return

            # === STEP 0: Create the target folder ===
            self._add_step(f"Creating folder: {name}/")
            log.info(f"Step 0: About to create folder at {folder_abs}")
            log.info(f"  Folder exists before: {os.path.exists(folder_abs)}")

            # Ensure the folder doesn't already exist to avoid conflicts
            if os.path.exists(folder_abs) and not os.path.isdir(folder_abs):
                msg = f"Path exists but is not a folder: {folder_abs}"
                log.error(msg)
                self._update_step_error(0, msg)
                return

            # Create folder - try multiple approaches
            if not os.path.exists(folder_abs):
                log.info(f"Folder doesn't exist, creating it...")
                try:
                    # Approach 1: Direct makedirs
                    log.info(f"Attempt 1: os.makedirs('{folder_abs}')")
                    os.makedirs(folder_abs, exist_ok=True)
                    log.info(f"  Return from makedirs")

                    # Verify immediately
                    exists_check1 = os.path.exists(folder_abs)
                    isdir_check1 = os.path.isdir(folder_abs)
                    log.info(
                        f"  After makedirs - exists: {exists_check1}, isdir: {isdir_check1}"
                    )

                    if not exists_check1:
                        log.warning(
                            f"  os.path.exists() says False immediately after makedirs!"
                        )
                        # Try alternative check
                        import pathlib

                        pathlib_exists = pathlib.Path(folder_abs).exists()
                        log.info(f"  pathlib.Path.exists(): {pathlib_exists}")

                        if pathlib_exists:
                            log.info(
                                f"  pathlib says it exists, issue with os.path.exists()?"
                            )
                        else:
                            log.error(f"  pathlib also says it doesn't exist!")

                    if not isdir_check1:
                        msg = f"Failed to create directory (isdir=False): {folder_abs}"
                        log.error(msg)
                        self._update_step_error(0, msg)
                        return

                    log.info(f"Step 0: Folder created successfully")
                    self._update_step_success(0, f"Created: {folder_abs}")

                except PermissionError as e:
                    msg = f"Permission denied creating folder: {folder_abs}\nError: {e}"
                    log.error(msg)
                    self._update_step_error(0, msg)
                    return
                except FileExistsError as e:
                    msg = f"File exists error: {folder_abs}\nError: {e}"
                    log.error(msg)
                    self._update_step_error(0, msg)
                    return
                except OSError as e:
                    msg = f"OS Error creating folder: {e}"
                    log.error(msg)
                    self._update_step_error(0, msg)
                    return
                except Exception as e:
                    msg = f"Unexpected error creating folder: {type(e).__name__}: {e}"
                    log.error(msg)
                    self._update_step_error(0, msg)
                    return
            else:
                log.info(f"Folder already exists, using it")
                if not os.path.isdir(folder_abs):
                    self._update_step_error(
                        0, f"Path exists but is not a folder: {folder_abs}"
                    )
                    return
                self._update_step_success(0, "Using existing folder")

            # === STEP 1: Create GitHub repo ===
            self._add_step("Creating GitHub repository…")
            log.info(f"Step 1: Creating GitHub repo")
            req = CreateRepoRequest(
                name=name,
                private=private,
                description=description,
                auto_init=False,
            )
            try:
                repo_info = create_user_repo(api_client, req)
                log.info(f"GitHub repo created: {repo_info.full_name}")
                self._update_step_success(
                    1, f"GitHub repo created: {repo_info.full_name}"
                )
            except GitHubApiError as e:
                # Check if session expired (401)
                if hasattr(e, "code") and e.code == "UNAUTHORIZED":
                    log.error(f"GitHub session expired: {e}")
                    self._update_step_error(1, "Session expired. Please reconnect.")
                    if self._parent_wizard._on_session_expired:
                        self._parent_wizard._on_session_expired()
                    return

                log.error(f"GitHub repo creation failed: {e}")
                self._update_step_error(1, str(e))
                return

            # === STEP 2: Init local repo ===
            self._add_step("Initializing local git…")
            log.info(f"Step 2: Initializing git in {folder_abs}")
            log.info(
                f"  Before init - exists: {os.path.exists(folder_abs)}, isdir: {os.path.isdir(folder_abs)}"
            )

            if not os.path.isdir(folder_abs):
                msg = f"Folder disappeared before git init: {folder_abs}"
                log.error(msg)
                self._update_step_error(2, msg)
                self._show_recovery(
                    "repo exists on GitHub", folder_abs, repo_info.html_url
                )
                return

            init_result = git_client.init_repo(folder_abs)
            log.info(
                f"Git init result: ok={init_result.ok}, stderr={init_result.stderr}"
            )
            if not init_result.ok:
                self._update_step_error(2, init_result.stderr)
                self._show_recovery(
                    "repo exists on GitHub", folder_abs, repo_info.html_url
                )
                return
            self._update_step_success(2, "Local git initialized")

            # === STEP 3: Write scaffolding ===
            self._add_step("Writing scaffolding…")
            log.info(f"Step 3: Writing scaffolding")
            if enable_scaffold:
                try:
                    scaffold.apply_scaffold(
                        folder_abs, enable_lfs=enable_lfs, write_preset=True
                    )
                    log.info(f"Scaffolding created successfully")
                    self._update_step_success(
                        3, "Scaffolding created (cad/, previews/, .freecad-pdm/)"
                    )
                except OSError as e:
                    log.error(f"Scaffolding failed: {e}")
                    self._update_step_error(3, str(e))
                    return
            else:
                log.info(f"Scaffolding skipped")
                self._update_step_success(3, "Scaffolding skipped")

            # === STEP 4: Set default branch ===
            self._add_step("Setting default branch…")
            log.info(f"Step 4: Setting default branch")
            branch_result = git_client.set_default_branch(folder_abs, "main")
            if not branch_result.ok:
                log.warning(f"Failed to set default branch: {branch_result.stderr}")
            self._update_step_success(4, "Default branch set to 'main'")

            # === STEP 5: Configure LFS ===
            self._add_step("Configuring Git LFS…")
            log.info(f"Step 5: Configuring Git LFS")
            if enable_lfs:
                lfs_result = git_client.lfs_install()
                if lfs_result.ok:
                    log.info(f"Git LFS configured")
                    self._update_step_success(5, "Git LFS configured")
                else:
                    log.warning(f"Git LFS install had issues: {lfs_result.stderr}")
                    self._update_step_success(
                        5, "Git LFS config written (install may be needed)"
                    )
            else:
                log.info(f"Git LFS skipped")
                self._update_step_success(5, "Git LFS skipped")

            # === STEP 6: Stage files ===
            self._add_step("Staging files…")
            log.info(f"Step 6: Staging files")
            stage_result = git_client.stage_all(folder_abs)
            if not stage_result.ok:
                log.error(f"Failed to stage files: {stage_result.stderr}")
                self._update_step_error(
                    6, f"Failed to stage files: {stage_result.stderr}"
                )
                return
            self._update_step_success(6, "Files staged")

            # === STEP 7: First commit ===
            self._add_step("Creating first commit…")
            log.info(f"Step 7: Creating first commit")
            commit_result = git_client.commit(folder_abs, f"Initial commit: {name}")
            if not commit_result.ok:
                if "MISSING_IDENTITY" in (commit_result.error_code or ""):
                    msg = (
                        "Git requires user.name and user.email.\n\n"
                        "Configure via:\n"
                        "  git config --global user.name 'Your Name'\n"
                        "  git config --global user.email 'your@example.com'\n\n"
                        "Then retry the wizard."
                    )
                    log.error(f"Commit failed - missing identity")
                    self._update_step_error(7, msg)
                else:
                    log.error(f"Commit failed: {commit_result.stderr}")
                    self._update_step_error(7, f"Commit failed: {commit_result.stderr}")
                return
            self._update_step_success(7, "Initial commit created")

            # === STEP 8: Add origin remote ===
            self._add_step("Setting up remote…")
            log.info(f"Step 8: Adding origin remote")
            clone_url = repo_info.clone_url
            remote_result = git_client.add_remote(folder_abs, "origin", clone_url)
            if not remote_result.ok:
                log.error(f"Failed to add remote: {remote_result.stderr}")
                self._update_step_error(8, remote_result.stderr)
                return
            self._update_step_success(8, "Origin remote added")

            # === STEP 9: Push to GitHub ===
            self._add_step("Pushing to GitHub…")
            log.info(f"Step 9: Pushing to GitHub")
            push_result = git_client.push(folder_abs, "origin")
            if not push_result.ok:
                if "AUTH_OR_PERMISSION" in (push_result.error_code or ""):
                    msg = (
                        "Authentication failed.\n\n"
                        "Ensure Git Credential Manager is configured and "
                        "you're signed into GitHub Desktop or the credential prompt."
                    )
                    log.error(f"Push failed - auth error")
                    self._update_step_error(9, msg)
                else:
                    log.error(f"Push failed: {push_result.stderr}")
                    self._update_step_error(9, f"Push failed: {push_result.stderr}")
                return
            log.info(f"Push successful")
            self._update_step_success(9, "Pushed to GitHub successfully")

            # === SUCCESS ===
            log.info(f"=== run_workflow COMPLETE - SUCCESS ===")
            self._parent_wizard._created_repo_path = folder_abs
            self._parent_wizard._created_repo_name = repo_info.full_name
            self._result_label.setText(
                f"✓ Success!\n\n"
                f"Repository: {repo_info.full_name}\n"
                f"Local folder: {folder_abs}\n\n"
                f"<a href='{repo_info.html_url}'>View on GitHub</a>"
            )
            self._result_label.setStyleSheet(
                "background: #e8f5e9; padding: 8px; border-radius: 4px; color: green;"
            )

            # Allow finishing
            self.setFinalPage(True)
            self._parent_wizard.button(QtWidgets.QWizard.FinishButton).setEnabled(True)

        except GitHubApiError as e:
            log.error(f"GitHub API error: {e}")
            self._add_step_error(0, str(e))
        except Exception as e:
            log.error(f"Workflow failed with exception: {type(e).__name__}: {e}")
            self._add_step_error(-1, str(e))

    def _add_step(self, message: str):
        """Add a new step to the progress list (in progress state)."""
        item = QtWidgets.QListWidgetItem(message)
        item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowRight))
        item.setForeground(QtGui.QColor("#1976d2"))
        self._progress_list.addItem(item)
        self._add_status(f"⟳ {message}")
        # Ensure the list scrolls to show the current item
        self._progress_list.scrollToItem(item)
        QtWidgets.QApplication.processEvents()

    def _update_step_success(self, index: int, message: str):
        """Mark step as completed with success message."""
        if 0 <= index < self._progress_list.count():
            item = self._progress_list.item(index)
            item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton))
            item.setForeground(QtGui.QColor("green"))
            item.setText(item.text() + " ✓")
        self._add_status(f"✓ {message}")
        QtWidgets.QApplication.processEvents()

    def _update_step_error(self, index: int, message: str):
        """Mark step as failed and show error."""
        if index >= 0 and index < self._progress_list.count():
            item = self._progress_list.item(index)
            item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton))
            item.setForeground(QtGui.QColor("red"))
            item.setText(item.text() + " ✗")
        self._add_status(f"✗ Error: {message}")
        QtWidgets.QApplication.processEvents()

    def _add_step_error(self, index: int, message: str):
        """Add and immediately mark a step as error."""
        self._add_step(message if index >= 0 else "Fatal error")
        if index >= 0:
            self._update_step_error(index, message)

    def _add_status(self, message: str):
        """Append message to status display."""
        current = self._status_text.toPlainText()
        if current:
            self._status_text.setText(current + "\n" + message)
        else:
            self._status_text.setText(message)
        # Scroll to bottom
        cursor = self._status_text.textCursor()
        cursor.movePosition(cursor.End)
        self._status_text.setTextCursor(cursor)

    def _show_recovery(self, context: str, folder: str, repo_url: str):
        """Show recovery steps for partial failure."""
        msg = (
            f"Repository was created on GitHub but local setup encountered an issue.\n\n"
            f"Recovery steps:\n"
            f"1. Delete the repository on GitHub: {repo_url}\n"
            f"   OR\n"
            f"2. Fix the issue and manually initialize {folder}\n"
            f"   Then run: git remote add origin {repo_url}\n"
            f"   And: git push -u origin main"
        )
        self._add_status(msg)

    def _set_step_active(self, index: int):
        """Mark step as in-progress."""
        if 0 <= index < self._progress_list.count():
            item = self._progress_list.item(index)
            item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowRight))
            item.setForeground(QtGui.QColor("#1976d2"))

    def _set_step_success(self, index: int):
        """Mark step as completed."""
        if 0 <= index < self._progress_list.count():
            item = self._progress_list.item(index)
            item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton))
            item.setForeground(QtGui.QColor("green"))

    def _set_step_error(self, index: int, message: str):
        """Mark step as failed with error message."""
        if index >= 0 and index < self._progress_list.count():
            item = self._progress_list.item(index)
            item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton))
            item.setForeground(QtGui.QColor("red"))
        self._add_status(f"✗ Error: {message}")

    def _add_status(self, message: str):
        """Append message to status display."""
        current = self._status_text.toPlainText()
        if current:
            self._status_text.setText(current + "\n" + message)
        else:
            self._status_text.setText(message)
        # Scroll to bottom
        cursor = self._status_text.textCursor()
        cursor.movePosition(cursor.End)
        self._status_text.setTextCursor(cursor)

    def _show_recovery(self, context: str, folder: str, repo_url: str):
        """Show recovery steps for partial failure."""
        msg = (
            f"Repository was created on GitHub but local setup encountered an issue.\n\n"
            f"Recovery steps:\n"
            f"1. Delete the repository on GitHub: {repo_url}\n"
            f"   OR\n"
            f"2. Fix the issue and manually initialize {folder}\n"
            f"   Then run: git remote add origin {repo_url}\n"
            f"   And: git push -u origin main"
        )
        self._add_status(msg)
