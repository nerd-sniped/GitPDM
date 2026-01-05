"""
GitPDM Panel UI Module
Sprint 5 Phase 1: Refactored with modular components
"""

from PySide6 import QtCore, QtGui, QtWidgets

import os
import glob
import sys
import subprocess

from freecad.gitpdm.core import log, settings, jobs
from freecad.gitpdm.git import client
from freecad.gitpdm.ui import dialogs
from freecad.gitpdm.ui.github_auth import GitHubAuthHandler
from freecad.gitpdm.ui.file_browser import FileBrowserHandler
from freecad.gitpdm.ui.fetch_pull import FetchPullHandler
from freecad.gitpdm.ui.commit_push import CommitPushHandler
from freecad.gitpdm.ui.repo_validator import RepoValidationHandler
from freecad.gitpdm.ui.branch_ops import BranchOperationsHandler
from freecad.gitpdm.ui.components import DocumentObserver, StatusWidget, RepositoryWidget, ChangesWidget
from freecad.gitpdm.export import exporter, mapper
from freecad.gitpdm.core import paths as core_paths
from freecad.gitpdm.core import publish




class GitPDMDockWidget(QtWidgets.QDockWidget):
    """
    Main GitPDM dock widget panel
    Sprint 1: Git status, validation, and controls
    """

    def __init__(self, services=None):
        super().__init__()
        self.setObjectName("GitPDM_DockWidget")
        self.setWindowTitle("Git PDM")
        self.setMinimumWidth(300)

        # Service container (Sprint 3)
        if services is None:
            from freecad.gitpdm.core.services import get_services

            services = get_services()
        self._services = services

        # Initialize git client and job runner
        self._git_client = self._services.git_client()
        self._job_runner = self._services.job_runner()
        self._job_runner.job_finished.connect(self._on_job_finished)

        # Initialize handlers (Sprint 4)
        self._github_auth = GitHubAuthHandler(self, self._services)
        self._file_browser = FileBrowserHandler(
            self, self._git_client, self._job_runner
        )
        self._fetch_pull = FetchPullHandler(self, self._git_client, self._job_runner)
        self._commit_push = CommitPushHandler(self, self._git_client, self._job_runner)
        self._repo_validator = RepoValidationHandler(self, self._git_client)
        self._branch_ops = BranchOperationsHandler(
            self, self._git_client, self._job_runner
        )
        # GitCAD lock handler (Phase 2)
        from freecad.gitpdm.ui.lock_handler import LockHandler
        self._lock_handler = LockHandler(
            self, self._git_client, self._job_runner
        )

        # State tracking
        self._current_repo_root = None
        self._upstream_ref = None
        self._ahead_count = 0
        self._behind_count = 0
        self._file_statuses = []
        self._busy_timer = QtCore.QTimer(self)
        self._busy_timer.setInterval(5000)
        self._busy_timer.timeout.connect(self._on_busy_timer_tick)
        self._busy_label = ""
        self._active_operations = (
            set()
        )  # Sprint PERF-4: Track multiple concurrent operations
        self._button_update_timer = QtCore.QTimer(self)
        self._button_update_timer.setSingleShot(True)
        self._button_update_timer.setInterval(300)
        self._button_update_timer.timeout.connect(self._do_deferred_button_update)
        self._cached_has_remote = False
        self._is_refreshing_status = (
            False  # Sprint PERF-1: prevent concurrent status refreshes
        )
        self._is_updating_upstream = (
            False  # Sprint PERF-1: prevent concurrent upstream updates
        )
        self._doc_observer = None
        self._group_git_check = None
        self._group_repo_selector = None
        self._group_status = None
        self._group_branch = None
        self._group_changes = None
        self._group_actions = None
        self._actions_extra_container = None
        self._repo_browser_container = None
        self._is_compact = False
        self._branch_combo_updating = False  # Prevent recursive combo change events

        # Font sizes for labels
        self._meta_font_size = 9
        self._strong_font_size = 11

        # Create main content widget and layout
        content_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)
        content_widget.setLayout(main_layout)

        # Build UI sections
        self._build_view_toggle(main_layout)
        
        # StatusWidget (Sprint 5 Phase 1.2)
        self._status_widget = StatusWidget(self, self._git_client, self._job_runner)
        self._status_widget.status_updated.connect(self._on_status_widget_updated)
        self._status_widget.refresh_requested.connect(self._on_status_refresh_requested)
        self._status_widget.git_status_changed.connect(self._on_git_status_changed)
        main_layout.addWidget(self._status_widget)
        
        # RepositoryWidget (Sprint 5 Phase 1.3)
        self._repository_widget = RepositoryWidget(self, self._git_client, self._job_runner)
        self._repository_widget.repository_changed.connect(self._on_repository_changed)
        self._repository_widget.browse_requested.connect(self._on_browse_clicked)
        self._repository_widget.clone_requested.connect(self._on_open_clone_repo_clicked)
        self._repository_widget.new_repo_requested.connect(self._on_new_repo_clicked)
        self._repository_widget.create_repo_requested.connect(self._on_create_repo_clicked)
        self._repository_widget.connect_remote_requested.connect(self._on_connect_remote_clicked)
        self._repository_widget.refresh_requested.connect(self._on_refresh_clicked)
        main_layout.addWidget(self._repository_widget)
        
        self._build_github_account_section(main_layout)
        self._build_branch_section(main_layout)
        
        # ChangesWidget (Sprint 5 Phase 1.4)
        self._changes_widget = ChangesWidget(self, self._git_client, self._job_runner)
        self._changes_widget.stage_all_changed.connect(lambda _: self._update_button_states())
        main_layout.addWidget(self._changes_widget)
        
        self._build_buttons_section(main_layout)
        self._build_repo_browser_section(main_layout)

        # Compact-mode commit mini section (hidden by default)
        self._build_compact_commit_section(main_layout)

        # Default to expanded view
        self._set_compact_mode(False)

        # Add stretch at bottom to push everything up
        main_layout.addStretch()

        # Wrap content in a scroll area for smaller screens
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(content_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        self.setWidget(scroll_area)

        # Load remote name
        self._remote_name = settings.load_remote_name()

        # Sprint PERF: Defer initialization as soon as possible (10ms instead of 100ms)
        # This makes the panel interactive almost immediately
        QtCore.QTimer.singleShot(10, self._deferred_initialization)

        log.info("GitPDM dock panel created")

    def _build_compact_commit_section(self, layout):
        """Build a minimal commit UI shown only in collapsed mode."""
        container = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(6, 4, 6, 0)
        row.setSpacing(6)
        container.setLayout(row)

        msg_label = QtWidgets.QLabel("What changed:")
        self._set_meta_label(msg_label, "gray")
        row.addWidget(msg_label)

        self.compact_commit_message = QtWidgets.QLineEdit()
        self.compact_commit_message.setPlaceholderText(
            "Example: Updated wheel design, Fixed bracket"
        )
        self.compact_commit_message.setToolTip(
            "Describe what you changed to help you remember later\n"
            "(Git term: 'commit message')"
        )
        self.compact_commit_message.textChanged.connect(self._on_commit_message_changed)
        row.addWidget(self.compact_commit_message, 1)

        self.compact_commit_btn = QtWidgets.QPushButton("Save Version")
        self.compact_commit_btn.setEnabled(False)
        self.compact_commit_btn.setToolTip(
            "Save a checkpoint of your current work\n"
            "(Git term: 'commit' - creates a saved snapshot)"
        )
        self.compact_commit_btn.clicked.connect(self._commit_push.commit_clicked)
        row.addWidget(self.compact_commit_btn)

        container.setVisible(False)
        layout.addWidget(container)
        self._compact_commit_container = container

    def _set_meta_label(self, label, color="gray"):
        label.setStyleSheet(f"color: {color}; font-size: {self._meta_font_size}px;")

    def _set_strong_label(self, label, color="black"):
        label.setStyleSheet(
            f"font-weight: bold; font-size: {self._strong_font_size}px; color: {color};"
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
            self.compact_toggle_btn.setText("Expand" if compact else "Collapse")
        show_full = not compact
        # Only toggle visibility for sections meant to be user-toggleable.
        # System and Branch sections are permanently hidden per current UX.
        for w in [
            getattr(self, "_group_repo_selector", None),
            getattr(self, "_group_github_account", None),
            getattr(self, "_group_status", None),
            getattr(self, "_group_changes", None),
            getattr(self, "_actions_extra_container", None),
            getattr(self, "_repo_browser_container", None),
        ]:
            if w is not None:
                w.setVisible(show_full)
        # Show compact commit mini section only when collapsed
        if hasattr(self, "_compact_commit_container"):
            self._compact_commit_container.setVisible(compact)

    def _deferred_initialization(self):
        """Run heavy initialization after panel is shown (Sprint PERF-2: fully async)."""
        try:
            # Sprint 5 Phase 1.2: Delegate git check to StatusWidget
            QtCore.QTimer.singleShot(10, self._status_widget.check_git_available)

            # Sprint PERF-2: Load saved repo path and validate in background (immediate)
            QtCore.QTimer.singleShot(20, self._load_saved_repo_path_async)

            # Register document observer to auto-refresh on save
            self._register_document_observer()

            # Load GitHub connection status (Sprint OAUTH-1) - slightly delayed
            QtCore.QTimer.singleShot(50, self._github_auth.refresh_connection_status)
            # Sprint OAUTH-2: Auto-verify identity in background with cooldown
            QtCore.QTimer.singleShot(100, self._github_auth.maybe_auto_verify_identity)

            # Check if user is editing from wrong folder (worktree mismatch) - low priority
            QtCore.QTimer.singleShot(500, self._check_for_wrong_folder_editing)

            # Start periodic working directory refresh to maintain repo folder as default
            self._start_working_directory_refresh()

            log.info("GitPDM dock panel initialized")
        except Exception as e:
            log.error(f"Deferred initialization failed: {e}")

    def _register_document_observer(self):
        """Register observer to detect document saves."""
        try:
            import FreeCAD

            if self._doc_observer is None:
                self._doc_observer = DocumentObserver(self)
                FreeCAD.addDocumentObserver(self._doc_observer)
                log.info("Document observer registered for auto-refresh")
            else:
                log.debug("Document observer already registered")
        except Exception as e:
            log.error(f"Failed to register document observer: {e}")

    def showEvent(self, event):
        """Handle panel show event - refresh working directory."""
        super().showEvent(event)
        # Reset working directory whenever panel becomes visible
        # This ensures FreeCAD's Save As always defaults to current repo
        if self._current_repo_root:
            QtCore.QTimer.singleShot(
                100,
                lambda: self._set_freecad_working_directory(self._current_repo_root),
            )

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
    
    # =========================================================================
    # Property Accessors (Sprint 5 Phase 1: Delegate to widgets)
    # =========================================================================
    
    @property
    def repo_path_field(self):
        """Access repository path field from RepositoryWidget."""
        return self._repository_widget.repo_path_field
    
    @property
    def changes_list(self):
        """Access changes list from ChangesWidget."""
        return self._changes_widget.changes_list
    
    @property
    def stage_all_checkbox(self):
        """Access stage all checkbox from ChangesWidget."""
        return self._changes_widget.stage_all_checkbox
    
    @property
    def validate_label(self):
        """Access validation label from RepositoryWidget."""
        return self._repository_widget.validate_label
    
    @property
    def repo_root_label(self):
        """Access repository root label from RepositoryWidget."""
        return self._repository_widget.repo_root_label
    
    @property
    def root_toggle_btn(self):
        """Access root toggle button from RepositoryWidget."""
        return self._repository_widget.root_toggle_btn
    
    @property
    def repo_root_row(self):
        """Access repo root row from RepositoryWidget."""
        return self._repository_widget.repo_root_row
    
    @property
    def create_repo_btn(self):
        """Access create repo button from RepositoryWidget."""
        return self._repository_widget.create_repo_btn
    
    @property
    def connect_remote_btn(self):
        """Access connect remote button from RepositoryWidget."""
        return self._repository_widget.connect_remote_btn
    
    @property
    def branch_label(self):
        """Access branch label from StatusWidget."""
        return self._status_widget.branch_label
    
    @property
    def working_tree_label(self):
        """Access working tree label from StatusWidget."""
        return self._status_widget.working_tree_label
    
    @property
    def upstream_label(self):
        """Access upstream label from StatusWidget."""
        return self._status_widget.upstream_label
    
    @property
    def ahead_behind_label(self):
        """Access ahead/behind label from StatusWidget."""
        return self._status_widget.ahead_behind_label
    
    @property
    def last_fetch_label(self):
        """Access last fetch label from StatusWidget."""
        return self._status_widget.last_fetch_label

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

                    # GitCAD export (decompress) if available (Phase 2)
                    if hasattr(self, '_lock_handler') and self._lock_handler._lock_manager:
                        try:
                            from freecad.gitpdm.export.fcstd_export import export_if_available
                            export_if_available(
                                self._current_repo_root,
                                active_path,
                                self._lock_handler._lock_manager
                            )
                        except Exception as e:
                            log.debug(f"GitCAD export skipped: {e}")

                    result = exporter.export_active_document(self._current_repo_root)
                except Exception as e_export:
                    log.warning(f"Auto preview export failed: {e_export}")
                    return

                if not result or not result.ok:
                    log.warning(
                        f"Auto preview export failed: {getattr(result, 'message', '')}"
                    )
                    return

                from datetime import datetime, timezone

                settings.save_last_preview_at(datetime.now(timezone.utc).isoformat())
                if result.rel_dir:
                    settings.save_last_preview_dir(result.rel_dir)
                self._update_preview_status_labels()

            # Defer to allow FreeCAD to finish its own save cycle
            QtCore.QTimer.singleShot(0, _do_export)
        except Exception as e:
            log.warning(f"Failed to schedule auto preview: {e}")

    def _on_status_widget_updated(self, status_info):
        """
        Callback when StatusWidget updates status.
        
        Args:
            status_info: Dict with upstream, ahead, behind counts
        """
        # Update internal state for button logic
        self._upstream_ref = status_info.get("upstream")
        self._ahead_count = status_info.get("ahead", 0)
        self._behind_count = status_info.get("behind", 0)
        
        # Trigger button state update
        self._update_button_states()
    
    def _on_status_refresh_requested(self):
        """
        Callback when StatusWidget requests refresh.
        Sprint 5 Phase 1.2: Triggered by StatusWidget refresh button.
        """
        if self._current_repo_root:
            self._refresh_status_views(self._current_repo_root)
    
    def _on_git_status_changed(self, is_available):
        """
        Callback when git availability changes.
        
        Args:
            is_available: True if git is available
        """
        if not is_available:
            log.warning("Git not available on PATH")
    
    def _on_repository_changed(self, path):
        """
        Callback when repository path changes.
        Sprint 5 Phase 1.3: Handle RepositoryWidget path changes.
        Sprint 7: Auto-initialize GitPDM if not already configured.
        
        Args:
            path: New repository path
        """
        # Auto-initialize GitPDM if needed (Sprint 7)
        if path:
            from freecad.gitpdm.ui.init_wizard import auto_initialize_if_needed
            was_initialized = auto_initialize_if_needed(path)
            if was_initialized:
                log.info(f"Auto-initialized GitPDM for repository: {path}")
                # Refresh lock handler availability
                if hasattr(self, '_lock_handler'):
                    self._lock_handler.check_availability(path)
        
        # Trigger validation
        self._validate_repo_path_async()
    
    def _build_github_account_section(self, layout):
        """
        Build the GitHub Account section (Sprint OAUTH-1)
        Shows connection status and connect/disconnect buttons.
        Implements OAuth Device Flow workflow.

        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("GitHub Account")
        group_layout = QtWidgets.QVBoxLayout()
        group_layout.setContentsMargins(6, 4, 6, 4)
        group_layout.setSpacing(4)
        group.setLayout(group_layout)

        # Connection status label
        self.github_status_label = QtWidgets.QLabel("GitHub: Not connected")
        self._set_strong_label(self.github_status_label, "gray")
        group_layout.addWidget(self.github_status_label)

        # Check if OAuth is configured
        try:
            from freecad.gitpdm.auth import config as auth_config

            client_id = auth_config.get_client_id()
            oauth_configured = client_id is not None
        except Exception:
            oauth_configured = False

        # Config hint (shown if OAuth not configured)
        if not oauth_configured:
            hint_label = QtWidgets.QLabel("GitHub OAuth not configured. See docs.")
            hint_label.setWordWrap(True)
            hint_label.setStyleSheet(
                "color: orange; font-style: italic; font-size: 9px;"
            )
            group_layout.addWidget(hint_label)

        # Buttons row
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setSpacing(4)

        self.github_connect_btn = QtWidgets.QPushButton("Connect GitHub")
        self.github_connect_btn.setEnabled(oauth_configured)
        self.github_connect_btn.setToolTip(
            "Connect to GitHub using OAuth Device Flow"
            if oauth_configured
            else "OAuth not configured"
        )
        self.github_connect_btn.clicked.connect(self._on_github_connect_clicked)
        buttons_layout.addWidget(self.github_connect_btn)

        self.github_disconnect_btn = QtWidgets.QPushButton("Disconnect")
        self.github_disconnect_btn.setEnabled(False)
        self.github_disconnect_btn.setToolTip("Disconnect GitHub account")
        self.github_disconnect_btn.clicked.connect(self._on_github_disconnect_clicked)
        buttons_layout.addWidget(self.github_disconnect_btn)

        self.github_refresh_btn = QtWidgets.QPushButton("Verify / Refresh Account")
        self.github_refresh_btn.setEnabled(oauth_configured)
        self.github_refresh_btn.setToolTip("Verify GitHub account and refresh session")
        self.github_refresh_btn.clicked.connect(self._on_github_verify_clicked)
        buttons_layout.addWidget(self.github_refresh_btn)

        group_layout.addLayout(buttons_layout)

        layout.addWidget(group)
        self._group_github_account = group

    def _build_branch_section(self, layout):
        """
        Build the branch management section with selector and actions.

        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("Branch")
        group_layout = QtWidgets.QVBoxLayout()
        group_layout.setContentsMargins(6, 4, 6, 4)
        group_layout.setSpacing(4)
        group.setLayout(group_layout)

        # Branch selector row
        selector_layout = QtWidgets.QHBoxLayout()
        selector_layout.setSpacing(4)

        selector_layout.addWidget(QtWidgets.QLabel("Current:"))

        self.branch_combo = QtWidgets.QComboBox()
        self.branch_combo.setMinimumWidth(120)
        self.branch_combo.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        self.branch_combo.currentIndexChanged.connect(
            self._branch_ops.branch_combo_changed
        )
        selector_layout.addWidget(self.branch_combo)

        group_layout.addLayout(selector_layout)

        # Action buttons row
        actions_layout = QtWidgets.QHBoxLayout()
        actions_layout.setSpacing(4)

        self.new_branch_btn = QtWidgets.QPushButton("New Work Version…")
        self.new_branch_btn.setToolTip(
            "Create a new version to try different design ideas\n"
            "(Like creating a new save file in a video game)\n\n"
            "Git term: 'branch' - an independent line of development"
        )
        self.new_branch_btn.clicked.connect(self._branch_ops.new_branch_clicked)
        actions_layout.addWidget(self.new_branch_btn)

        self.switch_branch_btn = QtWidgets.QPushButton("Switch Version")
        self.switch_branch_btn.setToolTip(
            "Switch to a different work version\n"
            "(Like loading a different save file)\n\n"
            "Git term: 'checkout' or 'switch' - changes which branch you're working on"
        )
        self.switch_branch_btn.clicked.connect(self._branch_ops.switch_branch_clicked)
        actions_layout.addWidget(self.switch_branch_btn)

        self.delete_branch_btn = QtWidgets.QPushButton("Delete Version…")
        self.delete_branch_btn.setToolTip(
            "Permanently delete a work version you no longer need\n"
            "(Can't be undone - be careful!)\n\n"
            "Git term: 'delete branch' - removes a branch permanently"
        )
        self.delete_branch_btn.clicked.connect(self._branch_ops.delete_branch_clicked)
        actions_layout.addWidget(self.delete_branch_btn)

        group_layout.addLayout(actions_layout)

        worktree_help_layout = QtWidgets.QHBoxLayout()
        worktree_help_layout.addStretch()
        self.worktree_help_btn = QtWidgets.QPushButton("About Work Versions")
        self.worktree_help_btn.setToolTip(
            "Learn how to keep each work version in its own folder\n"
            "to prevent file corruption (recommended for complex projects)\n\n"
            "Git term: 'worktree' - gives each branch its own directory"
        )
        self.worktree_help_btn.clicked.connect(self._branch_ops.worktree_help_clicked)
        worktree_help_layout.addWidget(self.worktree_help_btn)
        group_layout.addLayout(worktree_help_layout)

        layout.addWidget(group)
        # Hide the entire Branch section per request
        group.setVisible(False)
        self._group_branch = group

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
        self.fetch_btn = QtWidgets.QPushButton("Check for Updates")
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setToolTip(
            "Check if your team has shared new changes on GitHub\n"
            "(Git term: 'fetch' - downloads info about remote changes without applying them)"
        )
        self.fetch_btn.clicked.connect(self._fetch_pull.fetch_clicked)
        row1_layout.addWidget(self.fetch_btn)

        self.pull_btn = QtWidgets.QPushButton("Get Updates")
        self.pull_btn.setEnabled(False)
        self.pull_btn.setToolTip(
            "Download and apply changes from your team\n"
            "(Git term: 'pull' - combines fetch + merge to update your local files)"
        )
        self.pull_btn.clicked.connect(self._fetch_pull.pull_clicked)
        row1_layout.addWidget(self.pull_btn)

        group_layout.addLayout(row1_layout)

        # Extra actions are grouped for easy hide/show in compact mode
        self._actions_extra_container = QtWidgets.QWidget()
        extra_layout = QtWidgets.QVBoxLayout()
        extra_layout.setContentsMargins(0, 0, 0, 0)
        extra_layout.setSpacing(4)
        self._actions_extra_container.setLayout(extra_layout)

        msg_label = QtWidgets.QLabel("Describe what you changed:")
        msg_label.setStyleSheet("font-weight: bold;")
        msg_label.setToolTip(
            "Write a short description to help you and your team remember what changed\n"
            "(Git term: 'commit message' - describes what's in this checkpoint)"
        )
        extra_layout.addWidget(msg_label)

        self.commit_message = QtWidgets.QPlainTextEdit()
        self.commit_message.setPlaceholderText(
            "Example: Updated wheel design, Fixed mounting bracket dimensions, Added new parts..."
        )
        self.commit_message.setMaximumHeight(70)
        self.commit_message.setToolTip(
            "Describe what you changed in this version. Be specific so you can find this version later!\n"
            "(This creates a 'commit' - a saved checkpoint in your project's history)"
        )
        self.commit_message.textChanged.connect(self._on_commit_message_changed)
        extra_layout.addWidget(self.commit_message)

        row2_layout = QtWidgets.QHBoxLayout()
        row2_layout.setSpacing(4)

        # Combined Commit & Push button (regular push button)
        self.commit_push_btn = QtWidgets.QPushButton("Commit and Push")
        self.commit_push_btn.setEnabled(False)
        self.commit_push_btn.setToolTip(
            "Save your work and share it with your team on GitHub\n"
            "(Git terms: 'commit' = save checkpoint, 'push' = upload to GitHub)"
        )
        self.commit_push_btn.clicked.connect(self._commit_push.commit_push_clicked)

        # Dropdown menu for workflow selection
        self.workflow_menu = QtWidgets.QMenu(self)
        self.workflow_action_both = self.workflow_menu.addAction(
            "Save & Share (recommended)"
        )
        self.workflow_action_both.setCheckable(True)
        self.workflow_action_both.setChecked(True)
        self.workflow_action_both.triggered.connect(self._on_workflow_changed)
        self.workflow_action_commit = self.workflow_menu.addAction(
            "Save Only (don't share yet)"
        )
        self.workflow_action_commit.setCheckable(True)
        self.workflow_action_commit.triggered.connect(self._on_workflow_changed)
        self.workflow_action_push = self.workflow_menu.addAction(
            "Share Only (already saved)"
        )
        self.workflow_action_push.setCheckable(True)
        self.workflow_action_push.triggered.connect(self._on_workflow_changed)

        self._workflow_mode = "both"

        # Dropdown menu button (plain QPushButton to avoid duplicate indicators)
        workflow_menu_btn = QtWidgets.QPushButton("▼")
        workflow_menu_btn.setAutoDefault(False)
        workflow_menu_btn.setDefault(False)
        workflow_menu_btn.setFlat(True)
        workflow_menu_btn.setFixedWidth(24)
        workflow_menu_btn.setToolTip(
            "Select workflow: Commit and Push (recommended), Commit only, or Push only"
        )
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

        # Sprint 6: Generate Previews workflow
        previews_group = QtWidgets.QGroupBox("Previews")
        pg_layout = QtWidgets.QVBoxLayout()
        pg_layout.setContentsMargins(6, 4, 6, 4)
        pg_layout.setSpacing(4)
        previews_group.setLayout(pg_layout)

        rowp = QtWidgets.QHBoxLayout()
        rowp.setSpacing(4)
        self.generate_previews_btn = QtWidgets.QPushButton("Generate Previews")
        self.generate_previews_btn.setEnabled(False)
        self.generate_previews_btn.clicked.connect(self._on_generate_previews_clicked)
        rowp.addWidget(self.generate_previews_btn)

        self.stage_previews_checkbox = QtWidgets.QCheckBox(
            "Stage preview files after export"
        )
        self.stage_previews_checkbox.setChecked(
            settings.load_stage_previews_default_on()
        )
        self.stage_previews_checkbox.stateChanged.connect(
            lambda _: settings.save_stage_previews(
                self.stage_previews_checkbox.isChecked()
            )
        )
        rowp.addWidget(self.stage_previews_checkbox)
        rowp.addStretch()
        pg_layout.addLayout(rowp)

        # Status area
        status_row = QtWidgets.QHBoxLayout()
        status_row.setSpacing(6)
        self.preview_status_label = QtWidgets.QLabel("Last generated: (never)")
        self._set_meta_label(self.preview_status_label, "gray")
        status_row.addWidget(self.preview_status_label)
        status_row.addStretch()
        self.open_preview_folder_btn = QtWidgets.QPushButton("Open Folder")
        self.open_preview_folder_btn.setEnabled(False)
        self.open_preview_folder_btn.clicked.connect(
            self._on_open_preview_folder_clicked
        )
        status_row.addWidget(self.open_preview_folder_btn)
        pg_layout.addLayout(status_row)

        # Hide the entire Previews area per request
        previews_group.setVisible(False)
        extra_layout.addWidget(previews_group)

        # GitCAD Lock Management (Phase 2)
        gitcad_group = QtWidgets.QGroupBox("GitCAD File Locking")
        gitcad_layout = QtWidgets.QVBoxLayout()
        gitcad_layout.setContentsMargins(6, 4, 6, 4)
        gitcad_layout.setSpacing(4)
        gitcad_group.setLayout(gitcad_layout)

        # Status label
        self.gitcad_status_label = QtWidgets.QLabel("Checking...")
        self._set_meta_label(self.gitcad_status_label, "gray")
        gitcad_layout.addWidget(self.gitcad_status_label)

        # Buttons row - for when GitCAD is available
        gitcad_btn_row = QtWidgets.QHBoxLayout()
        gitcad_btn_row.setSpacing(4)

        self.show_locks_btn = QtWidgets.QPushButton("Show Locks")
        self.show_locks_btn.setEnabled(False)
        self.show_locks_btn.setToolTip("Show all currently locked files")
        self.show_locks_btn.clicked.connect(self._on_show_locks_clicked)
        gitcad_btn_row.addWidget(self.show_locks_btn)

        self.refresh_locks_btn = QtWidgets.QPushButton("↻")
        self.refresh_locks_btn.setEnabled(False)
        self.refresh_locks_btn.setFixedWidth(32)
        self.refresh_locks_btn.setToolTip("Refresh lock status")
        self.refresh_locks_btn.clicked.connect(self._on_refresh_locks_clicked)
        gitcad_btn_row.addWidget(self.refresh_locks_btn)
        
        self.config_gitcad_btn = QtWidgets.QPushButton("⚙")
        self.config_gitcad_btn.setEnabled(False)
        self.config_gitcad_btn.setFixedWidth(32)
        self.config_gitcad_btn.setToolTip("Configure GitCAD settings")
        self.config_gitcad_btn.clicked.connect(self._on_config_gitcad_clicked)
        gitcad_btn_row.addWidget(self.config_gitcad_btn)

        gitcad_btn_row.addStretch()
        gitcad_layout.addLayout(gitcad_btn_row)
        
        # Initialize button - for when GitCAD is not available
        init_btn_row = QtWidgets.QHBoxLayout()
        init_btn_row.setSpacing(4)
        
        self.init_gitcad_btn = QtWidgets.QPushButton("Initialize GitCAD...")
        self.init_gitcad_btn.setToolTip("Install GitCAD file locking in this repository")
        self.init_gitcad_btn.clicked.connect(self._on_init_gitcad_clicked)
        init_btn_row.addWidget(self.init_gitcad_btn)
        
        init_btn_row.addStretch()
        self._gitcad_init_row = init_btn_row
        gitcad_layout.addLayout(init_btn_row)

        # Hide by default until GitCAD is detected
        gitcad_group.setVisible(False)
        self._lock_group = gitcad_group
        extra_layout.addWidget(gitcad_group)

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
        self._file_browser.ensure_browser_host()

        container = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(6, 4, 6, 4)
        row.setSpacing(4)
        container.setLayout(row)

        label = QtWidgets.QLabel("Repository Browser")
        self._set_meta_label(label, "gray")
        row.addWidget(label)
        row.addStretch()

        self.browser_window_btn = QtWidgets.QPushButton("Open Browser")
        self.browser_window_btn.setEnabled(False)
        self.browser_window_btn.clicked.connect(self._file_browser.open_browser)
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
            QtWidgets.QFileDialog.ShowDirsOnly,
        )

        if folder:
            self.repo_path_field.setText(folder)
            # Trigger validation
            self._validate_repo_path(folder)
            log.info(f"Selected repo folder: {folder}")

    def _on_open_clone_repo_clicked(self):
        """Open repo picker dialog to select and clone GitHub repo."""
        try:
            from freecad.gitpdm.ui.repo_picker import RepoPickerDialog

            dlg = RepoPickerDialog(
                parent=self,
                job_runner=self._job_runner,
                git_client=self._git_client,
                client_factory=self._create_github_client,
                on_connect_requested=self._on_github_connect_clicked,
                default_clone_dir=settings.load_default_clone_dir(),
            )

            if dlg.exec():
                cloned_path = dlg.cloned_path()
                if cloned_path:
                    settings.save_repo_path(cloned_path)
                    self.repo_path_field.setText(cloned_path)
                    self._validate_repo_path(cloned_path)

                    # Offer to open the cloned folder
                    self._show_repo_opened_dialog(cloned_path, "cloned")

                    # Ensure working directory is set immediately after dialog
                    # Use delayed calls to ensure it happens after all UI updates complete
                    if self._current_repo_root:
                        self._set_freecad_working_directory(self._current_repo_root)
                        # Also set with delays to override any FreeCAD resets
                        QtCore.QTimer.singleShot(
                            100,
                            lambda: self._set_freecad_working_directory(
                                self._current_repo_root
                            ),
                        )
                        QtCore.QTimer.singleShot(
                            500,
                            lambda: self._set_freecad_working_directory(
                                self._current_repo_root
                            ),
                        )
        except Exception as e:
            log.error(f"Open/Clone flow failed: {e}")
            QtWidgets.QMessageBox.warning(
                self,
                "Open/Clone Repo",
                "Failed to open repo picker. See logs for details.",
            )

    def _on_new_repo_clicked(self):
        """Open New Repo wizard to create GitHub repo + local scaffold."""
        try:
            from freecad.gitpdm.ui.new_repo_wizard import NewRepoWizard

            # Check if user is connected to GitHub
            api_client = self._create_github_client()
            if not api_client:
                log.info("Not connected to GitHub; prompting connect")
                self._on_github_connect_clicked()
                api_client = self._create_github_client()
                if not api_client:
                    QtWidgets.QMessageBox.information(
                        self,
                        "New Repository",
                        "Please connect to GitHub first.",
                    )
                    return

            wizard = NewRepoWizard(api_client=api_client, parent=self)
            if wizard.exec():
                repo_path = wizard.get_created_repo_path()
                repo_name = wizard.get_created_repo_name()
                if repo_path:
                    log.info(f"New repo created: {repo_name} at {repo_path}")
                    # Switch to the new repo
                    settings.save_repo_path(repo_path)
                    self.repo_path_field.setText(repo_path)
                    self._validate_repo_path(repo_path)

                    # Show success dialog with option to open folder
                    self._show_repo_opened_dialog(repo_path, "created", repo_name)

                    # Ensure working directory is set immediately after dialog
                    # Use delayed call to ensure it happens after all UI updates complete
                    if self._current_repo_root:
                        self._set_freecad_working_directory(self._current_repo_root)
                        # Also set with a delay to override any FreeCAD resets
                        QtCore.QTimer.singleShot(
                            100,
                            lambda: self._set_freecad_working_directory(
                                self._current_repo_root
                            ),
                        )
                        QtCore.QTimer.singleShot(
                            500,
                            lambda: self._set_freecad_working_directory(
                                self._current_repo_root
                            ),
                        )
        except Exception as e:
            log.error(f"New repo wizard failed: {e}")
            QtWidgets.QMessageBox.critical(
                self,
                "Create New Repository",
                f"Failed to create repository. See logs for details.\n\n{e}",
            )

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
        self.root_toggle_btn.setText("Hide root" if checked else "Show root")

    def _validate_repo_path(self, path):
        """Validate repository path - delegated to RepoValidationHandler."""
        self._repo_validator.validate_repo_path(path)

    def _fetch_branch_and_status(self, repo_root):
        """Fetch branch and status - delegated to RepoValidationHandler."""
        self._repo_validator.fetch_branch_and_status(repo_root)

    def _update_upstream_info(self, repo_root):
        """
        Update upstream ref and ahead/behind counts (delegated to StatusWidget).
        Sprint 5 Phase 1.2: Simplified - StatusWidget handles UI updates.

        Args:
            repo_root: str - repository root path
        """
        if not repo_root:
            return
        
        # Check remote status (fast, local operation)
        self._cached_has_remote = self._git_client.has_remote(
            repo_root, self._remote_name
        )
        
        # Delegate to StatusWidget
        self._status_widget.update_upstream_info(repo_root)

    # ========== Fetch/Pull Operations (Sprint 4: Delegated to FetchPullHandler) ==========
    # Fetch and pull operations fully delegated to self._fetch_pull handler

    def _update_button_states(self):
        """Update enabled/disabled state of action buttons (uses cached values only)."""
        # Sprint PERF-1: Removed synchronous has_remote() call - use cached value
        # Remote status is updated by _update_upstream_info() in background
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
        repo_ok = self._current_repo_root is not None and self._current_repo_root != ""
        upstream_ok = self._upstream_ref is not None
        changes_present = len(self._file_statuses) > 0
        commit_msg_ok = False
        busy = (
            self._fetch_pull.is_busy()
            or self._commit_push.is_busy()
            or self._job_runner.is_busy()
        )

        if hasattr(self, "commit_message"):
            commit_msg_ok = bool(self.commit_message.toPlainText().strip())
        # Also consider compact commit message when present
        if hasattr(self, "compact_commit_message") and not commit_msg_ok:
            commit_msg_ok = bool(self.compact_commit_message.text().strip())

        fetch_enabled = git_ok and repo_ok and self._cached_has_remote and not busy
        self.fetch_btn.setEnabled(fetch_enabled)

        pull_enabled = (
            git_ok
            and repo_ok
            and self._cached_has_remote
            and upstream_ok
            and self._behind_count > 0
            and not busy
        )
        self.pull_btn.setEnabled(pull_enabled)
        commit_enabled = (
            git_ok and repo_ok and changes_present and commit_msg_ok and not busy
        )
        # Enable compact commit button in collapsed mode
        if hasattr(self, "compact_commit_btn"):
            self.compact_commit_btn.setEnabled(
                git_ok and repo_ok and changes_present and commit_msg_ok and not busy
            )

        commit_push_enabled = (
            git_ok
            and repo_ok
            and self._cached_has_remote
            and not busy
            and ((self._ahead_count > 0) or not upstream_ok)
        )
        if self._workflow_mode == "both":
            commit_push_enabled = (
                git_ok and repo_ok and changes_present and commit_msg_ok and not busy
            ) or (
                git_ok
                and repo_ok
                and self._cached_has_remote
                and not busy
                and ((self._ahead_count > 0) or not upstream_ok)
            )
        elif self._workflow_mode == "commit":
            commit_push_enabled = (
                git_ok and repo_ok and changes_present and commit_msg_ok and not busy
            )
        elif self._workflow_mode == "push":
            commit_push_enabled = (
                git_ok
                and repo_ok
                and self._cached_has_remote
                and not busy
                and ((self._ahead_count > 0) or not upstream_ok)
            )

        self.commit_push_btn.setEnabled(commit_push_enabled)

        if hasattr(self, "stage_all_checkbox"):
            self.stage_all_checkbox.setEnabled(repo_ok and changes_present)

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
        path_is_valid_dir = current_path and os.path.isdir(
            os.path.normpath(os.path.expanduser(current_path))
        )
        create_repo_visible = path_is_valid_dir and not repo_ok and git_ok
        self.create_repo_btn.setVisible(create_repo_visible)

        # Update Connect Remote button visibility/state
        remote_missing = repo_ok and git_ok and not self._cached_has_remote
        self.connect_remote_btn.setVisible(remote_missing)
        # Allow connecting even while other tasks might be considered busy,
        # but still require git/repo to be valid.

        # Update branch button states
        self._update_branch_button_states()
        self.connect_remote_btn.setEnabled(remote_missing)

    def _show_status_message(self, message, is_error=True):
        """
        Show a status message in the status section.
        Sprint 5 Phase 1.2: Delegated to StatusWidget.

        Args:
            message: str - message to display
            is_error: bool - whether this is an error message
        """
        self._status_widget.show_status_message(message, is_error)

    def _clear_status_message(self):
        """
        Clear the status message.
        Sprint 5 Phase 1.2: Delegated to StatusWidget.
        """
        self._status_widget.clear_status_message()

    # --- Repository browser window/dock ---

    # ========== File Browser (Sprint 4: Delegated to FileBrowserHandler) ==========
    # Browser UI creation and management delegated to self._file_browser

    def _refresh_branch_list(self):
        """Update the branch list in the combo box (delegates to handler)."""
        self._branch_ops.refresh_branch_list()

    def _update_branch_button_states(self):
        """Update enabled/disabled state of branch action buttons (delegates to handler)."""
        self._branch_ops.update_branch_button_states()

    def _show_repo_opened_dialog(
        self, repo_path: str, action: str, repo_name: str = None
    ):
        """
        Show success dialog after cloning or creating a repo, with option to open folder.

        Args:
            repo_path: Absolute path to the repo
            action: "cloned" or "created"
            repo_name: Repository name (optional, for created repos)
        """
        msg_box = QtWidgets.QMessageBox(self)

        if action == "created":
            title = "Repository Created"
            if repo_name:
                msg = (
                    f"✓ Repository '{repo_name}' has been created!\n\n"
                    f"Path: {repo_path}\n\n"
                    "GitPDM is now configured to work with this repository.\n\n"
                    "Click 'Open Folder' below to view the repository in File Explorer."
                )
            else:
                msg = (
                    f"✓ Repository has been created!\n\n"
                    f"Path: {repo_path}\n\n"
                    "GitPDM is now configured to work with this repository.\n\n"
                    "Click 'Open Folder' below to view the repository in File Explorer."
                )
        else:  # cloned
            title = "Repository Cloned"
            msg = (
                f"✓ Repository has been cloned successfully!\n\n"
                f"Path: {repo_path}\n\n"
                "GitPDM is now configured to work with this repository.\n\n"
                "Click 'Open Folder' below to view the repository in File Explorer."
            )

        msg_box.setWindowTitle(title)
        msg_box.setIcon(QtWidgets.QMessageBox.Information)
        msg_box.setText(msg)

        # Add custom buttons
        open_btn = msg_box.addButton("Open Folder", QtWidgets.QMessageBox.AcceptRole)
        close_btn = msg_box.addButton("Close", QtWidgets.QMessageBox.RejectRole)
        msg_box.setDefaultButton(open_btn)

        msg_box.exec_()

        if msg_box.clickedButton() == open_btn:
            self._open_folder_in_explorer(repo_path)

    def _open_folder_in_explorer(self, folder_path: str):
        """Open folder in Windows Explorer or equivalent."""
        import sys
        import subprocess

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
                self,
                "Cannot Open Folder",
                f"Could not open folder in file explorer:\n{e}",
            )

    def _check_for_wrong_folder_editing(self):
        """Check if user has FreeCAD documents open from a different folder than current repo root."""
        if not self._current_repo_root:
            return

        try:
            import FreeCAD

            list_docs = getattr(FreeCAD, "listDocuments", None)
            if not callable(list_docs):
                return

            # Get current repo root (normalized)
            current_root = os.path.normcase(os.path.normpath(self._current_repo_root))

            # Find any open .FCStd files that are NOT in the current repo root
            wrong_folder_docs = []
            for doc in list_docs().values():
                path = getattr(doc, "FileName", "") or ""
                if not path or not path.lower().endswith(".fcstd"):
                    continue

                path_norm = os.path.normcase(os.path.normpath(path))
                # If document is from a different folder entirely, warn
                if not path_norm.startswith(current_root):
                    wrong_folder_docs.append(path)

            if wrong_folder_docs:
                doc_list = "\n".join(f"  • {d}" for d in wrong_folder_docs[:5])
                if len(wrong_folder_docs) > 5:
                    doc_list += f"\n  ... and {len(wrong_folder_docs) - 5} more"

                msg = (
                    "⚠️ WRONG FOLDER DETECTED\n\n"
                    "You have FreeCAD documents open from a different folder than the current repo:\n\n"
                    f"{doc_list}\n\n"
                    f"Current GitPDM repo: {self._current_repo_root}\n\n"
                    "This can cause file corruption when switching branches!\n\n"
                    "To avoid corruption:\n"
                    "1. Close these documents\n"
                    "2. Open files from the current worktree folder shown above\n"
                    "3. Use 'Open Folder' button after creating worktrees"
                )

                QtWidgets.QMessageBox.warning(
                    self, "Wrong Folder - Risk of Corruption", msg
                )
                log.warning(
                    f"User has {len(wrong_folder_docs)} documents open from wrong folder"
                )

        except Exception as e:
            log.debug(f"Could not check for wrong folder editing: {e}")

    def _get_open_repo_documents(self):
        """
        Return list of open FreeCAD documents that live inside the current repo.

        CRITICAL: This checks for .FCStd files from the CURRENT repo root only.
        For worktree safety, use _get_all_open_fcstd_documents() to check ALL open files.
        """
        try:
            import FreeCAD

            list_docs = getattr(FreeCAD, "listDocuments", None)
            if not callable(list_docs):
                return []
        except Exception:
            return []

        if not self._current_repo_root:
            return []

        repo_root_norm = os.path.normcase(os.path.normpath(self._current_repo_root))
        open_paths = []
        try:
            for doc in list_docs().values():
                path = getattr(doc, "FileName", "") or ""
                if not path:
                    continue
                try:
                    path_norm = os.path.normcase(os.path.normpath(path))
                    if path_norm.startswith(repo_root_norm):
                        open_paths.append(path)
                except Exception:
                    continue
        except Exception:
            return []
        return open_paths

    def _start_working_directory_refresh(self):
        """Start periodic timer to maintain repo folder as FreeCAD's working directory."""
        if not hasattr(self, "_wd_refresh_timer"):
            self._wd_refresh_timer = QtCore.QTimer(self)
            self._wd_refresh_timer.timeout.connect(self._refresh_working_directory)
            # Refresh every 2 seconds to aggressively maintain working directory
            # This ensures FreeCAD's Save As dialog always defaults to current repo
            self._wd_refresh_timer.start(2000)
            log.debug("Started working directory refresh timer (2s interval)")

    def _set_freecad_working_directory(self, directory: str):
        """
        Set FreeCAD's working directory to ensure Save As dialog defaults to repo folder.

        This prevents users from accidentally saving files outside the repo.
        Delegates to repo_validator for the actual implementation.

        Args:
            directory: Absolute path to set as working directory
        """
        self._repo_validator._set_freecad_working_directory(directory)

    def _refresh_working_directory(self):
        """Periodic refresh of working directory to maintain repo folder as default."""
        if self._current_repo_root:
            try:
                # Always set the working directory, don't check for drift
                # This ensures FreeCAD's file dialogs always default to current repo
                # even if FreeCAD internally changes directories
                self._set_freecad_working_directory(self._current_repo_root)
            except Exception as e:
                log.debug(f"Working directory refresh error: {e}")

    def _refresh_after_branch_operation(self):
        """Refresh UI after branch operations (delegates to handler)."""
        self._branch_ops.refresh_after_branch_operation()

    # Fetch/pull button handlers delegated to self._fetch_pull

    def _update_operation_status(self, status_text):
        """
        Update the operation status (currently uses status bar only).

        Args:
            status_text: str - status message
        """
        # Status is shown via _show_status_message in _start_busy_feedback
        # No dedicated operation_status_label widget exists
        pass

    def _start_busy_feedback(self, label, operation_id=None):
        """Show progress indicator and periodic status updates (Sprint PERF-4: enhanced)."""
        self._busy_label = label

        # Sprint PERF-4: Track operation for better state management
        if operation_id:
            self._active_operations.add(operation_id)

        if hasattr(self, "busy_bar"):
            self.busy_bar.show()
        self._update_operation_status(label)
        self._busy_timer.start()
        self._show_status_message(label, is_error=False)

    def _stop_busy_feedback(self, operation_id=None):
        """Hide progress indicator and stop timer (Sprint PERF-4: enhanced)."""
        # Sprint PERF-4: Remove operation from tracking
        if operation_id and operation_id in self._active_operations:
            self._active_operations.discard(operation_id)

        # Only hide busy UI if no operations are active
        if not self._active_operations:
            try:
                QtCore.QMetaObject.invokeMethod(
                    self._busy_timer,
                    "stop",
                    QtCore.Qt.QueuedConnection,
                )
            except Exception:
                # Fallback if queued invocation is unavailable
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
        """Return UI to Ready after a short delay if idle (Sprint PERF-4: enhanced)."""

        def _to_ready():
            # Sprint PERF-4: Check all operation states including active_operations
            if not (
                self._fetch_pull.is_busy()
                or self._commit_push.is_busy()
                or self._job_runner.is_busy()
                or self._active_operations  # Check tracked operations
                or self._branch_ops._is_switching_branch
                or self._branch_ops._is_loading_branches
            ):
                self._update_operation_status(status_text)

        QtCore.QTimer.singleShot(delay_ms, _to_ready)

    def _display_working_tree_status(self, status):
        """
        Display working tree status in UI.
        Sprint 5 Phase 1.2: Delegated to StatusWidget.

        Args:
            status: dict - status summary from GitClient
        """
        file_count = (
            status.get("modified", 0)
            + status.get("added", 0)
            + status.get("deleted", 0)
            + status.get("untracked", 0)
        )
        self._status_widget.update_working_tree_status(file_count)

    def _refresh_status_views(self, repo_root):
        """Refresh working tree status and changes list (async via job_runner)."""
        # Sprint PERF-1: Move to background to avoid blocking UI
        if not repo_root:
            return

        # Prevent concurrent status refreshes
        if self._is_refreshing_status:
            log.debug("Status refresh already in progress, skipping")
            return

        self._is_refreshing_status = True

        # Show loading state
        self.working_tree_label.setText("Refreshing…")
        self._set_strong_label(self.working_tree_label, "gray")

        # Run git status operations in background
        def _fetch_status():
            status = self._git_client.status_summary(repo_root)
            file_statuses = self._git_client.status_porcelain(repo_root)
            return {"status": status, "file_statuses": file_statuses}

        self._job_runner.run_callable(
            "refresh_status",
            _fetch_status,
            on_success=self._on_status_refresh_complete,
            on_error=self._on_status_refresh_error,
        )

    def _on_status_refresh_complete(self, result):
        """Callback when async status refresh completes (Sprint PERF-1)."""
        try:
            self._is_refreshing_status = False

            status = result.get("status")
            file_statuses = result.get("file_statuses")

            if status:
                self._display_working_tree_status(status)

            if file_statuses is not None:
                self._file_statuses = file_statuses
                self._populate_changes_list()

            self._update_button_states()
            log.debug("Status refresh complete")
        except Exception as e:
            log.error(f"Error processing status refresh result: {e}")
            self._is_refreshing_status = False

    def _on_status_refresh_error(self, error):
        """Callback when async status refresh fails (Sprint PERF-1)."""
        self._is_refreshing_status = False
        log.warning(f"Status refresh error: {error}")
        self.working_tree_label.setText("(error)")
        self._set_strong_label(self.working_tree_label, "red")
        self._update_button_states()

    def _populate_changes_list(self):
        """
        Update changes list widget with current file statuses.
        Sprint 5 Phase 1.4: Delegated to ChangesWidget.
        """
        self._changes_widget.update_changes(self._file_statuses)

    def _on_workflow_changed(self):
        """Handle workflow selection change."""
        sender = self.sender()

        if sender == self.workflow_action_both:
            self._workflow_mode = "both"
        elif sender == self.workflow_action_commit:
            self._workflow_mode = "commit"
        elif sender == self.workflow_action_push:
            self._workflow_mode = "push"

        # Update checkmarks
        self.workflow_action_both.setChecked(self._workflow_mode == "both")
        self.workflow_action_commit.setChecked(self._workflow_mode == "commit")
        self.workflow_action_push.setChecked(self._workflow_mode == "push")

        # Update button label and states for the new mode
        self._update_commit_push_button_default_label()
        self._update_button_states()

    def _update_commit_push_button_default_label(self):
        """Set the combined button label based on workflow mode."""
        self._commit_push.update_commit_push_button_label()

    def _on_commit_message_changed(self):
        """Called when commit message text changes (debounced)."""
        self._button_update_timer.stop()
        self._button_update_timer.start()

    def _on_refresh_clicked(self):
        """Handle Refresh Status button click."""
        self._repo_validator.refresh_clicked()

    def _on_create_repo_clicked(self):
        """Handle Create Repo button click."""
        self._repo_validator.create_repo_clicked()

    def _on_connect_remote_clicked(self):
        """Handle Connect Remote button click."""
        self._repo_validator.connect_remote_clicked()

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
            self._fetch_pull.handle_fetch_result(job)
        elif job_type == "stage_previews":
            self._handle_stage_previews_result(job)

    # Fetch result handling delegated to self._fetch_pull handler

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
            self.preview_status_label.setText(f"Last generated: {display}")
            self._set_meta_label(self.preview_status_label, "#4db6ac")
        else:
            self.preview_status_label.setText("Last generated: (never)")
            self._set_meta_label(self.preview_status_label, "gray")
        self.open_preview_folder_btn.setEnabled(bool(rel_dir))

    def _on_open_preview_folder_clicked(self):
        rel_dir = settings.load_last_preview_dir()
        if not rel_dir or not self._current_repo_root:
            return
        abs_dir = core_paths.safe_join_repo(self._current_repo_root, rel_dir)
        if not abs_dir:
            return
        import os

        try:
            os.startfile(str(abs_dir))
        except Exception as e:
            log.warning(f"Open folder failed: {e}")

    def _on_generate_previews_clicked(self):
        if not self._current_repo_root:
            self._show_status_message("Repo not selected / invalid", is_error=True)
            return
        try:
            import FreeCAD

            ad = FreeCAD.ActiveDocument
        except Exception:
            ad = None
        if not ad:
            self._show_status_message("No active document", is_error=True)
            return
        file_name = getattr(ad, "FileName", "")
        if not file_name:
            self._show_status_message("Document not saved", is_error=True)
            return
        if not core_paths.is_inside_repo(file_name, self._current_repo_root):
            self._show_status_message("Document outside selected repo", is_error=True)
            return

        # Modal progress dialog (best-effort, keeps UI responsive)
        progress = QtWidgets.QProgressDialog("Generating previews…", None, 0, 0, self)
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

        settings.save_last_preview_at(datetime.now(timezone.utc).isoformat())
        if result.rel_dir:
            settings.save_last_preview_dir(result.rel_dir)
        self._update_preview_status_labels()

        # Stage outputs if enabled
        if self.stage_previews_checkbox.isChecked() and result.png_path and result.json_path:
            git_cmd = self._git_client._get_git_command()
            # Convert absolute paths to repo-relative paths
            import os
            png_rel = os.path.relpath(str(result.png_path), self._current_repo_root).replace("\\", "/")
            json_rel = os.path.relpath(str(result.json_path), self._current_repo_root).replace("\\", "/")
            
            # Build list of files to stage (always PNG + JSON, optionally GLB)
            files_to_stage = [png_rel, json_rel]
            if result.glb_path and result.glb_path.exists():
                glb_rel = os.path.relpath(str(result.glb_path), self._current_repo_root).replace("\\", "/")
                files_to_stage.append(glb_rel)
            
            args = [
                git_cmd,
                "-C",
                self._current_repo_root,
                "add",
                "--",
            ] + files_to_stage
            self._start_busy_feedback("Staging previews…")
            self._job_runner.run_job(
                "stage_previews", args, callback=self._on_stage_previews_completed
            )
        else:
            self._show_status_message("Previews generated", is_error=False)
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
            self._show_status_message("Previews generated and staged", is_error=False)
        else:
            self._show_status_message("Staging failed; outputs kept", is_error=True)
            log.warning(result.get("stderr", ""))
        if self._current_repo_root:
            self._refresh_status_views(self._current_repo_root)
        QtCore.QTimer.singleShot(2000, self._clear_status_message)

    def _on_publish_clicked(self):
        """Sprint 7: Handle Publish button click (one-click workflow)."""
        if not self._current_repo_root:
            self._show_status_message("Repo not selected / invalid", is_error=True)
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
            self._show_status_message("No active document", is_error=True)
            return

        file_name = getattr(ad, "FileName", "")
        if not file_name:
            self._show_status_message("Document not saved", is_error=True)
            return

        # Use commit message from the text box
        message = self.commit_message.toPlainText().strip()
        if not message:
            self._show_status_message("Commit message required", is_error=True)
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
                QtWidgets.QMessageBox.No,
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
            if (
                result.step == publish.PublishStep.COMMIT
                and "nothing" in result.message.lower()
            ):
                self._show_status_message("No changes to commit", is_error=False)
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
        self._show_status_message("Published successfully", is_error=False)

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

        settings.save_last_preview_at(datetime.now(timezone.utc).isoformat())
        export_details = result.details or {}
        if export_details.get("rel_dir"):
            settings.save_last_preview_dir(export_details["rel_dir"])
        self._update_preview_status_labels()

        # Refresh status views
        self._refresh_status_views(self._current_repo_root)

    # Preview operations delegated to self._file_browser handler

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
                QtWidgets.QMessageBox.Yes,
            )
            if choice == QtWidgets.QMessageBox.Yes:
                self._start_connect_remote_flow()
            else:
                self._show_status_message(f"Publish failed: {step_name}", is_error=True)
                log.error(f"Publish failed at {step_name}: {error_msg}")
                return
            # Do not continue to generic message box if user handled prompt
            return

        QtWidgets.QMessageBox.critical(
            self, f"Publish Failed ({step_name})", detailed_msg
        )

        self._show_status_message(f"Publish failed: {step_name}", is_error=True)
        log.error(f"Publish failed at {step_name}: {error_msg}")

    def _load_saved_repo_path(self):
        """
        Load the saved repository path from settings and validate it (synchronous).
        """
        saved_path = settings.load_repo_path()
        if saved_path:
            self.repo_path_field.blockSignals(True)
            self.repo_path_field.setText(saved_path)
            self.repo_path_field.blockSignals(False)
            # Auto-validate on load
            self._validate_repo_path(saved_path)
            log.info(f"Restored repo path from settings: {saved_path}")
        # Initialize preview status area
        self._update_preview_status_labels()

    def _load_saved_repo_path_async(self):
        """Load saved repository path and validate in background (Sprint PERF-2)."""
        saved_path = settings.load_repo_path()
        if saved_path:
            # Display path immediately
            self.repo_path_field.blockSignals(True)
            self.repo_path_field.setText(saved_path)
            self.repo_path_field.blockSignals(False)
            log.info(f"Restored repo path from settings: {saved_path}")
            # Validate in background (non-blocking)
            self._validate_repo_path(saved_path)
        # Initialize preview status area
        self._update_preview_status_labels()

    # ========== GitHub OAuth/Auth (Sprint 4: Delegated to GitHubAuthHandler) ==========

    def _on_github_connect_clicked(self):
        """Handle Connect GitHub button click."""
        self._github_auth.connect_clicked()

    def _on_github_disconnect_clicked(self):
        """Handle Disconnect GitHub button click."""
        self._github_auth.disconnect_clicked()

    def _on_github_refresh_clicked(self):
        """Legacy refresh handler: route to verify."""
        self._github_auth.verify_clicked()

    def _on_github_verify_clicked(self):
        """Handle Verify / Refresh Account button click."""
        self._github_auth.verify_clicked()

    def _create_github_client(self):
        """Construct a GitHubApiClient using stored token; returns None if not connected."""
        try:
            return self._services.github_api_client()
        except Exception as e:
            log.debug(f"Failed to create GitHub client: {e}")
            return None

    # ========== GitCAD Lock Management (Phase 2) ==========

    def _on_show_locks_clicked(self):
        """Handle Show Locks button click."""
        if hasattr(self, '_lock_handler'):
            self._lock_handler.show_locks_dialog()

    def _on_refresh_locks_clicked(self):
        """Handle Refresh Locks button click."""
        if hasattr(self, '_lock_handler'):
            self._lock_handler.refresh_lock_status()
            self._show_status_message("Refreshing lock status...")
    
    def _on_config_gitcad_clicked(self):
        """Handle Configure GitCAD button click."""
        if not self._current_repo_root:
            return
        
        from freecad.gitpdm.ui.config_dialog import show_config_dialog
        show_config_dialog(self._current_repo_root, self)
    
    def _on_init_gitcad_clicked(self):
        """Handle Initialize GitCAD button click."""
        if not self._current_repo_root:
            QtWidgets.QMessageBox.warning(
                self,
                "No Repository",
                "Please open a repository first."
            )
            return
        
        from freecad.gitpdm.ui.init_wizard import show_init_wizard
        
        success = show_init_wizard(self._current_repo_root, self)
        
        if success:
            # Re-check GitCAD availability
            if hasattr(self, '_lock_handler'):
                self._lock_handler.check_availability(self._current_repo_root)
                self._show_status_message("GitCAD initialized successfully!")

    def _update_lock_status(self):
        """Update GitCAD status display based on availability."""
        if not hasattr(self, '_lock_handler') or not hasattr(self, '_lock_group'):
            return

        if self._lock_handler._gitcad_available:
            # GitCAD is available - show lock management buttons
            lock_count = len(self._lock_handler._current_locks)
            my_locks = sum(
                1 for lock in self._lock_handler._current_locks.values()
                if lock.owner == self._lock_handler._current_username
            )
            
            if lock_count > 0:
                self.gitcad_status_label.setText(
                    f"✓ GitCAD active • {lock_count} file(s) locked ({my_locks} by you)"
                )
                self._set_meta_label(self.gitcad_status_label, "green")
            else:
                self.gitcad_status_label.setText("✓ GitCAD active • No files locked")
                self._set_meta_label(self.gitcad_status_label, "green")
            
            # Show lock management buttons, hide init button
            self.show_locks_btn.setEnabled(True)
            self.refresh_locks_btn.setEnabled(True)
            self.config_gitcad_btn.setEnabled(True)
            self.show_locks_btn.setVisible(True)
            self.refresh_locks_btn.setVisible(True)
            self.config_gitcad_btn.setVisible(True)
            self.init_gitcad_btn.setVisible(False)
            
            self._lock_group.setVisible(True)
        else:
            # GitCAD not available - show initialization option
            if self._current_repo_root:
                self.gitcad_status_label.setText("GitCAD not initialized")
                self._set_meta_label(self.gitcad_status_label, "gray")
                
                # Hide lock management buttons, show init button
                self.show_locks_btn.setEnabled(False)
                self.refresh_locks_btn.setEnabled(False)
                self.config_gitcad_btn.setEnabled(False)
                self.show_locks_btn.setVisible(False)
                self.refresh_locks_btn.setVisible(False)
                self.config_gitcad_btn.setVisible(False)
                self.init_gitcad_btn.setVisible(True)
                # Show the section but with disabled state
                self._lock_group.setVisible(True)
            else:
                # No repo selected - hide section
                self._lock_group.setVisible(False)

