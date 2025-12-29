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

import os
import glob
import sys
import subprocess

from freecad_gitpdm.core import log, settings, jobs
from freecad_gitpdm.git import client
from freecad_gitpdm.ui import dialogs
from freecad_gitpdm.ui.github_auth import GitHubAuthHandler
from freecad_gitpdm.ui.file_browser import FileBrowserHandler
from freecad_gitpdm.ui.fetch_pull import FetchPullHandler
from freecad_gitpdm.ui.commit_push import CommitPushHandler
from freecad_gitpdm.export import exporter, mapper
from freecad_gitpdm.core import paths as core_paths
from freecad_gitpdm.core import publish


class _DocumentObserver:
    """Observer to detect document saves and trigger status refresh."""
    
    def __init__(self, panel):
        self._panel = panel
        # Bind timer to the panel (Qt QObject) so it lives on the UI thread
        self._refresh_timer = QtCore.QTimer(panel)
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
            import glob
            filename = os.path.normpath(filename)
            repo_root = os.path.normpath(self._panel._current_repo_root)
            
            log.debug(f"Checking if {filename} is in {repo_root}")
            
            if filename.startswith(repo_root):
                log.info(f"Document saved in repo, scheduling refresh")
                # Stop/start the timer on its owning thread to avoid
                # cross-thread timer operations (Qt enforces thread affinity)
                try:
                    QtCore.QMetaObject.invokeMethod(
                        self._refresh_timer,
                        "stop",
                        QtCore.Qt.QueuedConnection,
                    )
                    QtCore.QMetaObject.invokeMethod(
                        self._refresh_timer,
                        "start",
                        QtCore.Qt.QueuedConnection,
                    )
                except Exception as e:
                    # Fallback: best-effort direct calls
                    log.debug(f"Queued timer restart failed, using direct: {e}")
                    try:
                        self._refresh_timer.stop()
                        self._refresh_timer.start()
                    except Exception as e2:
                        log.error(f"Failed to restart refresh timer: {e2}")
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

    def __init__(self, services=None):
        super().__init__()
        self.setObjectName("GitPDM_DockWidget")
        self.setWindowTitle("Git PDM")
        self.setMinimumWidth(300)

        # Service container (Sprint 3)
        if services is None:
            from freecad_gitpdm.core.services import get_services

            services = get_services()
        self._services = services

        # Initialize git client and job runner
        self._git_client = self._services.git_client()
        self._job_runner = self._services.job_runner()
        self._job_runner.job_finished.connect(self._on_job_finished)

        # Initialize handlers (Sprint 4)
        self._github_auth = GitHubAuthHandler(self, self._services)
        self._file_browser = FileBrowserHandler(self, self._git_client, self._job_runner)
        self._fetch_pull = FetchPullHandler(self, self._git_client, self._job_runner)
        self._commit_push = CommitPushHandler(self, self._git_client, self._job_runner)

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
        self._button_update_timer = QtCore.QTimer(self)
        self._button_update_timer.setSingleShot(True)
        self._button_update_timer.setInterval(300)
        self._button_update_timer.timeout.connect(
            self._do_deferred_button_update
        )
        self._cached_has_remote = False
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
        self._is_switching_branch = False
        self._branch_combo_updating = False  # Prevent recursive combo change events
        self._local_branches = []
        # Auto-publish tracking for newly created branches
        self._pending_publish_new_branch = None

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
        self._build_git_check_section(main_layout)
        self._build_repo_selector(main_layout)
        self._build_github_account_section(main_layout)
        self._build_status_section(main_layout)
        self._build_branch_section(main_layout)
        self._build_changes_section(main_layout)
        self._build_buttons_section(main_layout)
        self._build_repo_browser_section(main_layout)

        # Compact-mode commit mini section (hidden by default)
        self._build_compact_commit_section(main_layout)

        # Default to collapsed view
        self._set_compact_mode(True)

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

        # Defer heavy initialization to avoid blocking UI and window flash
        QtCore.QTimer.singleShot(100, self._deferred_initialization)
        
        log.info("GitPDM dock panel created")

    def _build_compact_commit_section(self, layout):
        """Build a minimal commit UI shown only in collapsed mode."""
        container = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(6, 4, 6, 0)
        row.setSpacing(6)
        container.setLayout(row)

        msg_label = QtWidgets.QLabel("Commit message:")
        self._set_meta_label(msg_label, "gray")
        row.addWidget(msg_label)

        self.compact_commit_message = QtWidgets.QLineEdit()
        self.compact_commit_message.setPlaceholderText("Describe your changes")
        self.compact_commit_message.textChanged.connect(self._on_commit_message_changed)
        row.addWidget(self.compact_commit_message, 1)

        self.compact_commit_btn = QtWidgets.QPushButton("Commit")
        self.compact_commit_btn.setEnabled(False)
        self.compact_commit_btn.clicked.connect(self._commit_push.commit_clicked)
        row.addWidget(self.compact_commit_btn)

        container.setVisible(False)
        layout.addWidget(container)
        self._compact_commit_container = container

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
        """Run heavy initialization after panel is shown."""
        try:
            # Check git availability
            self._check_git_available()
            
            # Load saved repo path and validate
            self._load_saved_repo_path()
            
            # Register document observer to auto-refresh on save
            self._register_document_observer()
            
            # Load GitHub connection status (Sprint OAUTH-1)
            self._github_auth.refresh_connection_status()
            # Sprint OAUTH-2: Auto-verify identity in background with cooldown
            QtCore.QTimer.singleShot(50, self._github_auth.maybe_auto_verify_identity)
            
            # Check if user is editing from wrong folder (worktree mismatch)
            QtCore.QTimer.singleShot(1000, self._check_for_wrong_folder_editing)
            
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
        # Hide the System section per request
        group.setVisible(False)
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

        clone_btn = QtWidgets.QPushButton("Open/Clone Repo…")
        clone_btn.clicked.connect(self._on_open_clone_repo_clicked)
        path_layout.addWidget(clone_btn)

        new_repo_btn = QtWidgets.QPushButton("New Repo…")
        new_repo_btn.clicked.connect(self._on_new_repo_clicked)
        path_layout.addWidget(new_repo_btn)

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
        # Hide the Show root dropdown entirely
        self.root_toggle_btn.setVisible(False)
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
        # Hide the Validate row
        self.validate_caption = QtWidgets.QLabel("Validate:")
        validation_layout.addWidget(self.validate_caption)
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
        # Hide refresh button
        refresh_btn.setVisible(False)
        validation_layout.addWidget(refresh_btn)

        # Hide Validate caption and value
        self.validate_caption.setVisible(False)
        self.validate_label.setVisible(False)
        group_layout.addLayout(validation_layout)

        layout.addWidget(group)
        self._group_repo_selector = group

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
        self.github_connect_btn.clicked.connect(self._on_github_connect_clicked)
        buttons_layout.addWidget(self.github_connect_btn)

        self.github_disconnect_btn = QtWidgets.QPushButton(
            "Disconnect"
        )
        self.github_disconnect_btn.setEnabled(False)
        self.github_disconnect_btn.setToolTip(
            "Disconnect GitHub account"
        )
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
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred
        )
        self.branch_combo.currentIndexChanged.connect(
            self._on_branch_combo_changed
        )
        selector_layout.addWidget(self.branch_combo)
        
        group_layout.addLayout(selector_layout)

        # Action buttons row
        actions_layout = QtWidgets.QHBoxLayout()
        actions_layout.setSpacing(4)

        self.new_branch_btn = QtWidgets.QPushButton("New Branch…")
        self.new_branch_btn.clicked.connect(self._on_new_branch_clicked)
        actions_layout.addWidget(self.new_branch_btn)

        self.switch_branch_btn = QtWidgets.QPushButton("Switch")
        self.switch_branch_btn.clicked.connect(self._on_switch_branch_clicked)
        actions_layout.addWidget(self.switch_branch_btn)

        self.delete_branch_btn = QtWidgets.QPushButton("Delete…")
        self.delete_branch_btn.clicked.connect(self._on_delete_branch_clicked)
        actions_layout.addWidget(self.delete_branch_btn)

        group_layout.addLayout(actions_layout)

        worktree_help_layout = QtWidgets.QHBoxLayout()
        worktree_help_layout.addStretch()
        self.worktree_help_btn = QtWidgets.QPushButton("Worktree Help")
        self.worktree_help_btn.setToolTip(
            "Use per-branch worktrees so each branch has its own folder."
        )
        self.worktree_help_btn.clicked.connect(self._on_worktree_help_clicked)
        worktree_help_layout.addWidget(self.worktree_help_btn)
        group_layout.addLayout(worktree_help_layout)

        layout.addWidget(group)
        # Hide the entire Branch section per request
        group.setVisible(False)
        self._group_branch = group

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
        # Reduce the size of the changes list
        self.changes_list.setMaximumHeight(50)
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
        self.fetch_btn.clicked.connect(self._fetch_pull.fetch_clicked)
        row1_layout.addWidget(self.fetch_btn)

        self.pull_btn = QtWidgets.QPushButton("Pull")
        self.pull_btn.setEnabled(False)
        self.pull_btn.clicked.connect(self._fetch_pull.pull_clicked)
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
            self._commit_push.commit_push_clicked
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

        # Hide the entire Previews area per request
        previews_group.setVisible(False)
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

        self.browser_window_btn = QtWidgets.QPushButton(
            "Open Browser"
        )
        self.browser_window_btn.setEnabled(False)
        self.browser_window_btn.clicked.connect(
            self._file_browser.open_browser
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

    def _on_open_clone_repo_clicked(self):
        """Open repo picker dialog to select and clone GitHub repo."""
        try:
            from freecad_gitpdm.ui.repo_picker import RepoPickerDialog

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
            from freecad_gitpdm.ui.new_repo_wizard import NewRepoWizard

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

            # Set FreeCAD working directory to repo folder
            # This ensures Save As dialog defaults to repo folder
            self._set_freecad_working_directory(repo_root)

            # Fetch branch and status
            self._fetch_branch_and_status(repo_root)
            # Refresh repo browser
            self._file_browser.refresh_files()
            # Update preview status area
            self._update_preview_status_labels()
            
            # Update button states (including branch buttons)
            self._update_button_states()
            
            # Explicitly ensure branch buttons are updated
            QtCore.QTimer.singleShot(100, self._update_branch_button_states)
            
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
            self._file_browser.clear_browser()
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
        self._fetch_pull.display_last_fetch()

    def _update_upstream_info(self, repo_root):
        """
        Update upstream ref and ahead/behind counts.
        Uses tracking upstream (@{u}) if available, otherwise falls back to default.
        
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
        
        # Use new method that prefers tracking upstream (no fallback)
        ab_result = self._git_client.get_ahead_behind_with_upstream(repo_root)
        upstream_ref = ab_result.get("upstream")
        
        # Show status message to debug
        msg = f"Upstream: {upstream_ref if upstream_ref else '(not set)'}"
        log.info(msg)
        
        if not upstream_ref:
            # No upstream configured for this branch
            self.upstream_label.setText("(not set)")
            self._set_meta_label(self.upstream_label, "orange")
            self.ahead_behind_label.setText("(unknown)")
            self._set_strong_label(self.ahead_behind_label, "gray")
            self._upstream_ref = None
            return
        
        # Display upstream
        self.upstream_label.setText(upstream_ref)
        self._set_meta_label(self.upstream_label, "#4db6ac")
        self._upstream_ref = upstream_ref
        
        # Display ahead/behind
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

    # ========== Fetch/Pull Operations (Sprint 4: Delegated to FetchPullHandler) ==========
    # Fetch and pull operations fully delegated to self._fetch_pull handler

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
            self._fetch_pull.is_busy()
            or self._commit_push.is_busy()
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
            self._fetch_pull.is_busy()
            or self._commit_push.is_busy()
            or self._job_runner.is_busy()
        )

        if hasattr(self, "commit_message"):
            commit_msg_ok = bool(
                self.commit_message.toPlainText().strip()
            )
        # Also consider compact commit message when present
        if hasattr(self, "compact_commit_message") and not commit_msg_ok:
            commit_msg_ok = bool(self.compact_commit_message.text().strip())

        fetch_enabled = (
            git_ok and repo_ok and self._cached_has_remote
            and not busy
        )
        self.fetch_btn.setEnabled(fetch_enabled)

        pull_enabled = (
            git_ok and repo_ok and self._cached_has_remote
            and upstream_ok
            and self._behind_count > 0
            and not busy
        )
        self.pull_btn.setEnabled(pull_enabled)
        commit_enabled = (
            git_ok and repo_ok and changes_present and commit_msg_ok
            and not busy
        )
        # Enable compact commit button in collapsed mode
        if hasattr(self, "compact_commit_btn"):
            self.compact_commit_btn.setEnabled(
                git_ok and repo_ok and changes_present and commit_msg_ok and not busy
            )

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
        
        # Update branch button states
        self._update_branch_button_states()
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

    # ========== File Browser (Sprint 4: Delegated to FileBrowserHandler) ==========
    # Browser UI creation and management delegated to self._file_browser

    def _refresh_branch_list(self):
        """Refresh the list of local branches in the combo box."""
        if not self._current_repo_root:
            self._local_branches = []
            self.branch_combo.clear()
            return
        
        self._local_branches = self._git_client.list_local_branches(
            self._current_repo_root
        )
        current_branch = self._git_client.current_branch(
            self._current_repo_root
        )
        
        # Update combo box
        self._branch_combo_updating = True
        self.branch_combo.clear()
        self.branch_combo.addItems(self._local_branches)
        
        # Select current branch
        if current_branch and current_branch in self._local_branches:
            idx = self._local_branches.index(current_branch)
            self.branch_combo.setCurrentIndex(idx)
        
        self._branch_combo_updating = False
        
        # Update button states
        self._update_branch_button_states()

    def _update_branch_button_states(self):
        """Update enabled/disabled state of branch action buttons."""
        # Safety check: ensure widgets exist
        if not hasattr(self, "new_branch_btn"):
            return
        
        repo_ok = self._current_repo_root is not None
        has_branches = len(self._local_branches) > 0
        busy = (
            self._fetch_pull.is_busy()
            or self._commit_push.is_busy()
            or self._is_switching_branch
            or self._job_runner.is_busy()
        )
        
        # Debug logging
        from freecad_gitpdm.core import log
        log.debug(f"Branch button states - repo_ok: {repo_ok}, busy: {busy}, has_branches: {has_branches}")
        
        self.new_branch_btn.setEnabled(repo_ok and not busy)
        self.switch_branch_btn.setEnabled(
            repo_ok and has_branches and not busy
        )
        
        # Can't delete current branch
        current_branch = self._git_client.current_branch(
            self._current_repo_root
        ) if self._current_repo_root else None
        selected_idx = self.branch_combo.currentIndex()
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
        self.delete_branch_btn.setEnabled(can_delete)

    def _on_branch_combo_changed(self, index):
        """Handle branch combo box selection change."""
        if self._branch_combo_updating:
            return
        # Just update delete button state
        self._update_branch_button_states()

    def _on_new_branch_clicked(self):
        """Handle New Branch button click - show dialog and create branch."""
        if not self._current_repo_root:
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
            self._current_repo_root, self._remote_name
        )
        if not default_upstream:
            default_upstream = "HEAD"
        
        # Show dialog with open files information
        dialog = dialogs.NewBranchDialog(
            parent=self,
            default_start_point=default_upstream,
            open_docs=open_docs,
            lock_files=lock_files
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
                self,
                "Files Opened",
                "FreeCAD files were opened after the dialog. Please close ALL documents "
                "and try again to prevent corruption."
            )
            return
        
        # Validate branch name
        if not self._validate_branch_name(branch_name):
            return
        
        # Create branch
        log.info(f"Creating branch: {branch_name} from {start_point}")
        result = self._git_client.create_branch(
            self._current_repo_root,
            branch_name,
            start_point
        )
        
        if not result.ok:
            QtWidgets.QMessageBox.warning(
                self,
                "Create Branch Failed",
                f"Failed to create branch '{branch_name}':\n\n{result.stderr}"
            )
            return
        
        log.info(f"Branch '{branch_name}' created, now switching to it")
        
        # Switch to new branch
        # Mark to auto-publish (push -u) after successful switch
        self._pending_publish_new_branch = branch_name
        self._switch_to_branch(branch_name)

    def _validate_branch_name(self, name):
        """
        Validate branch name according to git rules.
        Returns True if valid, shows error and returns False otherwise.
        """
        if not name:
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid Branch Name",
                "Branch name cannot be empty."
            )
            return False
        
        if name.startswith("-"):
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid Branch Name",
                "Branch name cannot start with a dash."
            )
            return False
        
        if " " in name:
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid Branch Name",
                "Branch name cannot contain spaces."
            )
            return False
        
        # Check for invalid characters
        invalid_chars = ["~", "^", ":", "?", "*", "[", "\\", "..", "@{"]
        for char in invalid_chars:
            if char in name:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Invalid Branch Name",
                    f"Branch name cannot contain '{char}'."
                )
                return False
        
        return True

    def _on_switch_branch_clicked(self):
        """Handle Switch button click - switch to selected branch."""
        if not self._current_repo_root:
            return
        
        selected_idx = self.branch_combo.currentIndex()
        if selected_idx < 0 or selected_idx >= len(self._local_branches):
            return
        
        target_branch = self._local_branches[selected_idx]
        current_branch = self._git_client.current_branch(
            self._current_repo_root
        )
        
        if target_branch == current_branch:
            log.debug("Already on selected branch")
            return
        
        self._switch_to_branch(target_branch)

    def _on_worktree_help_clicked(self):
        """Show quick guidance for setting up per-branch git worktrees."""
        example_path = os.path.normpath(os.path.join(self._current_repo_root or "..", "repo-feature"))
        msg = (
            "Use git worktree to give each branch its own folder. This avoids FCStd corruption "
            "from branch switches while files are open.\n\n"
            "Example commands:\n"
            f"  git worktree add {example_path} feature\n"
            "  git worktree add ../repo-main main\n\n"
            "Open the matching worktree folder in FreeCAD for the branch you are editing."
        )
        QtWidgets.QMessageBox.information(self, "Use Git Worktrees", msg)

    def _show_worktree_success_dialog(self, worktree_path: str, branch_name: str):
        """Show success dialog with option to open worktree folder."""
        msg_box = QtWidgets.QMessageBox(self)
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
        self._show_status_message(
            f"Opened worktree: {os.path.basename(worktree_path)}",
            is_error=False
        )
        QtCore.QTimer.singleShot(5000, self._clear_status_message)

    def _show_repo_opened_dialog(self, repo_path: str, action: str, repo_name: str = None):
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
                f"Could not open folder in file explorer:\n{e}"
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
                    self,
                    "Wrong Folder - Risk of Corruption",
                    msg
                )
                log.warning(f"User has {len(wrong_folder_docs)} documents open from wrong folder")
        
        except Exception as e:
            log.debug(f"Could not check for wrong folder editing: {e}")

    def _switch_to_branch(self, branch_name):
        """
        Switch to the specified branch, with dirty working tree check.
        
        Args:
            branch_name: str - branch to switch to
        """
        if not self._current_repo_root:
            return
        
        if self._is_switching_branch or self._job_runner.is_busy():
            log.debug("Job running, branch switch ignored")
            return

        # CRITICAL Guard: block ALL branch operations while ANY FreeCAD files are open
        # This prevents corruption that can occur when:
        # - Git operations modify files that are open in FreeCAD
        # - Switching between worktrees while files from other worktrees are open
        # - Creating new worktrees that share git objects with open files
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
                self,
                "Close ALL Files First",
                advice + ("\n\n" + "\n".join(details_lines) if details_lines else ""),
            )
            log.warning("Branch switch blocked - open FreeCAD documents detected")
            return
        
        # Check for uncommitted changes
        has_changes = self._git_client.has_uncommitted_changes(
            self._current_repo_root
        )
        
        if has_changes:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Uncommitted Changes",
                "You have uncommitted changes in your working tree.\n\n"
                "Switching branches may fail or overwrite your changes.\n"
                "Consider committing or stashing your changes first.\n\n"
                "Do you want to switch anyway?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
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
                self,
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
        self._start_busy_feedback(f"Switching to {branch_name}…")
        self._update_branch_button_states()
        
        log.info(f"Switching to branch: {branch_name}")
        
        git_cmd = self._git_client._get_git_command()
        args = [git_cmd, "-C", self._current_repo_root, "switch", branch_name]
        
        self._job_runner.run_job(
            "switch_branch",
            args,
            callback=lambda job: self._on_switch_branch_completed(job, branch_name)
        )

    def _on_switch_branch_completed(self, job, branch_name):
        """Callback when branch switch completes."""
        result = job.get("result", {})
        success = result.get("success", False)
        stderr = result.get("stderr", "")
        
        self._is_switching_branch = False
        self._stop_busy_feedback()
        
        if not success:
            # Check if 'switch' is not recognized and retry with checkout
            if "switch" in stderr.lower() and "not a git command" in stderr.lower():
                log.debug("'git switch' not available, retrying with checkout")
                self._switch_to_branch_with_checkout(branch_name)
                return
            
            QtWidgets.QMessageBox.warning(
                self,
                "Switch Branch Failed",
                f"Failed to switch to branch '{branch_name}':\n\n{stderr}"
            )
            self._update_branch_button_states()
            return
        
        log.info(f"Switched to branch: {branch_name}")
        
        # Show success message for new branch creation
        self._show_status_message(
            f"Switched to '{branch_name}'",
            is_error=False
        )
        QtCore.QTimer.singleShot(3000, self._clear_status_message)
        
        # If this switch follows a new branch creation, publish it to origin
        if self._pending_publish_new_branch == branch_name:
            log.info(f"Publishing new branch to remote: {branch_name}")
            # Clear flag before pushing to avoid re-entrancy
            self._pending_publish_new_branch = None
            # Use explicit branch name to ensure remote branch is created
            # and set as upstream regardless of HEAD state.
            self._retry_push_with_branch_name()

        # Refresh UI
        if self._current_repo_root:
            self._refresh_after_branch_operation()

    def _compute_worktree_path_for_branch(self, branch_name: str) -> str:
        """Compute a suggested worktree path for the given branch."""
        try:
            base = os.path.basename(os.path.normpath(self._current_repo_root or ""))
            parent = os.path.dirname(os.path.normpath(self._current_repo_root or ""))
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
                self,
                "Git Not Found",
                "Git is not available. Install Git or GitHub Desktop and retry.",
            )
            return

        self._is_switching_branch = True
        self._start_busy_feedback(f"Creating worktree for {branch_name}…")
        self._update_branch_button_states()

        args = [git_cmd, "-C", self._current_repo_root, "worktree", "add", worktree_path, branch_name]
        self._job_runner.run_job(
            "add_worktree",
            args,
            callback=lambda job: self._on_worktree_created(job, worktree_path, branch_name)
        )

    def _on_worktree_created(self, job, worktree_path: str, branch_name: str):
        """Handle completion of adding a worktree."""
        result = job.get("result", {})
        success = result.get("success", False)
        stderr = result.get("stderr", "")
        self._is_switching_branch = False
        self._stop_busy_feedback()

        if not success:
            QtWidgets.QMessageBox.warning(
                self,
                "Worktree Creation Failed",
                f"Failed to create worktree for '{branch_name}':\n\n{stderr}"
            )
            self._update_branch_button_states()
            return

        # Update repo root to new worktree and refresh
        log.info(f"Worktree created: {worktree_path}")
        settings.save_repo_path(worktree_path)
        self._validate_repo_path(worktree_path)
        
        # Show success dialog with "Open Folder" button
        self._show_worktree_success_dialog(worktree_path, branch_name)

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
        if not self._current_repo_root:
            return []
        pattern = os.path.join(self._current_repo_root, "*.FCStd.lock")
        try:
            return glob.glob(pattern)
        except Exception:
            return []

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
                    # These parameters control FreeCAD's file dialog defaults
                    param_grp.SetString("FileOpenSavePath", directory)
                    log.info(f"Set FreeCAD FileOpenSavePath parameter: {directory}")
            except Exception as e:
                log.debug(f"Could not set FreeCAD file path parameter: {e}")
                    
        except Exception as e:
            log.error(f"Failed to set working directory to {directory}: {e}")

    def _start_working_directory_refresh(self):
        """Start periodic timer to maintain repo folder as FreeCAD's working directory."""
        if not hasattr(self, '_wd_refresh_timer'):
            self._wd_refresh_timer = QtCore.QTimer(self)
            self._wd_refresh_timer.timeout.connect(self._refresh_working_directory)
            # Refresh every 10 seconds to maintain working directory
            self._wd_refresh_timer.start(10000)
            log.debug("Started working directory refresh timer")

    def _refresh_working_directory(self):
        """Periodic refresh of working directory to maintain repo folder as default."""
        if self._current_repo_root:
            try:
                current_wd = os.getcwd()
                repo_norm = os.path.normcase(os.path.normpath(self._current_repo_root))
                current_norm = os.path.normcase(os.path.normpath(current_wd))
                
                # Only update if working directory has drifted from repo
                if current_norm != repo_norm:
                    log.debug(f"Working directory drifted to {current_wd}, resetting to {self._current_repo_root}")
                    self._set_freecad_working_directory(self._current_repo_root)
            except Exception as e:
                log.debug(f"Working directory refresh error: {e}")

    def _switch_to_branch_with_checkout(self, branch_name):
        """Fallback to git checkout if git switch is not available."""
        if not self._current_repo_root:
            return
        
        self._is_switching_branch = True
        self._start_busy_feedback(f"Switching to {branch_name}…")
        
        git_cmd = self._git_client._get_git_command()
        args = [git_cmd, "-C", self._current_repo_root, "checkout", branch_name]
        
        self._job_runner.run_job(
            "checkout_branch",
            args,
            callback=lambda job: self._on_switch_branch_completed(job, branch_name)
        )

    def _on_delete_branch_clicked(self):
        """Handle Delete Branch button click."""
        if not self._current_repo_root:
            return
        
        selected_idx = self.branch_combo.currentIndex()
        if selected_idx < 0 or selected_idx >= len(self._local_branches):
            return
        
        branch_name = self._local_branches[selected_idx]
        current_branch = self._git_client.current_branch(
            self._current_repo_root
        )
        
        if branch_name == current_branch:
            QtWidgets.QMessageBox.warning(
                self,
                "Cannot Delete Branch",
                f"Cannot delete the current branch '{branch_name}'.\n"
                "Switch to another branch first."
            )
            return
        
        # Confirm deletion
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete Branch",
            f"Are you sure you want to delete branch '{branch_name}'?\n\n"
            "This operation cannot be undone.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        
        # Delete branch
        log.info(f"Deleting branch: {branch_name}")
        result = self._git_client.delete_local_branch(
            self._current_repo_root,
            branch_name,
            force=False
        )
        
        if not result.ok:
            # Check if branch needs force delete
            if "not fully merged" in result.stderr.lower():
                reply = QtWidgets.QMessageBox.question(
                    self,
                    "Force Delete Branch",
                    f"Branch '{branch_name}' is not fully merged.\n\n"
                    "Do you want to force delete it? "
                    "Unmerged changes will be lost.",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No
                )
                if reply == QtWidgets.QMessageBox.Yes:
                    result = self._git_client.delete_local_branch(
                        self._current_repo_root,
                        branch_name,
                        force=True
                    )
                    if not result.ok:
                        QtWidgets.QMessageBox.warning(
                            self,
                            "Delete Branch Failed",
                            f"Failed to delete branch '{branch_name}':\n\n{result.stderr}"
                        )
                        return
                else:
                    return
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Delete Branch Failed",
                    f"Failed to delete branch '{branch_name}':\n\n{result.stderr}"
                )
                return
        
        log.info(f"Deleted branch: {branch_name}")
        
        # Refresh branch list
        self._refresh_branch_list()

    def _refresh_after_branch_operation(self):
        """Refresh UI after branch operations (switch, create, etc.)."""
        if not self._current_repo_root:
            return
        
        # Update branch name display
        branch = self._git_client.current_branch(self._current_repo_root)
        self.branch_label.setText(branch)
        
        # Refresh branch list
        self._refresh_branch_list()
        
        # Refresh status and upstream
        self._refresh_status_views(self._current_repo_root)
        self._update_upstream_info(self._current_repo_root)
        
        # Refresh repo browser
        self._refresh_repo_browser_files()

    # Fetch/pull button handlers delegated to self._fetch_pull

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
        """Return UI to Ready after a short delay if idle."""
        def _to_ready():
            if not (
                self._fetch_pull.is_busy()
                or self._commit_push.is_busy()
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
        self._commit_push.update_commit_push_button_label()

    def _on_commit_message_changed(self):
        """Called when commit message text changes (debounced)."""
        self._button_update_timer.stop()
        self._button_update_timer.start()




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