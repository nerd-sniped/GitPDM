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
from freecad_gitpdm.export import exporter, mapper
from freecad_gitpdm.core import paths as core_paths
from freecad_gitpdm.core import publish


class _DocumentObserver:
    """Observer to detect document saves and trigger status refresh."""
    
    def __init__(self, panel):
        self._panel = panel
        self._refresh_timer = QtCore.QTimer()
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(500)
        self._refresh_timer.timeout.connect(self._do_refresh)
        log.debug("DocumentObserver created")
    
    def slotFinishSaveDocument(self, doc, filename):
        """Called after a document is saved."""
        log.debug(f"Document saved: {filename}")
        
        if not self._panel._current_repo_root:
            log.debug("No repo configured, skipping refresh")
            return
        
        try:
            import os
            filename = os.path.normpath(filename)
            repo_root = os.path.normpath(self._panel._current_repo_root)
            
            log.debug(f"Checking if {filename} is in {repo_root}")
            
            if filename.startswith(repo_root):
                log.info(f"Document saved in repo, scheduling refresh")
                self._refresh_timer.stop()
                self._refresh_timer.start()
                # Also schedule automatic preview generation for saved FCStd
                self._panel._schedule_auto_preview_generation(filename)
            else:
                log.debug(f"Document outside repo, no refresh")
        except Exception as e:
            log.error(f"Error in save handler: {e}")
    
    def _do_refresh(self):
        """Execute deferred refresh after save."""
        try:
            if self._panel._current_repo_root:
                log.info("Auto-refreshing status after save")
                self._panel._refresh_status_views(
                    self._panel._current_repo_root
                )
                log.debug("Refresh complete")
        except Exception as e:
            log.error(f"Refresh after save failed: {e}")


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
        self._all_cad_files = []
        self._is_listing_files = False
        self._busy_timer = QtCore.QTimer(self)
        self._busy_timer.setInterval(5000)
        self._busy_timer.timeout.connect(self._on_busy_timer_tick)
        self._busy_label = ""
        self._button_update_timer = QtCore.QTimer(self)
        self._button_update_timer.setSingleShot(True)
        self._button_update_timer.setInterval(300)
        self._button_update_timer.timeout.connect(
            self._do_deferred_button_update
        )
        self._cached_has_remote = False
        self._doc_observer = None
        self._browser_dock = None
        self._browser_content = None
        self._group_git_check = None
        self._group_repo_selector = None
        self._group_status = None
        self._group_changes = None
        self._group_actions = None
        self._actions_extra_container = None
        self._repo_browser_container = None
        self._is_compact = False

        # Font sizes for labels
        self._meta_font_size = 9
        self._strong_font_size = 11

        # Create main widget and layout
        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)
        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)

        # Build UI sections
        self._build_view_toggle(main_layout)
        self._build_git_check_section(main_layout)
        self._build_repo_selector(main_layout)
        self._build_github_account_section(main_layout)
        self._build_status_section(main_layout)
        self._build_changes_section(main_layout)
        self._build_buttons_section(main_layout)
        self._build_repo_browser_section(main_layout)

        # Default to collapsed view
        self._set_compact_mode(True)

        # Add stretch at bottom to push everything up
        main_layout.addStretch()

        # Load remote name
        self._remote_name = settings.load_remote_name()

        # Defer heavy initialization to avoid blocking UI and window flash
        QtCore.QTimer.singleShot(100, self._deferred_initialization)
        
        log.info("GitPDM dock panel created")

    def _set_meta_label(self, label, color="gray"):
        label.setStyleSheet(
            f"color: {color}; font-size: {self._meta_font_size}px;"
        )

    def _set_strong_label(self, label, color="black"):
        label.setStyleSheet(
            "font-weight: bold; "
            f"font-size: {self._strong_font_size}px; "
            f"color: {color};"
        )

    def _build_view_toggle(self, layout):
        """Add a compact/expanded toggle to shrink the dock UI."""
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(6, 4, 6, 0)
        row.setSpacing(6)

        label = QtWidgets.QLabel("View")
        self._set_meta_label(label, "gray")
        row.addWidget(label)

        self.compact_toggle_btn = QtWidgets.QPushButton("Collapse")
        self.compact_toggle_btn.setFlat(True)
        self.compact_toggle_btn.setMaximumWidth(80)
        self.compact_toggle_btn.clicked.connect(self._on_compact_clicked)
        row.addWidget(self.compact_toggle_btn)

        row.addStretch()
        layout.addLayout(row)

    def _on_compact_clicked(self):
        """Toggle between compact and expanded mode."""
        self._set_compact_mode(not self._is_compact)

    def _set_compact_mode(self, compact):
        self._is_compact = bool(compact)
        if hasattr(self, "compact_toggle_btn"):
            self.compact_toggle_btn.setText(
                "Expand" if compact else "Collapse"
            )
        show_full = not compact
        for w in [
            getattr(self, "_group_git_check", None),
            getattr(self, "_group_repo_selector", None),
            getattr(self, "_group_github_account", None),
            getattr(self, "_group_changes", None),
            getattr(self, "_actions_extra_container", None),
            getattr(self, "_repo_browser_container", None),
        ]:
            if w is not None:
                w.setVisible(show_full)
    
    def _deferred_initialization(self):
        """Run heavy initialization after panel is shown."""
        try:
            # Check git availability
            self._check_git_available()
            
            # Load saved repo path and validate
            self._load_saved_repo_path()
            
            # Register document observer to auto-refresh on save
            self._register_document_observer()
            
            log.info("GitPDM dock panel initialized")
        except Exception as e:
            log.error(f"Deferred initialization failed: {e}")
    
    def _register_document_observer(self):
        """Register observer to detect document saves."""
        try:
            import FreeCAD
            if self._doc_observer is None:
                self._doc_observer = _DocumentObserver(self)
                FreeCAD.addDocumentObserver(self._doc_observer)
                log.info("Document observer registered for auto-refresh")
            else:
                log.debug("Document observer already registered")
        except Exception as e:
            log.error(f"Failed to register document observer: {e}")
    
    def closeEvent(self, event):
        """Handle dock widget close - cleanup observers."""
        if self._doc_observer is not None:
            try:
                import FreeCAD
                FreeCAD.removeDocumentObserver(self._doc_observer)
                log.debug("Document observer unregistered")
            except Exception as e:
                log.warning(f"Failed to unregister observer: {e}")
        
        super().closeEvent(event)

    def _schedule_auto_preview_generation(self, filename):
        """Best-effort automatic preview export after a save/close."""
        try:
            import os
            if not filename or not filename.lower().endswith(".fcstd"):
                return
            if not self._current_repo_root:
                return
            # Avoid work if file is outside repo
            if not os.path.normpath(filename).startswith(
                os.path.normpath(self._current_repo_root)
            ):
                return

            def _do_export():
                try:
                    import FreeCAD
                    active = getattr(FreeCAD, "ActiveDocument", None)
                    active_path = getattr(active, "FileName", "") if active else ""
                    if not active_path:
                        log.debug("No active document for auto preview")
                        return
                    if os.path.normpath(active_path) != os.path.normpath(filename):
                        log.debug("Saved doc is not active; skipping auto preview")
                        return

                    result = exporter.export_active_document(
                        self._current_repo_root
                    )
                except Exception as e_export:
                    log.warning(f"Auto preview export failed: {e_export}")
                    return

                if not result or not result.ok:
                    log.warning(
                        f"Auto preview export failed: {getattr(result, 'message', '')}"
                    )
                    return

                from datetime import datetime, timezone
                settings.save_last_preview_at(
                    datetime.now(timezone.utc).isoformat()
                )
                if result.rel_dir:
                    settings.save_last_preview_dir(result.rel_dir)
                self._update_preview_status_labels()

            # Defer to allow FreeCAD to finish its own save cycle
            QtCore.QTimer.singleShot(0, _do_export)
        except Exception as e:
            log.warning(f"Failed to schedule auto preview: {e}")

    def _build_git_check_section(self, layout):
        """
        Build the git availability check section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("System")
        group_layout = QtWidgets.QFormLayout()
        group_layout.setContentsMargins(6, 4, 6, 4)
        group_layout.setVerticalSpacing(4)
        group.setLayout(group_layout)

        # Git availability (compact)
        self.git_label = QtWidgets.QLabel("● Checking…")
        self.git_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self.git_label.setStyleSheet("color: orange;")
        group_layout.addRow("Git", self.git_label)

        layout.addWidget(group)
        self._group_git_check = group

    def _check_git_available(self):
        """Check if git is available on system"""
        is_available = self._git_client.is_git_available()
        if is_available:
            version = self._git_client.git_version()
            self.git_label.setText(f"● OK ({version})")
            self.git_label.setStyleSheet("color: green;")
        else:
            self.git_label.setText("● Not found")
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
        group_layout.setContentsMargins(6, 3, 6, 3)
        group_layout.setSpacing(2)
        group.setLayout(group_layout)

        # Repo path row
        path_layout = QtWidgets.QHBoxLayout()
        path_layout.setSpacing(4)
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
        # Root details (collapsed by default)
        self.root_toggle_btn = QtWidgets.QToolButton()
        self.root_toggle_btn.setText("Show root")
        self.root_toggle_btn.setArrowType(QtCore.Qt.RightArrow)
        self.root_toggle_btn.setToolButtonStyle(
            QtCore.Qt.ToolButtonTextBesideIcon
        )
        self.root_toggle_btn.setCheckable(True)
        self.root_toggle_btn.setEnabled(False)
        self.root_toggle_btn.toggled.connect(
            self._on_root_toggle
        )
        group_layout.addWidget(self.root_toggle_btn)

        self.repo_root_row = QtWidgets.QWidget()
        repo_root_layout = QtWidgets.QHBoxLayout()
        repo_root_layout.setContentsMargins(0, 0, 0, 0)
        repo_root_layout.setSpacing(4)
        self.repo_root_row.setLayout(repo_root_layout)

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
        self.repo_root_row.setVisible(False)
        group_layout.addWidget(self.repo_root_row)

        # Validation status row
        validation_layout = QtWidgets.QHBoxLayout()
        validation_layout.setSpacing(4)
        validation_layout.addWidget(QtWidgets.QLabel("Validate:"))
        self.validate_label = QtWidgets.QLabel("Not checked")
        self.validate_label.setStyleSheet(
            "color: gray; font-style: italic;"
        )
        validation_layout.addWidget(self.validate_label)
        validation_layout.addStretch()

        self.create_repo_btn = QtWidgets.QPushButton("Create Repo")
        self.create_repo_btn.setMinimumWidth(130)
        self.create_repo_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.create_repo_btn.clicked.connect(self._on_create_repo_clicked)
        self.create_repo_btn.setVisible(False)
        validation_layout.addWidget(self.create_repo_btn)

        self.connect_remote_btn = QtWidgets.QPushButton("Connect Remote")
        self.connect_remote_btn.setMinimumWidth(130)
        self.connect_remote_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.connect_remote_btn.clicked.connect(self._on_connect_remote_clicked)
        self.connect_remote_btn.setVisible(False)
        validation_layout.addWidget(self.connect_remote_btn)

        refresh_btn = QtWidgets.QPushButton("Refresh Status")
        refresh_btn.setMinimumWidth(130)
        refresh_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,
        )
        refresh_btn.clicked.connect(self._on_refresh_clicked)
        validation_layout.addWidget(refresh_btn)

        group_layout.addLayout(validation_layout)

        layout.addWidget(group)
        self._group_repo_selector = group

    def _build_github_account_section(self, layout):
        """
        Build the GitHub Account section (Sprint OAUTH-0)
        Shows connection status and connect/disconnect buttons.
        No actual OAuth implementation yet - just placeholders.
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("GitHub Account")
        group_layout = QtWidgets.QVBoxLayout()
        group_layout.setContentsMargins(6, 4, 6, 4)
        group_layout.setSpacing(4)
        group.setLayout(group_layout)

        # Connection status label
        self.github_status_label = QtWidgets.QLabel(
            "GitHub: Not connected"
        )
        self._set_strong_label(self.github_status_label, "gray")
        group_layout.addWidget(self.github_status_label)

        # Check if OAuth is configured
        try:
            from freecad_gitpdm.auth import config as auth_config
            client_id = auth_config.get_client_id()
            oauth_configured = client_id is not None
        except Exception:
            oauth_configured = False

        # Config hint (shown if OAuth not configured)
        if not oauth_configured:
            hint_label = QtWidgets.QLabel(
                "GitHub OAuth not configured. See docs."
            )
            hint_label.setWordWrap(True)
            hint_label.setStyleSheet(
                "color: orange; font-style: italic; font-size: 9px;"
            )
            group_layout.addWidget(hint_label)

        # Buttons row
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setSpacing(4)

        self.github_connect_btn = QtWidgets.QPushButton(
            "Connect GitHub"
        )
        self.github_connect_btn.setEnabled(oauth_configured)
        self.github_connect_btn.setToolTip(
            "Connect to GitHub using OAuth Device Flow"
            if oauth_configured
            else "OAuth not configured"
        )
        # TODO OAUTH-1: Connect to OAuth flow handler
        buttons_layout.addWidget(self.github_connect_btn)

        self.github_disconnect_btn = QtWidgets.QPushButton(
            "Disconnect"
        )
        self.github_disconnect_btn.setEnabled(False)
        self.github_disconnect_btn.setToolTip(
            "Disconnect GitHub account"
        )
        # TODO OAUTH-1: Connect to disconnect handler
        buttons_layout.addWidget(self.github_disconnect_btn)

        group_layout.addLayout(buttons_layout)

        layout.addWidget(group)
        self._group_github_account = group

    def _build_status_section(self, layout):
        """
        Build the status information section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("Status")
        group_layout = QtWidgets.QVBoxLayout()
        group_layout.setContentsMargins(6, 4, 6, 4)
        group_layout.setSpacing(4)
        group.setLayout(group_layout)

        # Operation status header (shows Pulling… / Fetching… / Synced)
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(4)
        header_layout.addWidget(QtWidgets.QLabel("Operation:"))
        self.operation_status_label = QtWidgets.QLabel("Ready")
        self.operation_status_label.setStyleSheet(
            "color: gray; font-size: 9px;"
        )
        self.operation_status_label.setAlignment(QtCore.Qt.AlignRight)
        header_layout.addWidget(self.operation_status_label, 1)
        group_layout.addLayout(header_layout)

        # Grid-style fields in 3 columns
        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(8)
        grid_layout.setVerticalSpacing(2)

        def add_field(row, col, title, value_label):
            caption = QtWidgets.QLabel(title)
            self._set_meta_label(caption, "gray")
            grid_layout.addWidget(caption, row * 2, col)
            grid_layout.addWidget(value_label, row * 2 + 1, col)

        # Value labels
        self.working_tree_label = QtWidgets.QLabel("—")
        self.working_tree_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self._set_strong_label(self.working_tree_label, "black")

        self.ahead_behind_label = QtWidgets.QLabel("—")
        self.ahead_behind_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self._set_strong_label(self.ahead_behind_label, "black")

        self.branch_label = QtWidgets.QLabel("—")
        self.branch_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self._set_meta_label(self.branch_label, "gray")

        self.upstream_label = QtWidgets.QLabel("—")
        self.upstream_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self._set_meta_label(self.upstream_label, "gray")

        self.last_fetch_label = QtWidgets.QLabel("—")
        self.last_fetch_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self._set_meta_label(self.last_fetch_label, "gray")

        add_field(0, 0, "Working tree", self.working_tree_label)
        add_field(0, 1, "Ahead/Behind", self.ahead_behind_label)
        add_field(0, 2, "Branch", self.branch_label)
        add_field(1, 0, "Upstream", self.upstream_label)
        add_field(1, 1, "Last fetch", self.last_fetch_label)

        group_layout.addLayout(grid_layout)

        # Error/message area (Sprint 2)
        self.status_message_label = QtWidgets.QLabel("")
        self.status_message_label.setWordWrap(True)
        self.status_message_label.setStyleSheet(
            "color: red; font-size: 10px;"
        )
        self.status_message_label.hide()
        group_layout.addWidget(self.status_message_label)

        layout.addWidget(group)
        self._group_status = group

    def _build_changes_section(self, layout):
        """
        Build the changes list section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("Changes")
        group_layout = QtWidgets.QVBoxLayout()
        group_layout.setContentsMargins(6, 4, 6, 4)
        group_layout.setSpacing(4)
        group.setLayout(group_layout)

        info_label = QtWidgets.QLabel(
            "Working tree changes detected by git status." 
            " Use Stage all to include them in commits."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        group_layout.addWidget(info_label)

        self.changes_list = QtWidgets.QListWidget()
        self.changes_list.setMaximumHeight(80)
        self.changes_list.setEnabled(False)
        group_layout.addWidget(self.changes_list)

        stage_layout = QtWidgets.QHBoxLayout()
        stage_layout.setSpacing(4)
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
        self._group_changes = group

    def _build_buttons_section(self, layout):
        """
        Build the action buttons section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("Actions")
        group_layout = QtWidgets.QVBoxLayout()
        group_layout.setContentsMargins(6, 4, 6, 4)
        group_layout.setSpacing(4)
        group.setLayout(group_layout)

        row1_layout = QtWidgets.QHBoxLayout()
        row1_layout.setSpacing(4)
        self.fetch_btn = QtWidgets.QPushButton("Fetch")
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.clicked.connect(self._on_fetch_clicked)
        row1_layout.addWidget(self.fetch_btn)

        self.pull_btn = QtWidgets.QPushButton("Pull")
        self.pull_btn.setEnabled(False)
        self.pull_btn.clicked.connect(self._on_pull_clicked)
        row1_layout.addWidget(self.pull_btn)

        group_layout.addLayout(row1_layout)

        # Extra actions are grouped for easy hide/show in compact mode
        self._actions_extra_container = QtWidgets.QWidget()
        extra_layout = QtWidgets.QVBoxLayout()
        extra_layout.setContentsMargins(0, 0, 0, 0)
        extra_layout.setSpacing(4)
        self._actions_extra_container.setLayout(extra_layout)

        msg_label = QtWidgets.QLabel("Commit message:")
        msg_label.setStyleSheet("font-weight: bold;")
        extra_layout.addWidget(msg_label)

        self.commit_message = QtWidgets.QPlainTextEdit()
        self.commit_message.setPlaceholderText(
            "Describe your changes before committing"
        )
        self.commit_message.setMaximumHeight(70)
        self.commit_message.textChanged.connect(
            self._on_commit_message_changed
        )
        extra_layout.addWidget(self.commit_message)

        row2_layout = QtWidgets.QHBoxLayout()
        row2_layout.setSpacing(4)
        
        # Combined Commit & Push / Publish button (regular push button)
        self.commit_push_btn = QtWidgets.QPushButton("Commit & Push")
        self.commit_push_btn.setEnabled(False)
        self.commit_push_btn.clicked.connect(
            self._on_commit_push_clicked
        )
        
        # Dropdown menu for workflow selection
        self.workflow_menu = QtWidgets.QMenu(self)
        self.workflow_action_both = self.workflow_menu.addAction(
            "Commit & Push"
        )
        self.workflow_action_both.setCheckable(True)
        self.workflow_action_both.setChecked(True)
        self.workflow_action_both.triggered.connect(
            self._on_workflow_changed
        )
        self.workflow_action_commit = self.workflow_menu.addAction(
            "Commit Only"
        )
        self.workflow_action_commit.setCheckable(True)
        self.workflow_action_commit.triggered.connect(
            self._on_workflow_changed
        )
        self.workflow_action_push = self.workflow_menu.addAction(
            "Push Only"
        )
        self.workflow_action_push.setCheckable(True)
        self.workflow_action_push.triggered.connect(
            self._on_workflow_changed
        )
        self.workflow_menu.addSeparator()
        self.workflow_action_publish = self.workflow_menu.addAction(
            "Publish Branch (with previews)"
        )
        self.workflow_action_publish.setCheckable(True)
        self.workflow_action_publish.triggered.connect(
            self._on_workflow_changed
        )
        
        self._workflow_mode = 'both'
        
        # Dropdown menu button (plain QPushButton to avoid duplicate indicators)
        workflow_menu_btn = QtWidgets.QPushButton("▼")
        workflow_menu_btn.setAutoDefault(False)
        workflow_menu_btn.setDefault(False)
        workflow_menu_btn.setFlat(True)
        workflow_menu_btn.setFixedWidth(24)
        workflow_menu_btn.setToolTip("Select workflow: Commit & Push, Commit Only, Push Only, or Publish Branch")
        workflow_menu_btn.clicked.connect(
            lambda: self.workflow_menu.exec_(
                workflow_menu_btn.mapToGlobal(
                    QtCore.QPoint(0, workflow_menu_btn.height())
                )
            )
        )
        
        row2_layout.addWidget(self.commit_push_btn)
        row2_layout.addWidget(workflow_menu_btn)

        extra_layout.addLayout(row2_layout)

        self.stage_all_checkbox = QtWidgets.QCheckBox(
            "Stage all changes during Publish"
        )
        self.stage_all_checkbox.setChecked(True)
        extra_layout.addWidget(self.stage_all_checkbox)

        # Sprint 6: Generate Previews workflow
        previews_group = QtWidgets.QGroupBox("Previews")
        pg_layout = QtWidgets.QVBoxLayout()
        pg_layout.setContentsMargins(6, 4, 6, 4)
        pg_layout.setSpacing(4)
        previews_group.setLayout(pg_layout)

        rowp = QtWidgets.QHBoxLayout()
        rowp.setSpacing(4)
        self.generate_previews_btn = QtWidgets.QPushButton(
            "Generate Previews"
        )
        self.generate_previews_btn.setEnabled(False)
        self.generate_previews_btn.clicked.connect(
            self._on_generate_previews_clicked
        )
        rowp.addWidget(self.generate_previews_btn)

        self.stage_previews_checkbox = QtWidgets.QCheckBox(
            "Stage preview files after export"
        )
        self.stage_previews_checkbox.setChecked(
            settings.load_stage_previews_default_on()
        )
        self.stage_previews_checkbox.stateChanged.connect(
            lambda _:
                settings.save_stage_previews(
                    self.stage_previews_checkbox.isChecked()
                )
        )
        rowp.addWidget(self.stage_previews_checkbox)
        rowp.addStretch()
        pg_layout.addLayout(rowp)

        # Status area
        status_row = QtWidgets.QHBoxLayout()
        status_row.setSpacing(6)
        self.preview_status_label = QtWidgets.QLabel(
            "Last generated: (never)"
        )
        self._set_meta_label(self.preview_status_label, "gray")
        status_row.addWidget(self.preview_status_label)
        status_row.addStretch()
        self.open_preview_folder_btn = QtWidgets.QPushButton(
            "Open Folder"
        )
        self.open_preview_folder_btn.setEnabled(False)
        self.open_preview_folder_btn.clicked.connect(
            self._on_open_preview_folder_clicked
        )
        status_row.addWidget(self.open_preview_folder_btn)
        pg_layout.addLayout(status_row)

        extra_layout.addWidget(previews_group)

        # Busy indicator (indeterminate)
        self.busy_bar = QtWidgets.QProgressBar()
        self.busy_bar.setRange(0, 0)
        self.busy_bar.setFixedHeight(8)
        self.busy_bar.hide()

        # Add extras container and busy bar
        group_layout.addWidget(self._actions_extra_container)
        group_layout.addWidget(self.busy_bar)

        layout.addWidget(group)
        self._group_actions = group

    def _build_repo_browser_section(self, layout):
        """Build launcher row for the dockable repository browser."""
        self._ensure_browser_host()

        container = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(6, 4, 6, 4)
        row.setSpacing(4)
        container.setLayout(row)

        label = QtWidgets.QLabel("Repository Browser")
        self._set_meta_label(label, "gray")
        row.addWidget(label)
        row.addStretch()

        self.browser_window_btn = QtWidgets.QPushButton(
            "Open Browser"
        )
        self.browser_window_btn.setEnabled(False)
        self.browser_window_btn.clicked.connect(
            self._open_repo_browser
        )
        row.addWidget(self.browser_window_btn)

        layout.addWidget(container)
        self._repo_browser_container = container

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

    def _on_root_toggle(self, checked):
        """Show or hide the resolved repo root row."""
        self.repo_root_row.setVisible(checked)
        self.root_toggle_btn.setArrowType(
            QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow
        )
        self.root_toggle_btn.setText(
            "Hide root" if checked else "Show root"
        )

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
            self.last_fetch_label.setText("—")
            self._set_meta_label(self.branch_label, "gray")
            self._set_strong_label(self.working_tree_label, "black")
            self._set_meta_label(self.upstream_label, "gray")
            self._set_strong_label(self.ahead_behind_label, "gray")
            self._set_meta_label(self.last_fetch_label, "gray")
            self.root_toggle_btn.setEnabled(False)
            self.root_toggle_btn.setChecked(False)
            self.repo_root_row.setVisible(False)
            self.root_toggle_btn.setArrowType(QtCore.Qt.RightArrow)
            self.root_toggle_btn.setText("Show root")
            self.browser_window_btn.setEnabled(False)
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

            self.root_toggle_btn.setEnabled(True)
            self.repo_root_row.setVisible(
                self.root_toggle_btn.isChecked()
            )
            self.browser_window_btn.setEnabled(True)

            # Fetch branch and status
            self._fetch_branch_and_status(repo_root)
            # Refresh repo browser
            self._refresh_repo_browser_files()
            # Update preview status area
            self._update_preview_status_labels()
            
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
            self.last_fetch_label.setText("—")
            self._set_meta_label(self.branch_label, "gray")
            self._set_strong_label(self.working_tree_label, "black")
            self._set_meta_label(self.upstream_label, "gray")
            self._set_strong_label(self.ahead_behind_label, "gray")
            self._set_meta_label(self.last_fetch_label, "gray")
            self._current_repo_root = None
            self.root_toggle_btn.setEnabled(False)
            self.root_toggle_btn.setChecked(False)
            self.repo_root_row.setVisible(False)
            self.root_toggle_btn.setArrowType(QtCore.Qt.RightArrow)
            self.root_toggle_btn.setText("Show root")
            self.browser_window_btn.setEnabled(False)
            self._update_button_states()
            # Clear browser section
            self._clear_repo_browser()
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
        
        self._cached_has_remote = self._git_client.has_remote(
            repo_root, self._remote_name
        )
        
        if not self._cached_has_remote:
            self.upstream_label.setText("(no remote)")
            self._set_meta_label(self.upstream_label, "gray")
            self.ahead_behind_label.setText("(unknown)")
            self._set_strong_label(self.ahead_behind_label, "gray")
            self._upstream_ref = None
            return
        
        # Get default upstream ref
        upstream_ref = self._git_client.default_upstream_ref(
            repo_root, self._remote_name
        )
        self._upstream_ref = upstream_ref
        
        if not upstream_ref:
            self.upstream_label.setText("(not set)")
            self._set_meta_label(self.upstream_label, "gray")
            self.ahead_behind_label.setText("(unknown)")
            self._set_strong_label(self.ahead_behind_label, "gray")
            return
        
        # Display upstream
        self.upstream_label.setText(upstream_ref)
        self._set_meta_label(self.upstream_label, "#4db6ac")
        
        # Compute ahead/behind
        ab_result = self._git_client.ahead_behind(repo_root, upstream_ref)
        
        if ab_result["ok"]:
            ahead = ab_result["ahead"]
            behind = ab_result["behind"]
            
            self._ahead_count = ahead
            self._behind_count = behind
            
            ab_text = f"Ahead {ahead} / Behind {behind}"
            
            if ahead == 0 and behind == 0:
                self._set_strong_label(
                    self.ahead_behind_label, "green"
                )
            elif behind > 0:
                self._set_strong_label(
                    self.ahead_behind_label, "orange"
                )
            else:
                self._set_strong_label(
                    self.ahead_behind_label, "#4db6ac"
                )
            
            self.ahead_behind_label.setText(ab_text)
        else:
            self.ahead_behind_label.setText("(error)")
            self._set_strong_label(self.ahead_behind_label, "red")
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
                self._set_meta_label(self.last_fetch_label, "#4db6ac")
            except (ValueError, AttributeError):
                self.last_fetch_label.setText(last_fetch)
                self._set_meta_label(self.last_fetch_label, "#4db6ac")
        else:
            self.last_fetch_label.setText("(never)")
            self._set_meta_label(self.last_fetch_label, "gray")

    def _update_button_states(self):
        """Update enabled/disabled state of action buttons (full checks)."""
        git_ok = self._git_client.is_git_available()
        repo_ok = (
            self._current_repo_root is not None
            and self._current_repo_root != ""
        )
        upstream_ok = self._upstream_ref is not None
        changes_present = len(self._file_statuses) > 0
        busy = (
            self._is_fetching
            or self._is_pulling
            or self._is_committing
            or self._is_pushing
            or self._job_runner.is_busy()
        )

        if repo_ok:
            self._cached_has_remote = self._git_client.has_remote(
                self._current_repo_root, self._remote_name
            )

        self._update_button_states_fast()

    def _do_deferred_button_update(self):
        """Debounced callback: do fast button state update."""
        self._update_button_states_fast()

    def _update_button_states_fast(self):
        """
        Update button states using cached/local info only (no git calls).
        Called frequently during typing/UI changes.
        """
        git_ok = self._git_client.is_git_available()
        repo_ok = (
            self._current_repo_root is not None
            and self._current_repo_root != ""
        )
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

        if hasattr(self, "commit_message"):
            commit_msg_ok = bool(
                self.commit_message.toPlainText().strip()
            )

        fetch_enabled = (
            git_ok and repo_ok and self._cached_has_remote
            and not self._is_fetching
            and not self._is_pulling and not busy
        )
        self.fetch_btn.setEnabled(fetch_enabled)

        pull_enabled = (
            git_ok and repo_ok and self._cached_has_remote
            and upstream_ok
            and self._behind_count > 0 and not self._is_fetching
            and not self._is_pulling and not busy
        )
        self.pull_btn.setEnabled(pull_enabled)
        commit_enabled = (
            git_ok and repo_ok and changes_present and commit_msg_ok
            and not busy
        )
        # No separate commit button anymore; enabling handled by commit_push_btn

        commit_push_enabled = (
            git_ok and repo_ok and self._cached_has_remote and not busy
            and ((self._ahead_count > 0) or not upstream_ok)
        )
        if self._workflow_mode == 'both':
            commit_push_enabled = (
                git_ok and repo_ok and changes_present and commit_msg_ok
                and not busy
            ) or (
                git_ok and repo_ok and self._cached_has_remote and not busy
                and ((self._ahead_count > 0) or not upstream_ok)
            )
        elif self._workflow_mode == 'commit':
            commit_push_enabled = (
                git_ok and repo_ok and changes_present and commit_msg_ok
                and not busy
            )
        elif self._workflow_mode == 'push':
            commit_push_enabled = (
                git_ok and repo_ok and self._cached_has_remote and not busy
                and ((self._ahead_count > 0) or not upstream_ok)
            )
        elif self._workflow_mode == 'publish':
            # Publish mode: needs valid repo, saved doc, and remote
            doc_saved = False
            try:
                import FreeCAD
                ad = FreeCAD.ActiveDocument
                doc_saved = bool(getattr(ad, "FileName", ""))
            except Exception:
                doc_saved = False
            commit_push_enabled = (
                git_ok and repo_ok and doc_saved and self._cached_has_remote
                and not busy
            )
        
        self.commit_push_btn.setEnabled(commit_push_enabled)

        if hasattr(self, "stage_all_checkbox"):
            self.stage_all_checkbox.setEnabled(
                repo_ok and changes_present
            )

        self.changes_list.setEnabled(repo_ok)

        # Enable Generate Previews when repo is valid and a doc is saved
        doc_saved = False
        try:
            import FreeCAD
            ad = FreeCAD.ActiveDocument
            doc_saved = bool(getattr(ad, "FileName", ""))
        except Exception:
            doc_saved = False
        self.generate_previews_btn.setEnabled(
            git_ok and repo_ok and doc_saved and not busy
        )

        # Update Create Repo button visibility
        # Show when: path is specified, valid directory, but NOT a git repo
        import os
        current_path = self.repo_path_field.text()
        path_is_valid_dir = (
            current_path
            and os.path.isdir(os.path.normpath(os.path.expanduser(current_path)))
        )
        create_repo_visible = path_is_valid_dir and not repo_ok and git_ok
        self.create_repo_btn.setVisible(create_repo_visible)

        # Update Connect Remote button visibility/state
        remote_missing = repo_ok and git_ok and not self._cached_has_remote
        self.connect_remote_btn.setVisible(remote_missing)
        # Allow connecting even while other tasks might be considered busy,
        # but still require git/repo to be valid.
        self.connect_remote_btn.setEnabled(remote_missing)

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
                    "color: #4db6ac; font-size: 10px;"
                )
            self.status_message_label.show()
        else:
            self.status_message_label.hide()

    def _clear_status_message(self):
        """Clear the status message"""
        self.status_message_label.hide()

    # --- Repository browser window/dock ---

    def _create_browser_content(self):
        """Create the shared browser content widget once."""
        if self._browser_content:
            return self._browser_content

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        container.setLayout(layout)

        self.repo_info_label = QtWidgets.QLabel("Repo not selected.")
        self.repo_info_label.setWordWrap(True)
        self.repo_info_label.setStyleSheet(
            "color: gray; font-style: italic;"
        )
        layout.addWidget(self.repo_info_label)

        top_row = QtWidgets.QHBoxLayout()
        self.repo_search = QtWidgets.QLineEdit()
        self.repo_search.setPlaceholderText("Filter files…")
        self.repo_search.textChanged.connect(
            self._on_repo_search_changed
        )
        top_row.addWidget(self.repo_search)

        self.repo_refresh_btn = QtWidgets.QPushButton("Refresh Files")
        self.repo_refresh_btn.clicked.connect(
            self._on_repo_refresh_files_clicked
        )
        top_row.addWidget(self.repo_refresh_btn)
        layout.addLayout(top_row)

        self.repo_list = QtWidgets.QListWidget()
        self.repo_list.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        self.repo_list.customContextMenuRequested.connect(
            self._on_repo_list_context_menu
        )
        self.repo_list.itemDoubleClicked.connect(
            self._on_repo_item_double_clicked
        )
        self.repo_list.currentItemChanged.connect(
            self._on_repo_item_selected
        )
        layout.addWidget(self.repo_list)

        self.repo_preview_label = QtWidgets.QLabel("Select a file to preview")
        self.repo_preview_label.setAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )
        self.repo_preview_label.setMinimumHeight(180)
        self.repo_preview_label.setStyleSheet(
            "color: gray; border: 1px dashed #ccc;"
        )
        layout.addWidget(self.repo_preview_label)

        # Initial disabled state
        self.repo_search.setEnabled(False)
        self.repo_refresh_btn.setEnabled(False)
        self.repo_list.setEnabled(False)

        self._browser_content = container
        return container

    def _ensure_browser_host(self):
        """Create the dockable browser host; fallback to floating if needed."""
        if self._browser_dock:
            return self._browser_dock

        content = self._create_browser_content()

        dock = QtWidgets.QDockWidget("Repository Browser", self)
        dock.setObjectName("GitPDM_RepoBrowserDock")
        dock.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea
            | QtCore.Qt.RightDockWidgetArea
            | QtCore.Qt.BottomDockWidgetArea
        )
        dock.setFeatures(
            QtWidgets.QDockWidget.DockWidgetClosable
            | QtWidgets.QDockWidget.DockWidgetMovable
            | QtWidgets.QDockWidget.DockWidgetFloatable
        )
        dock.setWidget(content)

        main_window = None
        try:
            import FreeCADGui
            main_window = FreeCADGui.getMainWindow()
        except Exception:
            main_window = None

        if main_window:
            main_window.addDockWidget(
                QtCore.Qt.RightDockWidgetArea, dock
            )
        else:
            dock.setParent(self)
            dock.setFloating(True)

        self._browser_dock = dock
        return dock

    def _open_repo_browser(self):
        """Show the dockable repository browser (dock or floating)."""
        dock = self._ensure_browser_host()
        dock.show()
        dock.raise_()
        dock.activateWindow()

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
            # Refresh repo browser after pull
            self._refresh_repo_browser_files()
            
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

    # --- Sprint 5: Repo Browser logic ---

    def _clear_repo_browser(self):
        """Reset repo browser UI to empty state."""
        self._ensure_browser_host()
        self._all_cad_files = []
        self.repo_list.clear()
        self.repo_info_label.setText("Repo not selected.")
        self.repo_info_label.setStyleSheet(
            "color: gray; font-style: italic;"
        )
        self.repo_search.setEnabled(False)
        self.repo_refresh_btn.setEnabled(False)
        self.repo_list.setEnabled(False)

    def _on_repo_refresh_files_clicked(self):
        """Manual refresh of repo browser files."""
        self._ensure_browser_host()
        self._refresh_repo_browser_files()

    def _refresh_repo_browser_files(self):
        """
        Load tracked CAD files asynchronously using git ls-files.
        """
        self._ensure_browser_host()
        if not self._git_client.is_git_available():
            self.repo_info_label.setText("Git not available.")
            self.repo_info_label.setStyleSheet(
                "color: red; font-style: italic;"
            )
            self.repo_search.setEnabled(False)
            self.repo_refresh_btn.setEnabled(False)
            self.repo_list.setEnabled(False)
            return

        if not self._current_repo_root:
            self._clear_repo_browser()
            return

        if self._is_listing_files or self._job_runner.is_busy():
            # Avoid overlapping jobs; user can re-click later
            return

        self._is_listing_files = True
        self.repo_info_label.setText("Loading…")
        self.repo_info_label.setStyleSheet(
            "color: orange; font-style: italic;"
        )
        self.repo_search.setEnabled(False)
        self.repo_refresh_btn.setEnabled(False)
        self.repo_refresh_btn.setText("Loading…")
        self.repo_list.setEnabled(False)
        self.repo_list.clear()

        git_cmd = self._git_client._get_git_command()
        args = [git_cmd, "-C", self._current_repo_root,
                "ls-files", "-z"]

        self._job_runner.run_job(
            "list_files",
            args,
            callback=self._on_list_files_job_finished,
        )

    def _on_list_files_job_finished(self, job):
        """Process ls-files output and populate browser."""
        self._ensure_browser_host()
        self._is_listing_files = False

        result = job.get("result", {})
        success = result.get("success", False)
        stdout = result.get("stdout", "")

        self.repo_refresh_btn.setText("Refresh Files")

        if not success:
            err = result.get("stderr", "")
            self.repo_info_label.setText("Failed to list files.")
            self.repo_info_label.setStyleSheet(
                "color: red; font-style: italic;"
            )
            log.warning(f"ls-files failed: {err}")
            self.repo_search.setEnabled(True)
            self.repo_refresh_btn.setEnabled(True)
            self.repo_list.setEnabled(True)
            return

        # Parse NUL-separated entries
        tokens = [t for t in stdout.split("\0") if t]

        # Filter strictly to FreeCAD native files; the browser only opens .FCStd
        fcstd_set = []
        for p in tokens:
            name = p.rsplit("/", 1)[-1]
            name = name.rsplit("\\", 1)[-1]
            if name.lower().endswith(".fcstd"):
                fcstd_set.append(p)

        self._all_cad_files = fcstd_set
        self._apply_repo_filter_and_populate()

        self.repo_search.setEnabled(True)
        self.repo_refresh_btn.setEnabled(True)
        self.repo_list.setEnabled(True)

        if not self._all_cad_files:
            self.repo_info_label.setText("No FCStd files found.")
            self.repo_info_label.setStyleSheet(
                "color: gray; font-style: italic;"
            )
        else:
            self.repo_info_label.setText(
                f"Found {len(self._all_cad_files)} FCStd files."
            )
            self.repo_info_label.setStyleSheet(
                "color: #4db6ac; font-style: italic;"
            )

    def _on_repo_search_changed(self, _text):
        """Filter list on search text change (in-memory)."""
        self._ensure_browser_host()
        self._apply_repo_filter_and_populate()

    def _apply_repo_filter_and_populate(self):
        """Apply filter and update list widget."""
        self._ensure_browser_host()
        self.repo_list.clear()
        self._clear_repo_preview()
        q = self.repo_search.text().strip().lower()
        if not self._all_cad_files:
            return
        for rel in self._all_cad_files:
            if not q or q in rel.lower():
                self.repo_list.addItem(rel)

    def _on_repo_item_double_clicked(self, item):
        """Open double-clicked file if it's a .FCStd."""
        self._ensure_browser_host()
        rel = item.text()
        self._open_repo_file(rel)

    def _on_repo_item_selected(self, current, _previous):
        """Show preview for the selected repository item."""
        if not current:
            self._clear_repo_preview()
            return
        rel = current.text()
        self._show_repo_preview(rel)

    def _on_repo_list_context_menu(self, pos):
        """Show context menu for repo list items."""
        self._ensure_browser_host()
        item = self.repo_list.itemAt(pos)
        menu = QtWidgets.QMenu(self)

        act_open = menu.addAction("Open")
        act_reveal = menu.addAction("Reveal in Explorer/Finder")
        act_copy = menu.addAction("Copy Relative Path")

        chosen = menu.exec_(self.repo_list.mapToGlobal(pos))
        if not chosen:
            return

        rel = item.text() if item else None
        if chosen == act_copy and rel:
            QtWidgets.QApplication.clipboard().setText(rel)
            return

        if not rel:
            return

        if chosen == act_open:
            self._open_repo_file(rel)
        elif chosen == act_reveal:
            self._reveal_in_file_manager(rel)

    def _open_repo_file(self, rel):
        """Open the given repo-relative path in FreeCAD."""
        self._ensure_browser_host()
        if not self._current_repo_root:
            return
        import os
        abs_path = os.path.normpath(
            os.path.join(self._current_repo_root, rel)
        )

        # Only allow opening FCStd files
        name = abs_path.rsplit("/", 1)[-1]
        name = name.rsplit("\\", 1)[-1]
        is_fcstd = name.lower().endswith(".fcstd")
        if not is_fcstd:
            msg = QtWidgets.QMessageBox(self)
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setWindowTitle("Unsupported File Type")
            msg.setText("Only .FCStd files can be opened directly.")
            msg.exec()
            return

        if not os.path.isfile(abs_path):
            msg = QtWidgets.QMessageBox(self)
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle("File Missing")
            msg.setText(
                "File not present in working tree. Try Pull/Fetch."
            )
            msg.exec()
            return

        # Show preview (if available) even before opening
        self._show_repo_preview(rel)

        # Check for unsaved documents (MVP best-effort)
        try:
            import FreeCAD
            docs = FreeCAD.listDocuments()
            has_dirty = False
            for d in docs.values():
                # Document.Modified may exist; ignore if missing
                try:
                    if getattr(d, "Modified", False):
                        has_dirty = True
                        break
                except Exception:
                    pass
            if has_dirty:
                ask = QtWidgets.QMessageBox(self)
                ask.setIcon(QtWidgets.QMessageBox.Warning)
                ask.setWindowTitle("Unsaved Changes")
                ask.setText(
                    "There are unsaved changes. Open another file?"
                )
                ask.setStandardButtons(
                    QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Yes
                )
                res = ask.exec()
                if res != QtWidgets.QMessageBox.Yes:
                    return
        except Exception:
            # If FreeCAD API differs, proceed without blocking
            pass

        # Open document in FreeCAD
        try:
            import FreeCAD
            FreeCAD.open(abs_path)
        except Exception:
            try:
                import FreeCADGui
                FreeCADGui.open(abs_path)
            except Exception as e:
                log.error(f"Failed to open file: {e}")
                msg = QtWidgets.QMessageBox(self)
                msg.setIcon(QtWidgets.QMessageBox.Critical)
                msg.setWindowTitle("Open Failed")
                msg.setText("Could not open the file in FreeCAD.")
                msg.exec()

    def _reveal_in_file_manager(self, rel):
        """Reveal the file in the OS file manager (MVP)."""
        if not self._current_repo_root:
            return
        import os
        import sys
        import subprocess as sp
        abs_path = os.path.normpath(
            os.path.join(self._current_repo_root, rel)
        )
        folder = os.path.dirname(abs_path)

        if sys.platform.startswith("win"):
            try:
                os.startfile(folder)
            except Exception as e:
                log.error(f"Reveal failed: {e}")
        elif sys.platform == "darwin":
            try:
                sp.run(["open", "-R", abs_path], timeout=10)
            except Exception as e:
                log.error(f"Reveal failed: {e}")
        else:
            try:
                sp.run(["xdg-open", folder], timeout=10)
            except Exception as e:
                log.error(f"Reveal failed: {e}")

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

    def _do_refresh(self, path):
        """Execute the refresh operation (runs after brief delay)."""
        try:
            self._validate_repo_path(path)
        finally:
            self._stop_busy_feedback()
            self._show_status_message("Refresh complete", is_error=False)
            QtCore.QTimer.singleShot(2000, self._clear_status_message)

    def _display_working_tree_status(self, status):
        """
        Display working tree status in UI
        
        Args:
            status: dict - status summary from GitClient
        """
        if status["is_clean"]:
            self.working_tree_label.setText("Clean")
            self._set_strong_label(self.working_tree_label, "green")
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
            self._set_strong_label(self.working_tree_label, "orange")

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

    def _on_workflow_changed(self):
        """Handle workflow selection change."""
        sender = self.sender()
        
        if sender == self.workflow_action_both:
            self._workflow_mode = 'both'
        elif sender == self.workflow_action_commit:
            self._workflow_mode = 'commit'
        elif sender == self.workflow_action_push:
            self._workflow_mode = 'push'
        elif sender == self.workflow_action_publish:
            self._workflow_mode = 'publish'
        
        # Update checkmarks
        self.workflow_action_both.setChecked(
            self._workflow_mode == 'both'
        )
        self.workflow_action_commit.setChecked(
            self._workflow_mode == 'commit'
        )
        self.workflow_action_push.setChecked(
            self._workflow_mode == 'push'
        )
        self.workflow_action_publish.setChecked(
            self._workflow_mode == 'publish'
        )
        
        # Update button label and states for the new mode
        self._update_commit_push_button_default_label()
        self._update_button_states()

    def _update_commit_push_button_default_label(self):
        """Set the combined button label based on workflow mode."""
        if self._workflow_mode == 'commit':
            self.commit_push_btn.setText("Commit")
        elif self._workflow_mode == 'push':
            self.commit_push_btn.setText("Push")
        elif self._workflow_mode == 'publish':
            self.commit_push_btn.setText("Publish Branch")
        else:
            self.commit_push_btn.setText("Commit & Push")

    def _on_commit_message_changed(self):
        """Called when commit message text changes (debounced)."""
        self._button_update_timer.stop()
        self._button_update_timer.start()

    def _on_commit_push_clicked(self):
        """Handle Commit & Push / Publish button click (routes to appropriate flow)."""
        if self._workflow_mode == 'both':
            self._start_commit_push_sequence()
        elif self._workflow_mode == 'commit':
            self._on_commit_clicked()
        elif self._workflow_mode == 'push':
            self._on_push_clicked()
        elif self._workflow_mode == 'publish':
            self._on_publish_clicked()
    
    def _start_commit_push_sequence(self):
        """Start combined commit & push workflow."""
        if not self._current_repo_root:
            log.warning("No repository to commit+push")
            return

        if (
            self._is_committing
            or self._is_pushing
            or self._job_runner.is_busy()
        ):
            log.debug("Job running, commit+push ignored")
            return

        message = self.commit_message.toPlainText().strip()
        if not message:
            self._show_status_message(
                "Commit message required", is_error=True
            )
            return

        self._clear_status_message()
        self._is_committing = True
        self.commit_push_btn.setText("Committing…")
        self._pending_commit_message = message
        self._update_button_states()
        self._start_busy_feedback("Committing…")

        log.info("Starting commit & push sequence")

        git_cmd = self._git_client._get_git_command()
        args = [git_cmd, "-C", self._current_repo_root, "add", "-A"]

        self._job_runner.run_job(
            "commit_push_stage",
            args,
            callback=self._on_commit_push_stage_completed,
        )

    def _on_commit_push_stage_completed(self, job):
        """Callback after staging in commit & push sequence."""
        result = job.get("result", {})
        if not result.get("success"):
            log.warning(
                f"Stage failed: {result.get('stderr', '')}"
            )
            self._handle_commit_push_failed("Stage failed")
            return

        log.debug("Stage completed, running commit")

        if not self._current_repo_root:
            self._handle_commit_push_failed("Repository lost")
            return

        message = self._pending_commit_message
        if not message:
            self._handle_commit_push_failed("No commit message")
            return

        git_cmd = self._git_client._get_git_command()
        args = [
            git_cmd, "-C", self._current_repo_root, "commit", "-m", message
        ]

        self._job_runner.run_job(
            "commit_push_commit",
            args,
            callback=self._on_commit_push_commit_completed,
        )

    def _on_commit_push_commit_completed(self, job):
        """Callback after commit in commit & push sequence."""
        result = job.get("result", {})
        success = result.get("success", False)
        stderr = result.get("stderr", "")

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
            self._handle_commit_push_failed(
                "Commit failed, skipping push"
            )
            return

        log.info("Commit succeeded, now pushing")
        self.commit_push_btn.setText("Pushing…")
        self._is_committing = False
        self._is_pushing = True
        self._show_status_message("Pushing…", is_error=False)

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
            "commit_push_push",
            args,
            callback=self._on_commit_push_push_completed,
        )

    def _on_commit_push_push_completed(self, job):
        """Callback after push in commit & push sequence."""
        result = job.get("result", {})
        success = result.get("success", False)
        stderr = result.get("stderr", "")

        self._is_pushing = False
        self._update_commit_push_button_default_label()
        self._stop_busy_feedback()

        if not success:
            code = self._git_client._classify_push_error(stderr)
            self._show_push_error_dialog(code, stderr)
            log.warning(f"Push failed: {code}")
            self._update_button_states()
            return

        log.info("Commit & push completed successfully")

        self.commit_message.clear()

        if self._current_repo_root:
            branch = self._git_client.current_branch(
                self._current_repo_root
            )
            self.branch_label.setText(branch)

            self._refresh_status_views(self._current_repo_root)

            self._update_upstream_info(self._current_repo_root)

        self._show_status_message("Commit & push completed", is_error=False)

        QtCore.QTimer.singleShot(2000, self._clear_status_message)

        self._update_button_states()

    def _handle_commit_push_failed(self, message):
        """Handle commit & push failure."""
        self._is_committing = False
        self._is_pushing = False
        self.commit_push_btn.setText("Commit & Push")
        self._pending_commit_message = ""
        self._stop_busy_feedback()
        self._show_status_message(message, is_error=True)
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
        self.commit_push_btn.setText("Committing…")
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
        self._update_commit_push_button_default_label()
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
        self._update_commit_push_button_default_label()
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
        self.commit_push_btn.setText("Pushing…")
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
        self._update_commit_push_button_default_label()

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
        if not current_path:
            log.warning("No repository path set")
            return
        
        # Show busy feedback immediately
        self._start_busy_feedback("Refreshing…")
        self._update_operation_status("Refreshing…")
        
        # Defer the actual work to keep UI responsive
        QtCore.QTimer.singleShot(50, lambda: self._do_refresh(current_path))

    def _on_create_repo_clicked(self):
        """
        Handle Create Repo button click.
        Initialize a new git repository in the selected path.
        """
        current_path = self.repo_path_field.text()
        if not current_path:
            log.warning("No path specified for repo creation")
            self._show_status_message(
                "Error: Please specify a folder path first",
                is_error=True
            )
            return
        
        # Normalize the path
        import os
        current_path = os.path.normpath(os.path.expanduser(current_path))
        
        # Check if path exists
        if not os.path.isdir(current_path):
            log.warning(f"Path does not exist: {current_path}")
            self._show_status_message(
                f"Error: Folder does not exist: {current_path}",
                is_error=True
            )
            return
        
        # Show confirmation dialog
        dlg = QtWidgets.QMessageBox(self)
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
        self._start_busy_feedback("Creating repository…")
        self._update_operation_status("Creating repository…")
        
        # Perform the actual init in a deferred call to keep UI responsive
        QtCore.QTimer.singleShot(50, lambda: self._do_create_repo(current_path))

    def _do_create_repo(self, path):
        """Execute the actual repo creation."""
        try:
            log.info(f"Creating repository at: {path}")
            result = self._git_client.init_repo(path)
            
            if result.ok:
                log.info("Repository created successfully")
                self._show_status_message(
                    "Repository created successfully!",
                    is_error=False
                )
                
                # Show helpful next steps dialog
                dlg = QtWidgets.QMessageBox(self)
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
                    QtCore.QTimer.singleShot(50, self._on_connect_remote_clicked)
                
                # Refresh the repo validation with the new repo
                QtCore.QTimer.singleShot(500, lambda: self._validate_repo_path(path))
            else:
                log.error(f"Repository creation failed: {result.stderr}")
                self._show_status_message(
                    f"Error: Failed to create repository",
                    is_error=True
                )
        except Exception as e:
            log.error(f"Exception during repo creation: {e}")
            self._show_status_message(
                f"Error: {str(e)}",
                is_error=True
            )
        finally:
            self._stop_busy_feedback()

    def _on_connect_remote_clicked(self):
        """Entry point for Connect Remote button or prompt."""
        if not self._current_repo_root:
            self._show_status_message(
                "No repository selected", is_error=True
            )
            return
        self._start_connect_remote_flow()

    def _start_connect_remote_flow(self, url_hint=""):
        """Prompt user for remote URL and start add-remote operation."""
        remote_name = getattr(self, "_remote_name", "origin") or "origin"
        prompt_title = "Connect Remote"
        prompt_label = (
            f"Add remote '{remote_name}'.\n"
            "Paste the repository URL (GitHub Desktop will handle auth):"
        )
        url, ok = QtWidgets.QInputDialog.getText(
            self,
            prompt_title,
            prompt_label,
            text=url_hint
        )
        if not ok:
            log.info("Connect Remote cancelled")
            return

        url = url.strip()
        if not url:
            self._show_status_message("Remote URL required", is_error=True)
            return

        # Run asynchronously to keep UI responsive
        self._start_busy_feedback("Connecting remote…")
        self._update_operation_status("Connecting remote…")
        QtCore.QTimer.singleShot(
            50,
            lambda: self._do_connect_remote(remote_name, url)
        )

    def _do_connect_remote(self, remote_name, url):
        """Execute remote add and refresh UI."""
        try:
            if not self._current_repo_root:
                self._show_status_message(
                    "No repository selected", is_error=True
                )
                return

            result = self._git_client.add_remote(
                self._current_repo_root, remote_name, url
            )

            if result.ok:
                self._show_status_message(
                    "Remote connected. You can publish now.",
                    is_error=False
                )
                self._cached_has_remote = True
                # Refresh labels/status to pick up remote
                self._validate_repo_path(self._current_repo_root)
            else:
                msg = result.stderr or "Failed to add remote"
                QtWidgets.QMessageBox.critical(
                    self,
                    "Connect Remote Failed",
                    msg
                )
                self._show_status_message(
                    f"Error: {msg}", is_error=True
                )
        except Exception as e:
            log.error(f"Exception during connect remote: {e}")
            self._show_status_message(
                f"Error: {str(e)}", is_error=True
            )
        finally:
            self._stop_busy_feedback()

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
        elif job_type == "stage_previews":
            self._handle_stage_previews_result(job)

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

    # --- Sprint 6: Generate Previews ---

    def _update_preview_status_labels(self):
        ts = settings.load_last_preview_at()
        rel_dir = settings.load_last_preview_dir()
        if ts:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(ts)
                display = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                display = ts
            self.preview_status_label.setText(
                f"Last generated: {display}"
            )
            self._set_meta_label(self.preview_status_label, "#4db6ac")
        else:
            self.preview_status_label.setText(
                "Last generated: (never)"
            )
            self._set_meta_label(self.preview_status_label, "gray")
        self.open_preview_folder_btn.setEnabled(bool(rel_dir))

    def _on_open_preview_folder_clicked(self):
        rel_dir = settings.load_last_preview_dir()
        if not rel_dir or not self._current_repo_root:
            return
        abs_dir = core_paths.safe_join_repo(
            self._current_repo_root, rel_dir
        )
        if not abs_dir:
            return
        import os
        try:
            os.startfile(str(abs_dir))
        except Exception as e:
            log.warning(f"Open folder failed: {e}")

    def _on_generate_previews_clicked(self):
        if not self._current_repo_root:
            self._show_status_message(
                "Repo not selected / invalid", is_error=True
            )
            return
        try:
            import FreeCAD
            ad = FreeCAD.ActiveDocument
        except Exception:
            ad = None
        if not ad:
            self._show_status_message(
                "No active document", is_error=True
            )
            return
        file_name = getattr(ad, "FileName", "")
        if not file_name:
            self._show_status_message(
                "Document not saved", is_error=True
            )
            return
        if not core_paths.is_inside_repo(file_name, self._current_repo_root):
            self._show_status_message(
                "Document outside selected repo", is_error=True
            )
            return

        # Modal progress dialog (best-effort, keeps UI responsive)
        progress = QtWidgets.QProgressDialog(
            "Generating previews…", None, 0, 0, self
        )
        progress.setWindowTitle("GitPDM")
        progress.setModal(True)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.show()
        QtWidgets.QApplication.processEvents()

        result = exporter.export_active_document(self._current_repo_root)

        progress.close()

        if not result.ok:
            self._show_status_message(result.message or "Export failed", True)
            return

        # Update status labels and remember last output dir
        from datetime import datetime, timezone
        settings.save_last_preview_at(
            datetime.now(timezone.utc).isoformat()
        )
        if result.rel_dir:
            settings.save_last_preview_dir(result.rel_dir)
        self._update_preview_status_labels()

        # Stage outputs if enabled
        if self.stage_previews_checkbox.isChecked() and result.rel_dir:
            git_cmd = self._git_client._get_git_command()
            png_rel = result.rel_dir + "preview.png"
            json_rel = result.rel_dir + "preview.json"
            args = [
                git_cmd, "-C", self._current_repo_root,
                "add", "--", png_rel, json_rel
            ]
            self._start_busy_feedback("Staging previews…")
            self._job_runner.run_job(
                "stage_previews", args, callback=self._on_stage_previews_completed
            )
        else:
            self._show_status_message(
                "Previews generated", is_error=False
            )
            self._refresh_status_views(self._current_repo_root)
            QtCore.QTimer.singleShot(2000, self._clear_status_message)

    def _on_stage_previews_completed(self, job):
        # Handled in _handle_stage_previews_result
        pass

    def _handle_stage_previews_result(self, job):
        self._stop_busy_feedback()
        result = job.get("result", {})
        success = result.get("success", False)
        if success:
            self._show_status_message(
                "Previews generated and staged", is_error=False
            )
        else:
            self._show_status_message(
                "Staging failed; outputs kept", is_error=True
            )
            log.warning(result.get("stderr", ""))
        if self._current_repo_root:
            self._refresh_status_views(self._current_repo_root)
        QtCore.QTimer.singleShot(2000, self._clear_status_message)

    def _on_publish_clicked(self):
        """Sprint 7: Handle Publish button click (one-click workflow)."""
        if not self._current_repo_root:
            self._show_status_message(
                "Repo not selected / invalid", is_error=True
            )
            return
        
        # Check if busy
        if self._job_runner.is_busy():
            log.debug("Job running, publish ignored")
            return
        
        try:
            import FreeCAD
            ad = FreeCAD.ActiveDocument
        except Exception:
            ad = None
        if not ad:
            self._show_status_message(
                "No active document", is_error=True
            )
            return
        
        file_name = getattr(ad, "FileName", "")
        if not file_name:
            self._show_status_message(
                "Document not saved", is_error=True
            )
            return
        
        # Use commit message from the text box
        message = self.commit_message.toPlainText().strip()
        if not message:
            self._show_status_message(
                "Commit message required", is_error=True
            )
            return
        
        # Run publish workflow with progress
        self._run_publish_workflow(message)
    
    def _run_publish_workflow(self, commit_message):
        """Execute the publish workflow with progress feedback."""
        # Modal progress dialog
        progress = QtWidgets.QProgressDialog(
            "Starting publish workflow…", "Cancel", 0, 5, self
        )
        progress.setWindowTitle("GitPDM Publish")
        progress.setModal(True)
        progress.setMinimumDuration(0)
        progress.show()
        QtWidgets.QApplication.processEvents()
        
        coordinator = publish.PublishCoordinator(self._git_client)
        
        # Step 1: Precheck
        progress.setLabelText("Running preflight checks…")
        progress.setValue(0)
        QtWidgets.QApplication.processEvents()
        
        result = coordinator.precheck(self._current_repo_root)
        if not result.ok:
            progress.close()
            self._handle_publish_error(result)
            return

        precheck_details = result.details or {}
        
        # Check if behind upstream
        details = result.details or {}
        behind = details.get("behind", 0)
        if behind > 0:
            progress.close()
            choice = QtWidgets.QMessageBox.question(
                self,
                "Branch Behind Remote",
                f"Your branch is {behind} commit(s) behind the remote.\n\n"
                "Recommendation: Pull changes first to avoid conflicts.\n\n"
                "Publish anyway?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            if choice != QtWidgets.QMessageBox.Yes:
                log.info("User chose not to publish while behind")
                return
            # Reopen progress dialog
            progress = QtWidgets.QProgressDialog(
                "Continuing publish workflow…", "Cancel", 0, 5, self
            )
            progress.setWindowTitle("GitPDM Publish")
            progress.setModal(True)
            progress.setMinimumDuration(0)
            progress.show()
            QtWidgets.QApplication.processEvents()
        
        # Step 2: Export previews
        progress.setLabelText("Exporting previews (PNG + JSON + GLB)…")
        progress.setValue(1)
        QtWidgets.QApplication.processEvents()
        
        result = coordinator.export_previews(self._current_repo_root)
        if not result.ok:
            progress.close()
            self._handle_publish_error(result)
            return

        export_result = None
        if result.details:
            export_result = result.details.get("export_result")
        
        # Step 3: Stage files
        progress.setLabelText("Staging files…")
        progress.setValue(2)
        QtWidgets.QApplication.processEvents()
        
        source_path = precheck_details.get("file_name") if precheck_details else None
        result = coordinator.stage_files(
            self._current_repo_root,
            source_path,
            export_result,
            stage_all=self.stage_all_checkbox.isChecked(),
        )
        if not result.ok:
            progress.close()
            self._handle_publish_error(result)
            return
        
        # Step 4: Commit
        progress.setLabelText("Creating commit…")
        progress.setValue(3)
        QtWidgets.QApplication.processEvents()
        
        result = coordinator.commit_changes(self._current_repo_root, commit_message)
        if not result.ok:
            progress.close()
            # Special handling for NOTHING_TO_COMMIT
            if result.step == publish.PublishStep.COMMIT and "nothing" in result.message.lower():
                self._show_status_message(
                    "No changes to commit", is_error=False
                )
            else:
                self._handle_publish_error(result)
            return
        
        # Step 5: Push
        progress.setLabelText("Pushing to remote…")
        progress.setValue(4)
        QtWidgets.QApplication.processEvents()
        
        result = coordinator.push_to_remote(self._current_repo_root)
        progress.close()
        
        if not result.ok:
            self._handle_publish_error(result)
            return
        
        # Success!
        self._show_status_message(
            "Published successfully", is_error=False
        )

        # Clear commit message after successful publish
        try:
            self.commit_message.blockSignals(True)
            self.commit_message.setPlainText("")
        finally:
            try:
                self.commit_message.blockSignals(False)
            except Exception:
                pass
        self._on_commit_message_changed()
        
        # Update preview status
        from datetime import datetime, timezone
        settings.save_last_preview_at(
            datetime.now(timezone.utc).isoformat()
        )
        export_details = result.details or {}
        if export_details.get("rel_dir"):
            settings.save_last_preview_dir(export_details["rel_dir"])
        self._update_preview_status_labels()
        
        # Refresh status views
        self._refresh_status_views(self._current_repo_root)

    def _show_repo_preview(self, rel):
        """Load and display preview.png for the given repo-relative file."""
        try:
            if not hasattr(self, "repo_preview_label"):
                return
            if not self._current_repo_root:
                self._clear_repo_preview()
                return
            rel = (rel or "").strip()
            if not rel:
                self._clear_repo_preview()
                return

            preview_dir = mapper.to_preview_dir_rel(rel)
            png_rel = preview_dir + "preview.png"
            abs_png = core_paths.safe_join_repo(
                self._current_repo_root, png_rel
            )
            if not abs_png or not abs_png.exists():
                self.repo_preview_label.setText("No preview found")
                self.repo_preview_label.setPixmap(QtGui.QPixmap())
                return

            pix = QtGui.QPixmap(str(abs_png))
            if pix.isNull():
                self.repo_preview_label.setText("Preview could not be loaded")
                self.repo_preview_label.setPixmap(QtGui.QPixmap())
                return

            target = self.repo_preview_label.size() - QtCore.QSize(8, 8)
            scaled = pix.scaled(
                max(16, target.width()),
                max(16, target.height()),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
            self.repo_preview_label.setPixmap(scaled)
            self.repo_preview_label.setText("")
        except Exception as e:
            log.warning(f"Failed to load preview: {e}")
            self.repo_preview_label.setText("Preview error")
            self.repo_preview_label.setPixmap(QtGui.QPixmap())

    def _clear_repo_preview(self):
        if hasattr(self, "repo_preview_label"):
            self.repo_preview_label.setPixmap(QtGui.QPixmap())
            self.repo_preview_label.setText("Select a file to preview")
        QtCore.QTimer.singleShot(3000, self._clear_status_message)
    
    def _handle_publish_error(self, result):
        """Display publish error to user."""
        step_name = result.step.name if result.step else "Unknown"
        error_msg = result.message or "Unknown error"
        
        # Provide helpful guidance for common errors
        detailed_msg = error_msg
        if "Remote 'origin' not found" in error_msg:
            choice = QtWidgets.QMessageBox.question(
                self,
                f"Publish Failed ({step_name})",
                "No remote configured. Connect a remote now?\n\n"
                "Tip: Create the repo in GitHub Desktop, copy its URL, then paste here.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Yes
            )
            if choice == QtWidgets.QMessageBox.Yes:
                self._start_connect_remote_flow()
            else:
                self._show_status_message(
                    f"Publish failed: {step_name}", is_error=True
                )
                log.error(f"Publish failed at {step_name}: {error_msg}")
                return
            # Do not continue to generic message box if user handled prompt
            return
        
        QtWidgets.QMessageBox.critical(
            self,
            f"Publish Failed ({step_name})",
            detailed_msg
        )
        
        self._show_status_message(
            f"Publish failed: {step_name}", is_error=True
        )
        log.error(f"Publish failed at {step_name}: {error_msg}")

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
        # Initialize preview status area
        self._update_preview_status_labels()
