# -*- coding: utf-8 -*-
"""
GitPDM Panel UI Module
Sprint 1: Main dockable panel with git operations
"""

# Qt compatibility layer - try PySide6 first, then PySide2
try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError as e:
        raise ImportError(
            "Neither PySide6 nor PySide2 found. "
            "FreeCAD installation may be incomplete."
        ) from e

from freecad_gitpdm.core import log, settings, jobs
from freecad_gitpdm.git import client


class GitPDMDockWidget(QtWidgets.QDockWidget):
    """
    Main GitPDM dock widget panel
    Sprint 1: Git status, validation, and controls
    """

    def __init__(self):
        super().__init__()
        self.setObjectName("GitPDM_DockWidget")
        self.setWindowTitle("Git PDM")
        self.setMinimumWidth(300)

        # Initialize git client and job runner
        self._git_client = client.GitClient()
        self._job_runner = jobs.get_job_runner()
        self._job_runner.job_finished.connect(self._on_job_finished)

        # Create main widget and layout
        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)

        # Build UI sections
        self._build_git_check_section(main_layout)
        self._build_repo_selector(main_layout)
        self._build_status_section(main_layout)
        self._build_changes_section(main_layout)
        self._build_buttons_section(main_layout)
        self._build_repo_browser_section(main_layout)

        # Add stretch at bottom to push everything up
        main_layout.addStretch()

        # Load saved repo path
        self._load_saved_repo_path()

        # Perform initial git check
        self._check_git_available()

        log.info("GitPDM dock panel initialized (Sprint 1)")

    def _build_git_check_section(self, layout):
        """
        Build the git availability check section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("System")
        group_layout = QtWidgets.QFormLayout()
        group.setLayout(group_layout)

        # Git availability
        self.git_label = QtWidgets.QLabel("Checking...")
        self.git_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        group_layout.addRow("Git:", self.git_label)

        layout.addWidget(group)

    def _check_git_available(self):
        """Check if git is available on system"""
        is_available = self._git_client.is_git_available()
        if is_available:
            version = self._git_client.git_version()
            self.git_label.setText(f"OK ({version})")
            self.git_label.setStyleSheet("color: green;")
        else:
            self.git_label.setText("Not found")
            self.git_label.setStyleSheet("color: red;")
            log.warning("Git not available on PATH")

    def _build_repo_selector(self, layout):
        """
        Build the repository selector section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("Repository")
        group_layout = QtWidgets.QVBoxLayout()
        group.setLayout(group_layout)

        # Repo path row
        path_layout = QtWidgets.QHBoxLayout()
        self.repo_path_field = QtWidgets.QLineEdit()
        self.repo_path_field.setPlaceholderText(
            "Select repository folder..."
        )
        self.repo_path_field.editingFinished.connect(
            self._on_repo_path_editing_finished
        )
        path_layout.addWidget(self.repo_path_field)

        browse_btn = QtWidgets.QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_clicked)
        path_layout.addWidget(browse_btn)

        group_layout.addLayout(path_layout)

        # Repo root label (resolved path, read-only)
        repo_root_layout = QtWidgets.QHBoxLayout()
        repo_root_layout.addWidget(QtWidgets.QLabel("Root:"))
        self.repo_root_label = QtWidgets.QLabel("—")
        self.repo_root_label.setStyleSheet(
            "color: gray; font-size: 10px;"
        )
        self.repo_root_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self.repo_root_label.setWordWrap(True)
        repo_root_layout.addWidget(self.repo_root_label)
        group_layout.addLayout(repo_root_layout)

        # Validation status row
        validation_layout = QtWidgets.QHBoxLayout()
        validation_layout.addWidget(QtWidgets.QLabel("Validate:"))
        self.validate_label = QtWidgets.QLabel("Not checked")
        self.validate_label.setStyleSheet(
            "color: gray; font-style: italic;"
        )
        validation_layout.addWidget(self.validate_label)
        validation_layout.addStretch()

        refresh_btn = QtWidgets.QPushButton("Refresh Status")
        refresh_btn.clicked.connect(self._on_refresh_clicked)
        validation_layout.addWidget(refresh_btn)

        group_layout.addLayout(validation_layout)

        layout.addWidget(group)

    def _build_status_section(self, layout):
        """
        Build the status information section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("Status")
        group_layout = QtWidgets.QFormLayout()
        group.setLayout(group_layout)

        # Branch label
        self.branch_label = QtWidgets.QLabel("—")
        self.branch_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        group_layout.addRow("Branch:", self.branch_label)

        # Working tree status label
        self.working_tree_label = QtWidgets.QLabel("—")
        self.working_tree_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        group_layout.addRow("Working tree:", self.working_tree_label)

        layout.addWidget(group)

    def _build_changes_section(self, layout):
        """
        Build the changes list section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("Changes")
        group_layout = QtWidgets.QVBoxLayout()
        group.setLayout(group_layout)

        # Info label
        info_label = QtWidgets.QLabel(
            "Modified, staged, and untracked files will appear here."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        group_layout.addWidget(info_label)

        # Changes list widget (placeholder)
        self.changes_list = QtWidgets.QListWidget()
        self.changes_list.setMaximumHeight(150)
        self.changes_list.setEnabled(False)  # Disabled in Sprint 0
        group_layout.addWidget(self.changes_list)

        layout.addWidget(group)

    def _build_buttons_section(self, layout):
        """
        Build the action buttons section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("Actions")
        group_layout = QtWidgets.QVBoxLayout()
        group.setLayout(group_layout)

        # First row: Fetch, Pull
        row1_layout = QtWidgets.QHBoxLayout()
        self.fetch_btn = QtWidgets.QPushButton("Fetch")
        self.fetch_btn.setEnabled(False)
        row1_layout.addWidget(self.fetch_btn)

        self.pull_btn = QtWidgets.QPushButton("Pull")
        self.pull_btn.setEnabled(False)
        row1_layout.addWidget(self.pull_btn)

        group_layout.addLayout(row1_layout)

        # Second row: Commit, Push
        row2_layout = QtWidgets.QHBoxLayout()
        self.commit_btn = QtWidgets.QPushButton("Commit")
        self.commit_btn.setEnabled(False)
        row2_layout.addWidget(self.commit_btn)

        self.push_btn = QtWidgets.QPushButton("Push")
        self.push_btn.setEnabled(False)
        row2_layout.addWidget(self.push_btn)

        group_layout.addLayout(row2_layout)

        # Third row: Publish
        self.publish_btn = QtWidgets.QPushButton("Publish Branch")
        self.publish_btn.setEnabled(False)
        group_layout.addWidget(self.publish_btn)

        layout.addWidget(group)

    def _build_repo_browser_section(self, layout):
        """
        Build the repository browser section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("Repository Browser")
        group_layout = QtWidgets.QVBoxLayout()
        group.setLayout(group_layout)

        # Info label
        info_label = QtWidgets.QLabel(
            "Browse commits, branches, and tags here (coming soon)."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        group_layout.addWidget(info_label)

        # Tree/list widget placeholder
        self.repo_tree = QtWidgets.QTreeWidget()
        self.repo_tree.setHeaderLabels(["Item", "Details"])
        self.repo_tree.setMaximumHeight(100)
        self.repo_tree.setEnabled(False)  # Disabled in Sprint 0
        group_layout.addWidget(self.repo_tree)

        layout.addWidget(group)

    def _on_browse_clicked(self):
        """
        Handle Browse button click - open folder dialog
        """
        current_path = self.repo_path_field.text()
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Repository Folder",
            current_path if current_path else "",
            QtWidgets.QFileDialog.ShowDirsOnly
        )

        if folder:
            self.repo_path_field.setText(folder)
            # Trigger validation
            self._validate_repo_path(folder)
            log.info(f"Selected repo folder: {folder}")

    def _on_repo_path_editing_finished(self):
        """
        Handle repo path field editing finished event.
        Only validate on explicit edits, not programmatic changes.
        """
        text = self.repo_path_field.text()
        if text:
            self._validate_repo_path(text)

    def _validate_repo_path(self, path):
        """
        Validate that path is inside a git repository.
        Run validation in background to keep UI responsive.
        
        Args:
            path: str - path to validate
        """
        if not path:
            self.validate_label.setText("Not checked")
            self.validate_label.setStyleSheet(
                "color: gray; font-style: italic;"
            )
            self.repo_root_label.setText("—")
            self.branch_label.setText("—")
            self.working_tree_label.setText("—")
            return

        # Show "Checking..." status
        self.validate_label.setText("Checking…")
        self.validate_label.setStyleSheet(
            "color: orange; font-style: italic;"
        )

        # Run validation in background
        repo_root = self._git_client.get_repo_root(path)

        if repo_root:
            # Valid repo
            self.validate_label.setText("OK")
            self.validate_label.setStyleSheet("color: green;")
            self.repo_root_label.setText(repo_root)

            # Save the valid path
            settings.save_repo_path(path)

            # Fetch branch and status
            self._fetch_branch_and_status(repo_root)
            log.info(f"Validated repo: {repo_root}")
        else:
            # Invalid repo
            self.validate_label.setText("Invalid")
            self.validate_label.setStyleSheet("color: red;")
            self.repo_root_label.setText("—")
            self.branch_label.setText("—")
            self.working_tree_label.setText("—")
            # Do not overwrite saved path - just show typed text in UI
            log.warning(
                f"Not a git repository: {path}"
            )

    def _fetch_branch_and_status(self, repo_root):
        """
        Fetch current branch and working tree status for repo_root.
        
        Args:
            repo_root: str - repository root path
        """
        # Get branch synchronously (fast operation)
        branch = self._git_client.current_branch(repo_root)
        self.branch_label.setText(branch)

        # Get status synchronously (fast operation)
        status = self._git_client.status_summary(repo_root)
        self._display_working_tree_status(status)

    def _display_working_tree_status(self, status):
        """
        Display working tree status in UI
        
        Args:
            status: dict - status summary from GitClient
        """
        if status["is_clean"]:
            self.working_tree_label.setText("Clean")
            self.working_tree_label.setStyleSheet("color: green;")
        else:
            parts = []
            if status["modified"] > 0:
                parts.append(f"M:{status['modified']}")
            if status["added"] > 0:
                parts.append(f"A:{status['added']}")
            if status["deleted"] > 0:
                parts.append(f"D:{status['deleted']}")
            if status["untracked"] > 0:
                parts.append(f"U:{status['untracked']}")

            status_str = "Dirty (" + " ".join(parts) + ")"
            self.working_tree_label.setText(status_str)
            self.working_tree_label.setStyleSheet("color: orange;")

    def _on_refresh_clicked(self):
        """
        Handle Refresh Status button click.
        Re-validate current repo path and refresh status.
        """
        current_path = self.repo_path_field.text()
        if current_path:
            self._validate_repo_path(current_path)
        else:
            log.warning("No repository path set")

    def _on_job_finished(self, job):
        """
        Callback when a background job finishes.
        Currently not used in Sprint 1 (synchronous operations),
        but present for future Sprint 2+ enhancements.
        
        Args:
            job: dict - job result descriptor
        """
        log.debug(f"Job finished: {job.get('type')}")

    def _load_saved_repo_path(self):
        """
        Load the saved repository path from settings and validate it.
        """
        saved_path = settings.load_repo_path()
        if saved_path:
            self.repo_path_field.blockSignals(True)
            self.repo_path_field.setText(saved_path)
            self.repo_path_field.blockSignals(False)
            # Auto-validate on load
            self._validate_repo_path(saved_path)
            log.info(
                f"Restored repo path from settings: {saved_path}"
            )
