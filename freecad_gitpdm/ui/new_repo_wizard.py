# -*- coding: utf-8 -*-
"""
GitPDM New Repository Wizard
Sprint OAUTH-4: Dialog to create GitHub repo + local scaffold + push
Sprint OAUTH-6: Error handling, token invalidation detection
Phase G4: provider abstraction — GitHub (create via API) or a generic git
remote (paste a URL you already created). Capability flags decide which
path runs; UI never offers an action the active provider can't perform.

Guides user through:
  1. Choosing a provider (GitHub, or another git remote)
  2. Selecting local folder
  3. Entering repo name + visibility (GitHub) or remote URL (generic)
  4. Choosing scaffolding options
  5. Executing creation steps with progress
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
from typing import Optional, Callable

from freecad_gitpdm.core import log, scaffold, provider_config
from freecad_gitpdm.providers.base import BaseProvider, GenericProvider, RemoteRepoInfo
from freecad_gitpdm.providers.github.api_client import GitHubApiClient
from freecad_gitpdm.providers.github.errors import GitHubApiError
from freecad_gitpdm.providers.github.provider import GitHubProvider
from freecad_gitpdm.git import client as git_client_module


class NewRepoWizard(QtWidgets.QWizard):
    """Multi-step wizard to create a new repo (via a provider's API, or by
    pointing at an existing remote) plus a local scaffold."""

    def __init__(
        self,
        api_client: Optional[GitHubApiClient] = None,
        provider: Optional[BaseProvider] = None,
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

        # Wizard steps. Provider choice comes first: it decides which
        # fields the input page shows and which workflow branch runs.
        self._provider_page = _ProviderPage(
            self,
            initial_provider=provider or GitHubProvider(),
            github_available=api_client is not None,
        )
        self._input_page = _InputPage(self)
        self._options_page = _OptionsPage(self)
        self._progress_page = _ProgressPage(self)

        self.addPage(self._provider_page)
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
        """Return name of created repo, or None if failed."""
        return self._created_repo_name

    def selected_provider(self) -> BaseProvider:
        return self._provider_page.get_provider()


class _ProviderPage(QtWidgets.QWizardPage):
    """Page 1: choose which provider owns the new repository.

    GitHub can create the repo via its API; any other option is a
    generic git remote the user already created elsewhere (browser,
    another tool) and pastes the URL for on the next page. UI never
    offers the GitHub option when there's no way to call its API.
    """

    def __init__(self, parent, initial_provider: BaseProvider, github_available: bool):
        super().__init__(parent)
        self.setTitle("Choose a Provider")
        self.setSubTitle("Where should this repository live?")

        self._github_available = github_available

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self._github_radio = QtWidgets.QRadioButton(
            "GitHub — create the repository automatically"
        )
        self._generic_radio = QtWidgets.QRadioButton(
            "Another git remote — I'll paste a URL I already have"
        )
        layout.addWidget(self._github_radio)
        layout.addWidget(self._generic_radio)

        self._hint_label = QtWidgets.QLabel("")
        self._hint_label.setWordWrap(True)
        self._hint_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self._hint_label)
        layout.addStretch()

        if github_available:
            wants_github = initial_provider.capabilities.supports_repo_creation
            self._github_radio.setChecked(wants_github)
            self._generic_radio.setChecked(not wants_github)
        else:
            self._github_radio.setEnabled(False)
            self._generic_radio.setChecked(True)
            self._hint_label.setText(
                "Connect GitHub from the panel first to create a repository "
                "automatically here. You can still continue with another "
                "git remote."
            )

    def get_provider(self) -> BaseProvider:
        if self._github_radio.isChecked() and self._github_available:
            return GitHubProvider()
        return GenericProvider()


class _InputPage(QtWidgets.QWizardPage):
    """Page 2: select folder, name, and provider-specific details."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle("Repository Details")
        self.setSubTitle("Choose a folder and name for your new repository")

        self._parent_wizard = parent

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

        # Visibility (GitHub only)
        self._private_check = QtWidgets.QCheckBox("Private (not visible to public)")
        self._private_row_label = QtWidgets.QLabel("Visibility:")
        layout.addRow(self._private_row_label, self._private_check)

        # Description (GitHub only)
        self._desc_edit = QtWidgets.QLineEdit()
        self._desc_edit.setPlaceholderText(
            "Optional description (can be edited on GitHub)"
        )
        self._desc_row_label = QtWidgets.QLabel("Description:")
        layout.addRow(self._desc_row_label, self._desc_edit)

        # Remote URL (generic provider only)
        self._remote_url_edit = QtWidgets.QLineEdit()
        self._remote_url_edit.setPlaceholderText(
            "e.g., https://example.com/you/repo.git"
        )
        self._remote_url_edit.textChanged.connect(self._on_field_changed)
        self._remote_url_row_label = QtWidgets.QLabel("Remote URL:")
        layout.addRow(self._remote_url_row_label, self._remote_url_edit)

        # Status label
        self._status_label = QtWidgets.QLabel("")
        self._status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addRow("", self._status_label)

    def initializePage(self):
        """Show/hide provider-specific fields based on the chosen provider."""
        super().initializePage()
        provider = self._parent_wizard.selected_provider()
        can_create = provider.capabilities.supports_repo_creation

        self._private_check.setVisible(can_create)
        self._private_row_label.setVisible(can_create)
        self._desc_edit.setVisible(can_create)
        self._desc_row_label.setVisible(can_create)

        self._remote_url_edit.setVisible(not can_create)
        self._remote_url_row_label.setVisible(not can_create)
        self.completeChanged.emit()

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
        """Return dict with folder, name, private, description, remote_url."""
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
            "remote_url": self._remote_url_edit.text().strip() or None,
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

        # Generic provider needs a remote URL to push to; GitHub creates one.
        provider = self._parent_wizard.selected_provider()
        if not provider.capabilities.supports_repo_creation:
            if not self._remote_url_edit.text().strip():
                self._status_label.setText(
                    "Enter the URL of a git remote you already created."
                )
                return False

        # All checks passed
        self._status_label.setText(f"Will create: {name}/")
        return True


class _OptionsPage(QtWidgets.QWizardPage):
    """Page 3: Configure scaffolding and LFS options."""

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
    """Page 4: Execute creation steps with real-time progress display."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle("Creating Repository")
        self.setSubTitle("Setting up your repository…")

        self._parent_wizard = parent
        self._workflow_running = False
        self._api_client = None
        self._git_client = None
        self._provider = None
        self._inputs = None
        self._options = None
        self._step_index = -1  # index of the most recently added step

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
            self._provider = self._parent_wizard.selected_provider()
            self._inputs = self._parent_wizard._input_page.get_inputs()
            self._options = self._parent_wizard._options_page.get_options()

            log.info(f"Provider: {self._provider.provider_id}")
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
        self._step_index = -1

        log.info(f"Inputs: {self._inputs}")
        log.info(f"Options: {self._options}")

        self.run_workflow(
            self._provider,
            self._api_client,
            self._git_client,
            self._inputs,
            self._options,
        )

    def run_workflow(
        self,
        provider: BaseProvider,
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
        remote_url = inputs.get("remote_url")
        enable_scaffold = options["enable_scaffold"]
        enable_lfs = options["enable_lfs"]

        can_create_remotely = provider.capabilities.supports_repo_creation

        if can_create_remotely and not api_client:
            self._add_step_error(-1, "API client not available")
            return
        if not can_create_remotely and not remote_url:
            self._add_step_error(-1, "Remote URL not provided")
            return

        # Normalize the path to handle spaces and special characters
        folder_abs = os.path.normpath(os.path.abspath(folder))
        log.info("=== run_workflow START ===")
        log.info(f"folder input: {folder}")
        log.info(f"folder_abs after normpath: {folder_abs}")
        log.info(f"name: {name}")

        # Disable Finish button during workflow
        self._parent_wizard.button(QtWidgets.QWizard.FinishButton).setEnabled(False)
        self._parent_wizard.button(QtWidgets.QWizard.BackButton).setEnabled(False)

        try:
            # Check parent directory exists BEFORE trying to create anything
            parent_dir = os.path.dirname(folder_abs)
            log.info(f"Parent directory: {parent_dir}")
            log.info(f"Parent exists: {os.path.exists(parent_dir)}")

            if not os.path.exists(parent_dir):
                msg = f"Parent directory does not exist: {parent_dir}"
                log.error(msg)
                self._add_step(f"Creating folder: {name}/")
                self._update_step_error(self._step_index, msg)
                return

            # === Create the target folder ===
            self._add_step(f"Creating folder: {name}/")
            log.info(f"About to create folder at {folder_abs}")
            log.info(f"  Folder exists before: {os.path.exists(folder_abs)}")

            # Ensure the folder doesn't already exist to avoid conflicts
            if os.path.exists(folder_abs) and not os.path.isdir(folder_abs):
                msg = f"Path exists but is not a folder: {folder_abs}"
                log.error(msg)
                self._update_step_error(self._step_index, msg)
                return

            # Create folder
            if not os.path.exists(folder_abs):
                log.info("Folder doesn't exist, creating it...")
                try:
                    os.makedirs(folder_abs, exist_ok=True)
                    if not os.path.isdir(folder_abs):
                        msg = f"Failed to create directory (isdir=False): {folder_abs}"
                        log.error(msg)
                        self._update_step_error(self._step_index, msg)
                        return
                    log.info("Folder created successfully")
                    self._update_step_success(
                        self._step_index, f"Created: {folder_abs}"
                    )
                except PermissionError as e:
                    msg = f"Permission denied creating folder: {folder_abs}\nError: {e}"
                    log.error(msg)
                    self._update_step_error(self._step_index, msg)
                    return
                except FileExistsError as e:
                    msg = f"File exists error: {folder_abs}\nError: {e}"
                    log.error(msg)
                    self._update_step_error(self._step_index, msg)
                    return
                except OSError as e:
                    msg = f"OS Error creating folder: {e}"
                    log.error(msg)
                    self._update_step_error(self._step_index, msg)
                    return
                except Exception as e:
                    msg = f"Unexpected error creating folder: {type(e).__name__}: {e}"
                    log.error(msg)
                    self._update_step_error(self._step_index, msg)
                    return
            else:
                log.info("Folder already exists, using it")
                if not os.path.isdir(folder_abs):
                    self._update_step_error(
                        self._step_index,
                        f"Path exists but is not a folder: {folder_abs}",
                    )
                    return
                self._update_step_success(self._step_index, "Using existing folder")

            # === Create the remote repository ===
            if can_create_remotely:
                self._add_step(f"Creating repository on {provider.provider_id}…")
                log.info(f"Creating remote repo via {provider.provider_id}")
                try:
                    repo_info = provider.create_remote_repo(
                        api_client, name=name, private=private, description=description
                    )
                    log.info(f"Remote repo created: {repo_info.full_name}")
                    self._update_step_success(
                        self._step_index, f"Repository created: {repo_info.full_name}"
                    )
                except GitHubApiError as e:
                    # Session expiry needs a distinct UX (reconnect prompt).
                    if getattr(e, "code", None) == "UNAUTHORIZED":
                        log.error(f"Provider session expired: {e}")
                        self._update_step_error(
                            self._step_index, "Session expired. Please reconnect."
                        )
                        if self._parent_wizard._on_session_expired:
                            self._parent_wizard._on_session_expired()
                        return

                    log.error(f"Remote repo creation failed: {e}")
                    self._update_step_error(self._step_index, str(e))
                    return
            else:
                # Generic provider: the user already created the remote and
                # pasted its URL — nothing to call over the network here.
                repo_info = RemoteRepoInfo(
                    full_name=name,
                    html_url=remote_url,
                    clone_url=remote_url,
                    default_branch=None,
                )

            # === Init local repo ===
            self._add_step("Initializing local git…")
            log.info(f"Initializing git in {folder_abs}")

            if not os.path.isdir(folder_abs):
                msg = f"Folder disappeared before git init: {folder_abs}"
                log.error(msg)
                self._update_step_error(self._step_index, msg)
                self._show_recovery(folder_abs, repo_info.html_url)
                return

            init_result = git_client.init_repo(folder_abs)
            log.info(
                f"Git init result: ok={init_result.ok}, stderr={init_result.stderr}"
            )
            if not init_result.ok:
                self._update_step_error(self._step_index, init_result.stderr)
                self._show_recovery(folder_abs, repo_info.html_url)
                return
            self._update_step_success(self._step_index, "Local git initialized")

            # === Write scaffolding ===
            self._add_step("Writing scaffolding…")
            log.info("Writing scaffolding")
            if enable_scaffold:
                try:
                    scaffold.apply_scaffold(
                        folder_abs, enable_lfs=enable_lfs, write_preset=True
                    )
                    log.info("Scaffolding created successfully")
                    self._update_step_success(
                        self._step_index,
                        "Scaffolding created (cad/, previews/, .freecad-pdm/)",
                    )
                except OSError as e:
                    log.error(f"Scaffolding failed: {e}")
                    self._update_step_error(self._step_index, str(e))
                    return
            else:
                log.info("Scaffolding skipped")
                self._update_step_success(self._step_index, "Scaffolding skipped")

            # Persist the provider choice for this repo (Phase G4) so
            # future sessions know which provider it belongs to.
            try:
                provider_config.set_provider_config(folder_abs, provider.provider_id)
            except (OSError, ValueError) as e:
                log.warning(f"Could not persist provider config: {e}")

            # === Set default branch ===
            self._add_step("Setting default branch…")
            log.info("Setting default branch")
            branch_result = git_client.set_default_branch(folder_abs, "main")
            if not branch_result.ok:
                log.warning(f"Failed to set default branch: {branch_result.stderr}")
            self._update_step_success(self._step_index, "Default branch set to 'main'")

            # === Configure LFS ===
            self._add_step("Configuring Git LFS…")
            log.info("Configuring Git LFS")
            if enable_lfs:
                lfs_result = git_client.lfs_install()
                if lfs_result.ok:
                    log.info("Git LFS configured")
                    self._update_step_success(self._step_index, "Git LFS configured")
                else:
                    log.warning(f"Git LFS install had issues: {lfs_result.stderr}")
                    self._update_step_success(
                        self._step_index,
                        "Git LFS config written (install may be needed)",
                    )
            else:
                log.info("Git LFS skipped")
                self._update_step_success(self._step_index, "Git LFS skipped")

            # === Stage files ===
            self._add_step("Staging files…")
            log.info("Staging files")
            stage_result = git_client.stage_all(folder_abs)
            if not stage_result.ok:
                log.error(f"Failed to stage files: {stage_result.stderr}")
                self._update_step_error(
                    self._step_index, f"Failed to stage files: {stage_result.stderr}"
                )
                return
            self._update_step_success(self._step_index, "Files staged")

            # === First commit ===
            self._add_step("Creating first commit…")
            log.info("Creating first commit")
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
                    log.error("Commit failed - missing identity")
                    self._update_step_error(self._step_index, msg)
                else:
                    log.error(f"Commit failed: {commit_result.stderr}")
                    self._update_step_error(
                        self._step_index, f"Commit failed: {commit_result.stderr}"
                    )
                return
            self._update_step_success(self._step_index, "Initial commit created")

            # === Add origin remote ===
            self._add_step("Setting up remote…")
            log.info("Adding origin remote")
            clone_url = repo_info.clone_url
            remote_result = git_client.add_remote(folder_abs, "origin", clone_url)
            if not remote_result.ok:
                log.error(f"Failed to add remote: {remote_result.stderr}")
                self._update_step_error(self._step_index, remote_result.stderr)
                return
            self._update_step_success(self._step_index, "Origin remote added")

            # === Push ===
            self._add_step("Pushing to remote…")
            log.info("Pushing to remote")
            push_result = git_client.push(folder_abs, "origin")
            if not push_result.ok:
                if "AUTH_OR_PERMISSION" in (push_result.error_code or ""):
                    msg = (
                        "Authentication failed.\n\n"
                        "Ensure Git Credential Manager is configured and "
                        "you're signed into GitHub Desktop or the credential prompt."
                    )
                    log.error("Push failed - auth error")
                    self._update_step_error(self._step_index, msg)
                else:
                    log.error(f"Push failed: {push_result.stderr}")
                    self._update_step_error(
                        self._step_index, f"Push failed: {push_result.stderr}"
                    )
                return
            log.info("Push successful")
            self._update_step_success(self._step_index, "Pushed successfully")

            # === SUCCESS ===
            log.info("=== run_workflow COMPLETE - SUCCESS ===")
            self._parent_wizard._created_repo_path = folder_abs
            self._parent_wizard._created_repo_name = repo_info.full_name
            html_link = (
                f"<a href='{repo_info.html_url}'>View repository</a>"
                if repo_info.html_url
                else ""
            )
            self._result_label.setText(
                f"✓ Success!\n\n"
                f"Repository: {repo_info.full_name}\n"
                f"Local folder: {folder_abs}\n\n"
                f"{html_link}"
            )
            self._result_label.setStyleSheet(
                "background: #e8f5e9; padding: 8px; border-radius: 4px; color: green;"
            )

            # Allow finishing
            self.setFinalPage(True)
            self._parent_wizard.button(QtWidgets.QWizard.FinishButton).setEnabled(True)
            self._parent_wizard.button(QtWidgets.QWizard.BackButton).setEnabled(True)

        except GitHubApiError as e:
            log.error(f"Provider API error: {e}")
            self._add_step_error(-1, str(e))
            self._parent_wizard.button(QtWidgets.QWizard.BackButton).setEnabled(True)
        except Exception as e:
            log.error(f"Workflow failed with exception: {type(e).__name__}: {e}")
            self._add_step_error(-1, str(e))
            self._parent_wizard.button(QtWidgets.QWizard.BackButton).setEnabled(True)

    def _add_step(self, message: str):
        """Add a new step to the progress list (in progress state)."""
        item = QtWidgets.QListWidgetItem(message)
        item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowRight))
        item.setForeground(QtGui.QColor("#1976d2"))
        self._progress_list.addItem(item)
        self._step_index = self._progress_list.count() - 1
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
        if 0 <= index < self._progress_list.count():
            item = self._progress_list.item(index)
            item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogNoButton))
            item.setForeground(QtGui.QColor("red"))
            item.setText(item.text() + " ✗")
        self._add_status(f"✗ Error: {message}")
        QtWidgets.QApplication.processEvents()

    def _add_step_error(self, index: int, message: str):
        """Add and immediately mark a step as error."""
        self._add_step(message if index >= 0 else "Fatal error")
        self._update_step_error(self._step_index, message)

    def _add_status(self, message: str):
        """Append message to status display."""
        current = self._status_text.toPlainText()
        if current:
            self._status_text.setText(current + "\n" + message)
        else:
            self._status_text.setText(message)
        # Scroll to bottom
        cursor = self._status_text.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        self._status_text.setTextCursor(cursor)

    def _show_recovery(self, folder: str, repo_url: str):
        """Show recovery steps for partial failure."""
        msg = (
            "The remote repository exists but local setup encountered an issue.\n\n"
            "Recovery steps:\n"
            f"1. Delete the remote repository if it's no longer wanted: {repo_url}\n"
            "   OR\n"
            f"2. Fix the issue and manually initialize {folder}\n"
            f"   Then run: git remote add origin {repo_url}\n"
            "   And: git push -u origin main"
        )
        self._add_status(msg)
