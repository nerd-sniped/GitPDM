# -*- coding: utf-8 -*-
"""
GitPDM Panel UI Module
Sprint 2: Main dockable panel with git operations + fetch support
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
from freecad_gitpdm.ui import dialogs


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

        # State tracking
        self._current_repo_root = None
        self._is_fetching = False
        self._is_pulling = False
        self._is_committing = False
        self._is_pushing = False
        self._upstream_ref = None
        self._ahead_count = 0
        self._behind_count = 0
        self._file_statuses = []
        self._pending_commit_message = ""
        self._busy_timer = QtCore.QTimer(self)
        self._busy_timer.setInterval(5000)
        self._busy_timer.timeout.connect(self._on_busy_timer_tick)
        self._busy_label = ""

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

        # Load remote name
        self._remote_name = settings.load_remote_name()

        # Load saved repo path
        self._load_saved_repo_path()

        # Perform initial git check
        self._check_git_available()

        log.info("GitPDM dock panel initialized (Sprint 2)")

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
        group_layout = QtWidgets.QVBoxLayout()
        group.setLayout(group_layout)

        # Operation status header (shows Pulling… / Fetching… / Synced)
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addWidget(QtWidgets.QLabel("Operation:"))
        self.operation_status_label = QtWidgets.QLabel("Ready")
        self.operation_status_label.setStyleSheet(
            "color: gray; font-size: 9px;"
        )
        self.operation_status_label.setAlignment(QtCore.Qt.AlignRight)
        header_layout.addWidget(self.operation_status_label)
        group_layout.addLayout(header_layout)

        # Form-style fields
        form_layout = QtWidgets.QFormLayout()

        # Branch label
        self.branch_label = QtWidgets.QLabel("—")
        self.branch_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        form_layout.addRow("Branch:", self.branch_label)

        # Working tree status label
        self.working_tree_label = QtWidgets.QLabel("—")
        self.working_tree_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        form_layout.addRow("Working tree:", self.working_tree_label)

        # Upstream label (Sprint 2)
        self.upstream_label = QtWidgets.QLabel("—")
        self.upstream_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        form_layout.addRow("Upstream:", self.upstream_label)

        # Ahead/Behind label (Sprint 2)
        self.ahead_behind_label = QtWidgets.QLabel("—")
        self.ahead_behind_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        form_layout.addRow("Ahead/Behind:",
                           self.ahead_behind_label)

        # Last fetch label (Sprint 2)
        self.last_fetch_label = QtWidgets.QLabel("—")
        self.last_fetch_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        form_layout.addRow("Last fetch:", self.last_fetch_label)

        group_layout.addLayout(form_layout)

        # Error/message area (Sprint 2)
        self.status_message_label = QtWidgets.QLabel("")
        self.status_message_label.setWordWrap(True)
        self.status_message_label.setStyleSheet(
            "color: red; font-size: 10px;"
        )
        self.status_message_label.hide()
        group_layout.addWidget(self.status_message_label)

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

        info_label = QtWidgets.QLabel(
            "Working tree changes detected by git status." 
            " Use Stage all to include them in commits."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        group_layout.addWidget(info_label)

        self.changes_list = QtWidgets.QListWidget()
        self.changes_list.setMaximumHeight(180)
        self.changes_list.setEnabled(False)
        group_layout.addWidget(self.changes_list)

        stage_layout = QtWidgets.QHBoxLayout()
        self.stage_all_checkbox = QtWidgets.QCheckBox("Stage all changes")
        self.stage_all_checkbox.setChecked(True)
        self.stage_all_checkbox.setEnabled(False)
        self.stage_all_checkbox.stateChanged.connect(
            self._update_button_states
        )
        stage_layout.addWidget(self.stage_all_checkbox)
        stage_layout.addStretch()
        group_layout.addLayout(stage_layout)

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

        row1_layout = QtWidgets.QHBoxLayout()
        self.fetch_btn = QtWidgets.QPushButton("Fetch")
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.clicked.connect(self._on_fetch_clicked)
        row1_layout.addWidget(self.fetch_btn)

        self.pull_btn = QtWidgets.QPushButton("Pull")
        self.pull_btn.setEnabled(False)
        self.pull_btn.clicked.connect(self._on_pull_clicked)
        row1_layout.addWidget(self.pull_btn)

        group_layout.addLayout(row1_layout)

        msg_label = QtWidgets.QLabel("Commit message:")
        msg_label.setStyleSheet("font-weight: bold;")
        group_layout.addWidget(msg_label)

        self.commit_message = QtWidgets.QPlainTextEdit()
        self.commit_message.setPlaceholderText(
            "Describe your changes before committing"
        )
        self.commit_message.setMaximumHeight(90)
        self.commit_message.textChanged.connect(
            self._on_commit_message_changed
        )
        group_layout.addWidget(self.commit_message)

        row2_layout = QtWidgets.QHBoxLayout()
        self.commit_btn = QtWidgets.QPushButton("Commit")
        self.commit_btn.setEnabled(False)
        self.commit_btn.clicked.connect(self._on_commit_clicked)
        row2_layout.addWidget(self.commit_btn)

        self.push_btn = QtWidgets.QPushButton("Push")
        self.push_btn.setEnabled(False)
        self.push_btn.clicked.connect(self._on_push_clicked)
        row2_layout.addWidget(self.push_btn)

        group_layout.addLayout(row2_layout)

        self.publish_btn = QtWidgets.QPushButton("Publish Branch")
        self.publish_btn.setEnabled(False)
        group_layout.addWidget(self.publish_btn)

        # Busy indicator (indeterminate)
        self.busy_bar = QtWidgets.QProgressBar()
        self.busy_bar.setRange(0, 0)
        self.busy_bar.setFixedHeight(8)
        self.busy_bar.hide()
        group_layout.addWidget(self.busy_bar)

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
            self.upstream_label.setText("—")
            self.ahead_behind_label.setText("—")
            self._update_button_states()
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
            self._current_repo_root = repo_root

            # Fetch branch and status
            self._fetch_branch_and_status(repo_root)
            
            # Update button states
            self._update_button_states()
            
            log.info(f"Validated repo: {repo_root}")
        else:
            # Invalid repo
            self.validate_label.setText("Invalid")
            self.validate_label.setStyleSheet("color: red;")
            self.repo_root_label.setText("—")
            self.branch_label.setText("—")
            self.working_tree_label.setText("—")
            self.upstream_label.setText("—")
            self.ahead_behind_label.setText("—")
            self._current_repo_root = None
            self._update_button_states()
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
        branch = self._git_client.current_branch(repo_root)
        self.branch_label.setText(branch)

        self._refresh_status_views(repo_root)

        self._update_upstream_info(repo_root)

        # Display last fetch time
        self._display_last_fetch()

    def _update_upstream_info(self, repo_root):
        """
        Update upstream ref and ahead/behind counts
        
        Args:
            repo_root: str - repository root path
        """
        self._ahead_count = 0
        self._behind_count = 0
        
        has_remote = self._git_client.has_remote(
            repo_root, self._remote_name
        )
        
        if not has_remote:
            self.upstream_label.setText("(no remote)")
            self.upstream_label.setStyleSheet("color: gray;")
            self.ahead_behind_label.setText("(unknown)")
            self.ahead_behind_label.setStyleSheet("color: gray;")
            self._upstream_ref = None
            return
        
        # Get default upstream ref
        upstream_ref = self._git_client.default_upstream_ref(
            repo_root, self._remote_name
        )
        self._upstream_ref = upstream_ref
        
        if not upstream_ref:
            self.upstream_label.setText("(not set)")
            self.upstream_label.setStyleSheet("color: gray;")
            self.ahead_behind_label.setText("(unknown)")
            self.ahead_behind_label.setStyleSheet("color: gray;")
            return
        
        # Display upstream
        self.upstream_label.setText(upstream_ref)
        self.upstream_label.setStyleSheet("color: blue;")
        
        # Compute ahead/behind
        ab_result = self._git_client.ahead_behind(repo_root, upstream_ref)
        
        if ab_result["ok"]:
            ahead = ab_result["ahead"]
            behind = ab_result["behind"]
            
            self._ahead_count = ahead
            self._behind_count = behind
            
            ab_text = f"Ahead {ahead} / Behind {behind}"
            
            if ahead == 0 and behind == 0:
                self.ahead_behind_label.setStyleSheet("color: green;")
            elif behind > 0:
                self.ahead_behind_label.setStyleSheet("color: orange;")
            else:
                self.ahead_behind_label.setStyleSheet("color: blue;")
            
            self.ahead_behind_label.setText(ab_text)
        else:
            self.ahead_behind_label.setText("(error)")
            self.ahead_behind_label.setStyleSheet("color: red;")
            if ab_result["error"]:
                log.debug(
                    f"Ahead/behind error: {ab_result['error']}"
                )

        self._update_button_states()

    def _display_last_fetch(self):
        """Display the last fetch timestamp"""
        last_fetch = settings.load_last_fetch_at()
        if last_fetch:
            # Parse ISO timestamp and format for display
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(last_fetch)
                display_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                self.last_fetch_label.setText(display_time)
                self.last_fetch_label.setStyleSheet("color: blue;")
            except (ValueError, AttributeError):
                self.last_fetch_label.setText(last_fetch)
                self.last_fetch_label.setStyleSheet("color: blue;")
        else:
            self.last_fetch_label.setText("(never)")
            self.last_fetch_label.setStyleSheet("color: gray;")

    def _update_button_states(self):
        """Update enabled/disabled state of action buttons."""
        git_ok = self._git_client.is_git_available()
        repo_ok = (
            self._current_repo_root is not None
            and self._current_repo_root != ""
        )
        has_remote = False
        upstream_ok = self._upstream_ref is not None
        changes_present = len(self._file_statuses) > 0
        commit_msg_ok = False
        busy = (
            self._is_fetching
            or self._is_pulling
            or self._is_committing
            or self._is_pushing
            or self._job_runner.is_busy()
        )

        if repo_ok:
            has_remote = self._git_client.has_remote(
                self._current_repo_root, self._remote_name
            )

        if hasattr(self, "commit_message"):
            commit_msg_ok = bool(
                self.commit_message.toPlainText().strip()
            )

        fetch_enabled = (
            git_ok and repo_ok and has_remote and not self._is_fetching
            and not self._is_pulling and not busy
        )
        self.fetch_btn.setEnabled(fetch_enabled)

        pull_enabled = (
            git_ok and repo_ok and has_remote and upstream_ok
            and self._behind_count > 0 and not self._is_fetching
            and not self._is_pulling and not busy
        )
        self.pull_btn.setEnabled(pull_enabled)

        commit_enabled = (
            git_ok and repo_ok and changes_present and commit_msg_ok
            and not busy
        )
        self.commit_btn.setEnabled(commit_enabled)

        push_enabled = (
            git_ok and repo_ok and has_remote and not busy
            and ((self._ahead_count > 0) or not upstream_ok)
        )
        self.push_btn.setEnabled(push_enabled)

        if hasattr(self, "stage_all_checkbox"):
            self.stage_all_checkbox.setEnabled(
                repo_ok and changes_present
            )

        self.changes_list.setEnabled(repo_ok)
        self.publish_btn.setEnabled(False)

    def _show_status_message(self, message, is_error=True):
        """
        Show a status message in the status section
        
        Args:
            message: str - message to display
            is_error: bool - whether this is an error message
        """
        if message:
            self.status_message_label.setText(message)
            if is_error:
                self.status_message_label.setStyleSheet(
                    "color: red; font-size: 10px;"
                )
            else:
                self.status_message_label.setStyleSheet(
                    "color: blue; font-size: 10px;"
                )
            self.status_message_label.show()
        else:
            self.status_message_label.hide()

    def _clear_status_message(self):
        """Clear the status message"""
        self.status_message_label.hide()

    def _on_fetch_clicked(self):
        """
        Handle Fetch button click.
        Run fetch in background via job runner.
        """
        if not self._current_repo_root:
            log.warning("No repository to fetch")
            return
        
        if self._is_fetching:
            log.debug("Fetch already in progress, ignoring click")
            return
        
        # Clear previous messages
        self._clear_status_message()
        
        # Set fetching state
        self._is_fetching = True
        self.fetch_btn.setText("Fetching…")
        self.fetch_btn.setEnabled(False)
        self._start_busy_feedback("Fetching…")
        
        log.info(f"Starting fetch from {self._remote_name}")
        
        # Build command
        git_cmd = self._git_client._get_git_command()
        command = [
            git_cmd, "-C", self._current_repo_root,
            "fetch", self._remote_name
        ]
        
        # Run via job runner
        self._job_runner.run_job(
            "fetch",
            command,
            callback=self._on_fetch_job_finished
        )

    def _on_fetch_job_finished(self, job):
        """
        Callback when fetch job finishes
        
        Args:
            job: dict - job result from job runner
        """
        # This callback runs in addition to _on_job_finished signal
        # We'll do most work in _on_job_finished to avoid duplication
        pass

    def _on_pull_clicked(self):
        """
        Handle Pull button click.
        Check for uncommitted changes; if present, show warning.
        Then run pull sequence: fetch -> pull -> refresh.
        """
        log.info("Pull button clicked!")
        
        if not self._current_repo_root:
            log.warning("No repository to pull")
            return
        
        if self._is_pulling or self._is_fetching:
            log.debug("Pull/fetch already in progress")
            return
        
        log.info(f"Starting pull for repo: {self._current_repo_root}")
        
        # Clear previous messages
        self._clear_status_message()
        
        # Check for uncommitted changes
        has_changes = (
            self._git_client.has_uncommitted_changes(
                self._current_repo_root
            )
        )
        
        log.info(f"Has uncommitted changes: {has_changes}")
        
        if has_changes:
            # Show warning dialog
            dlg = dialogs.UncommittedChangesWarningDialog(self)
            if not dlg.show_and_ask():
                log.info("User cancelled pull due to changes")
                return
        
        # Start pull sequence
        self._start_pull_sequence()

    def _start_pull_sequence(self):
        """
        Start the pull sequence: fetch -> pull -> refresh.
        This is an async workflow that keeps UI responsive.
        """
        if not self._current_repo_root or not self._upstream_ref:
            log.warning("Cannot start pull sequence")
            return
        
        self._is_pulling = True
        self.pull_btn.setEnabled(False)
        self.fetch_btn.setEnabled(False)
        self._update_operation_status("Pulling…")
        self._start_busy_feedback("Pulling…")
        
        # Step 1: Fetch from origin
        git_cmd = self._git_client._get_git_command()
        command = [
            git_cmd, "-C", self._current_repo_root,
            "fetch", self._remote_name
        ]
        
        log.info("Pull sequence: starting fetch")
        self._job_runner.run_job(
            "pull_fetch",
            command,
            callback=self._on_pull_fetch_completed
        )

    def _on_pull_fetch_completed(self, job):
        """
        Callback when fetch completes in pull sequence.
        If successful, proceed to pull; otherwise abort.
        """
        result = job.get("result", {})
        if not result.get("success"):
            # Fetch failed - abort pull sequence
            stderr = result.get("stderr", "")
            log.warning(
                f"Pull sequence aborted: fetch failed: {stderr}"
            )
            self._handle_pull_failed("Fetch failed before pull")
            return
        
        log.info("Pull sequence: fetch completed, starting pull")
        
        # Step 2: Pull with ff-only
        if not self._current_repo_root or not self._upstream_ref:
            self._handle_pull_failed("Repository lost during pull")
            return
        
        git_cmd = self._git_client._get_git_command()
        # Extract branch from upstream (e.g., origin/main -> main)
        if "/" in self._upstream_ref:
            branch = self._upstream_ref.split("/", 1)[1]
        else:
            branch = self._upstream_ref
        
        command = [
            git_cmd, "-C", self._current_repo_root,
            "pull", "--ff-only", self._remote_name, branch
        ]
        
        self._job_runner.run_job(
            "pull_main",
            command,
            callback=self._on_pull_main_completed
        )

    def _on_pull_main_completed(self, job):
        """
        Callback when main pull command completes.
        Refresh status if successful.
        """
        result = job.get("result", {})
        success = result.get("success", False)
        stderr = result.get("stderr", "")
        
        if not success:
            # Pull failed - classify error and show dialog
            error_code = (
                self._git_client._classify_pull_error(stderr)
            )
            log.warning(
                f"Pull failed with error {error_code}: {stderr}"
            )
            self._show_pull_error_dialog(error_code, stderr)
            self._is_pulling = False
            self._update_operation_status("Error")
            self._stop_busy_feedback()
            self._update_button_states()
            return
        
        log.info("Pull completed successfully")
        self._update_operation_status("Synced")
        self._stop_busy_feedback()
        
        if self._current_repo_root:
            branch = self._git_client.current_branch(
                self._current_repo_root
            )
            self.branch_label.setText(branch)
            
            self._refresh_status_views(self._current_repo_root)
            
            self._update_upstream_info(self._current_repo_root)
            
            from datetime import datetime, timezone
            pull_time = datetime.now(timezone.utc).isoformat()
            settings.save_last_pull_at(pull_time)
        
        self._is_pulling = False
        self._show_status_message(
            "Synced to latest",
            is_error=False
        )
        
        # Clear success message after 3 seconds
        QtCore.QTimer.singleShot(
            3000, self._clear_status_message
        )
        
        self._update_button_states()

    def _handle_pull_failed(self, message):
        """
        Handle pull failure.
        
        Args:
            message: str - failure message
        """
        self._is_pulling = False
        self._update_operation_status("Error")
        self._show_status_message(message, is_error=True)
        self._stop_busy_feedback()
        self._update_button_states()

    def _show_pull_error_dialog(self, error_code, stderr):
        """
        Show detailed error dialog for pull failure.
        
        Args:
            error_code: str - error classification
            stderr: str - raw error output
        """
        dlg = dialogs.PullErrorDialog(error_code, stderr, self)
        dlg.exec()

    def _update_operation_status(self, status_text):
        """
        Update the operation status label.
        
        Args:
            status_text: str - status message
        """
        self.operation_status_label.setText(status_text)
        if status_text == "Ready":
            self.operation_status_label.setStyleSheet(
                "color: gray; font-size: 9px;"
            )
        elif "…" in status_text:
            self.operation_status_label.setStyleSheet(
                "color: orange; font-size: 9px;"
            )
        elif status_text == "Synced":
            self.operation_status_label.setStyleSheet(
                "color: green; font-size: 9px;"
            )
        else:
            self.operation_status_label.setStyleSheet(
                "color: red; font-size: 9px;"
            )

    def _start_busy_feedback(self, label):
        """Show progress indicator and periodic status updates."""
        self._busy_label = label
        if hasattr(self, "busy_bar"):
            self.busy_bar.show()
        self._update_operation_status(label)
        self._busy_timer.start()
        self._show_status_message(label, is_error=False)

    def _stop_busy_feedback(self):
        """Hide progress indicator and stop timer."""
        self._busy_timer.stop()
        self._busy_label = ""
        if hasattr(self, "busy_bar"):
            self.busy_bar.hide()
        self._set_ready_later()

    def _on_busy_timer_tick(self):
        """Periodic pulse while a long operation is running."""
        if self._busy_label:
            self._show_status_message(
                f"Working… {self._busy_label}",
                is_error=False,
            )

    def _set_ready_later(self, delay_ms=1500, status_text="Ready"):
        """Return UI to Ready after a short delay if idle."""
        def _to_ready():
            if not (
                self._is_fetching
                or self._is_pulling
                or self._is_committing
                or self._is_pushing
                or self._job_runner.is_busy()
            ):
                self._update_operation_status(status_text)
        QtCore.QTimer.singleShot(delay_ms, _to_ready)

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

    def _refresh_status_views(self, repo_root):
        """Refresh working tree status and changes list."""
        status = self._git_client.status_summary(repo_root)
        self._display_working_tree_status(status)

        self._file_statuses = self._git_client.status_porcelain(repo_root)
        self._populate_changes_list()
        self._update_button_states()

    def _populate_changes_list(self):
        """Update changes list widget with current file statuses."""
        self.changes_list.clear()

        if not self._file_statuses:
            return

        for entry in self._file_statuses:
            prefix = f"{entry.x}{entry.y}"
            text = f"{prefix} {entry.path}"
            self.changes_list.addItem(text)

    def _on_commit_message_changed(self):
        """Called when commit message text changes."""
        self._update_button_states()

    def _on_commit_clicked(self):
        """Handle Commit button click."""
        if not self._current_repo_root:
            log.warning("No repository to commit")
            return

        if self._is_committing or self._job_runner.is_busy():
            log.debug("Job running, commit ignored")
            return

        message = self.commit_message.toPlainText().strip()
        if not message:
            self._show_status_message(
                "Commit message required", is_error=True
            )
            return

        if self._behind_count > 0:
            behind_msg = (
                f"You're {self._behind_count} commits behind upstream. "
                "Consider Pull before pushing."
            )
            self._show_status_message(behind_msg, is_error=False)

        self._clear_status_message()
        self._is_committing = True
        self.commit_btn.setText("Committing…")
        self._pending_commit_message = message
        self._update_button_states()
        self._start_busy_feedback("Committing…")

        log.info("Starting commit sequence")

        git_cmd = self._git_client._get_git_command()
        args = [git_cmd, "-C", self._current_repo_root, "add", "-A"]

        self._job_runner.run_job(
            "commit_stage",
            args,
            callback=self._on_commit_stage_completed,
        )

    def _on_commit_stage_completed(self, job):
        """Callback after staging completes."""
        result = job.get("result", {})
        if not result.get("success"):
            log.warning(
                f"Stage failed: {result.get('stderr', '')}"
            )
            self._handle_commit_failed("Stage failed")
            return

        log.debug("Stage completed, running commit")

        if not self._current_repo_root:
            self._handle_commit_failed("Repository lost")
            return

        message = self._pending_commit_message
        if not message:
            self._handle_commit_failed("No commit message")
            return

        git_cmd = self._git_client._get_git_command()
        args = [git_cmd, "-C", self._current_repo_root, "commit", "-m", message]

        self._job_runner.run_job(
            "commit_main",
            args,
            callback=self._on_commit_main_completed,
        )

    def _on_commit_main_completed(self, job):
        """Callback after commit completes."""
        result = job.get("result", {})
        success = result.get("success", False)
        stderr = result.get("stderr", "")

        self._is_committing = False
        self.commit_btn.setText("Commit")
        self._pending_commit_message = ""
        self._stop_busy_feedback()

        if not success:
            code = self._git_client._classify_commit_error(stderr)
            if code == "NOTHING_TO_COMMIT":
                self._show_status_message(
                    "No changes to commit", is_error=False
                )
            elif code == "MISSING_IDENTITY":
                self._show_commit_identity_error_dialog()
            else:
                self._show_status_message(
                    f"Commit failed: {stderr[:80]}", is_error=True
                )
            log.warning(f"Commit failed: {code}")
            self._update_button_states()
            return

        log.info("Commit created successfully")
        self.commit_message.clear()

        if self._current_repo_root:
            branch = self._git_client.current_branch(
                self._current_repo_root
            )
            self.branch_label.setText(branch)
            self._refresh_status_views(self._current_repo_root)
            self._update_upstream_info(self._current_repo_root)

        self._show_status_message(
            "Commit created", is_error=False
        )

        QtCore.QTimer.singleShot(2000, self._clear_status_message)
        self._update_button_states()

    def _handle_commit_failed(self, message):
        """Handle commit failure."""
        self._is_committing = False
        self.commit_btn.setText("Commit")
        self._show_status_message(message, is_error=True)
        self._stop_busy_feedback()
        self._update_button_states()

    def _show_commit_identity_error_dialog(self):
        """Show error about missing git identity."""
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setIcon(QtWidgets.QMessageBox.Warning)
        msg_box.setWindowTitle("Git Identity Not Configured")
        msg_box.setText(
            "Git needs your name and email before committing."
        )
        details = (
            "Configure in GitHub Desktop or run:\n\n"
            "git config --global user.name \"Your Name\"\n"
            "git config --global user.email \"you@example.com\""
        )
        msg_box.setInformativeText(details)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg_box.exec()

    def _on_push_clicked(self):
        """Handle Push button click."""
        if not self._current_repo_root:
            log.warning("No repository to push")
            return

        if self._is_pushing or self._job_runner.is_busy():
            log.debug("Job running, push ignored")
            return

        if self._behind_count > 0:
            should_continue = self._show_push_behind_warning()
            if not should_continue:
                log.info("User cancelled push due to being behind")
                return

        self._clear_status_message()
        self._is_pushing = True
        self.push_btn.setText("Pushing…")
        self._update_button_states()
        self._start_busy_feedback("Pushing…")

        log.info("Starting push")

        git_cmd = self._git_client._get_git_command()

        has_upstream = self._git_client.has_upstream(
            self._current_repo_root
        )

        if has_upstream:
            args = [git_cmd, "-C", self._current_repo_root, "push"]
        else:
            args = [
                git_cmd, "-C", self._current_repo_root, "push", "-u",
                self._remote_name, "HEAD"
            ]

        self._job_runner.run_job(
            "push_main",
            args,
            callback=self._on_push_main_completed,
        )

    def _on_push_main_completed(self, job):
        """Callback when push completes."""
        result = job.get("result", {})
        success = result.get("success", False)
        stderr = result.get("stderr", "")

        self._is_pushing = False
        self.push_btn.setText("Push")

        if not success:
            code = self._git_client._classify_push_error(stderr)
            self._show_push_error_dialog(code, stderr)
            log.warning(f"Push failed: {code}")
            self._stop_busy_feedback()
            self._update_button_states()
            return

        log.info("Push completed successfully")

        # Clear any leftover commit message after a successful push
        if hasattr(self, "commit_message"):
            self.commit_message.clear()

        if self._current_repo_root:
            self._update_upstream_info(self._current_repo_root)

        self._show_status_message("Push completed", is_error=False)

        QtCore.QTimer.singleShot(2000, self._clear_status_message)

        self._stop_busy_feedback()

        self._update_button_states()

    def _show_push_behind_warning(self):
        """Show warning if behind upstream."""
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setIcon(QtWidgets.QMessageBox.Warning)
        msg_box.setWindowTitle("Behind Upstream")
        msg_box.setText(
            f"You're {self._behind_count} commits behind upstream. "
            "Push may be rejected."
        )
        msg_box.setInformativeText(
            "Consider Pull first to sync with upstream."
        )
        msg_box.setStandardButtons(
            QtWidgets.QMessageBox.Cancel
            | QtWidgets.QMessageBox.Ok
        )
        msg_box.setDefaultButton(QtWidgets.QMessageBox.Cancel)
        result = msg_box.exec()
        return result == QtWidgets.QMessageBox.Ok

    def _show_push_error_dialog(self, error_code, stderr):
        """Show error dialog for push failure."""
        dlg = dialogs.PushErrorDialog(error_code, stderr, self)
        dlg.exec()

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
        Sprint 2: Handle fetch results
        
        Args:
            job: dict - job result descriptor
        """
        job_type = job.get("type")
        log.debug(f"Job finished: {job_type}")
        
        if job_type == "fetch":
            self._handle_fetch_result(job)

    def _handle_fetch_result(self, job):
        """
        Handle fetch job completion
        
        Args:
            job: dict - job result from job runner
        """
        result = job.get("result", {})
        success = result.get("success", False)
        
        # Reset fetching state
        self._is_fetching = False
        self.fetch_btn.setText("Fetch")
        self._stop_busy_feedback()
        
        if success:
            # Fetch succeeded
            from datetime import datetime, timezone
            fetch_time = datetime.now(timezone.utc).isoformat()
            settings.save_last_fetch_at(fetch_time)
            
            # Update UI
            self._display_last_fetch()
            
            # Re-evaluate upstream and ahead/behind
            if self._current_repo_root:
                self._update_upstream_info(self._current_repo_root)
            
            self._show_status_message(
                "Fetch completed successfully", is_error=False
            )
            log.info("Fetch completed successfully")
            
            # Clear success message after 3 seconds
            QtCore.QTimer.singleShot(
                3000, self._clear_status_message
            )
        else:
            # Fetch failed
            stderr = result.get("stderr", "")
            exit_code = result.get("exit_code", -1)
            
            # Create user-friendly error message
            if "could not resolve host" in stderr.lower():
                error_msg = "Fetch failed: Network error"
            elif "permission denied" in stderr.lower():
                error_msg = "Fetch failed: Permission denied"
            elif exit_code == -1:
                error_msg = "Fetch failed: Process error"
            else:
                error_msg = f"Fetch failed (exit {exit_code})"
            
            self._show_status_message(error_msg, is_error=True)
            log.warning(f"Fetch failed: {stderr}")
        
        # Update button states
        self._update_button_states()

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
