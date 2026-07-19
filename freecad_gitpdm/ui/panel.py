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
            "Neither PySide6 nor PySide2 found. FreeCAD installation may be incomplete."
        ) from e

import os
import glob
import sys
import subprocess
import time

from freecad_gitpdm.core import (
    log,
    session_lock,
    settings,
    jobs,
    storage_mode,
    checkpoint,
)
from freecad_gitpdm.git import client
from freecad_gitpdm.ui import dialogs
from freecad_gitpdm.ui.fetch_pull import FetchPullHandler
from freecad_gitpdm.ui.commit_push import CommitPushHandler
from freecad_gitpdm.ui.repo_validator import RepoValidationHandler
from freecad_gitpdm.ui.branch_ops import BranchOperationsHandler
from freecad_gitpdm.ui.connections_dialog import ConnectionsDialog
from freecad_gitpdm.ui import label_style
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

    def slotChangedObject(self, obj, prop):
        """
        Called on every property change to any object in any open document
        (FreeCAD's signalChangedObject). This is the "activity" signal the
        Phase G6 (R2.5) checkpoint scheduler debounces against -- an edit
        resets the idle clock so a checkpoint only fires once the user has
        actually stopped touching the model for a while. Cheap and
        unconditional (no repo-root filtering): a wrong-repo edit just
        means the idle clock resets one extra time, which is harmless,
        versus resolving obj's owning document's path on every property
        change of every edit.
        """
        if self._panel._current_repo_root:
            self._panel._checkpoint_state.note_activity(time.time())

    def slotCreatedDocument(self, doc):
        """
        Called when a new document is created (e.g. File > New).

        Reasserts the working directory immediately, rather than waiting on
        the periodic timer, since a document created via File > New can be
        saved for the first time before that timer's next tick — and by then
        FreeCAD may have already reset FileOpenSavePath to whatever folder a
        prior document/dialog last touched.
        """
        if not self._panel._current_repo_root:
            return
        try:
            self._panel._set_freecad_working_directory(self._panel._current_repo_root)
            log.debug("Reasserted working directory on new document creation")
        except Exception as e:
            log.debug(f"Failed to reassert working directory on new document: {e}")

    def slotStartSaveDocument(self, doc, filename):
        """
        Called just before a document is serialized to disk (FreeCAD's
        signalStartSaveDocument). This is the precise, save-scoped hook
        for the G3 compression fix (see core/settings.py) -- entering the
        scope here, and exiting it in slotFinishSaveDocument below, means
        the global CompressionLevel preference is only touched for the
        duration of this one save, and only when it's a delta-mode
        GitPDM repo's document being saved.
        """
        self._maybe_enter_compression_scope(filename)

    def _maybe_enter_compression_scope(self, filename):
        """Enter the git-friendly compression scope, but only for saves of
        a document inside the active delta-mode GitPDM repo."""
        try:
            if not filename or not self._panel._current_repo_root:
                return
            filename_norm = os.path.normpath(filename)
            repo_root = os.path.normpath(self._panel._current_repo_root)
            if not filename_norm.startswith(repo_root):
                return
            if storage_mode.get_storage_mode(repo_root) == storage_mode.MODE_DELTA:
                settings.enter_git_friendly_compression_scope()
        except Exception as e:
            log.debug(f"Compression scope check skipped: {e}")

    def slotFinishSaveDocument(self, doc, filename):
        """Called after a document is saved."""
        try:
            log.info(f"Document saved: {filename}")

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

                    # Reset working directory to repo to ensure next Save As defaults correctly
                    self._panel._set_freecad_working_directory(repo_root)

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
        finally:
            # Always exit -- a no-op if we never entered (e.g. lfs mode,
            # or a save outside the repo), so this is safe unconditionally.
            settings.exit_git_friendly_compression_scope()

    def _do_refresh(self):
        """Execute deferred refresh after save."""
        try:
            if self._panel._current_repo_root:
                log.info("Auto-refreshing status after save")
                self._panel._refresh_status_views(self._panel._current_repo_root)
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
        # Bottom-docked strip, not a sidebar: no minimum width constraint,
        # just enough height for the three compact rows.
        self.setMinimumHeight(120)

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
        # GitHub/other-host connection UI + its handlers now live in the
        # standalone ConnectionsDialog (reachable from the GitPDM menu),
        # constructed eagerly below so startup connection checks still run
        # against real widgets regardless of dialog visibility.
        self._connections_dialog = ConnectionsDialog(self, self._services)
        self._fetch_pull = FetchPullHandler(self, self._git_client, self._job_runner)
        self._commit_push = CommitPushHandler(self, self._git_client, self._job_runner)
        self._repo_validator = RepoValidationHandler(self, self._git_client)
        self._branch_ops = BranchOperationsHandler(
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
        # Phase G5 (R2.3): periodic heartbeat so our session lock doesn't
        # look abandoned/stale to a second instance during a long session.
        self._lock_refresh_timer = QtCore.QTimer(self)
        self._lock_refresh_timer.setInterval(5 * 60 * 1000)
        self._lock_refresh_timer.timeout.connect(self._on_lock_refresh_tick)
        self._lock_refresh_timer.start()
        # Phase G6 (R2.5): continuous checkpointing. The tick interval is
        # just the scheduler's polling granularity, not the checkpoint
        # cadence itself -- should_checkpoint() (idle-debounce + max-interval
        # backstop) decides whether a given tick actually does anything.
        self._checkpoint_state = checkpoint.CheckpointState()
        self._checkpoint_timer = QtCore.QTimer(self)
        self._checkpoint_timer.setInterval(10 * 1000)
        self._checkpoint_timer.timeout.connect(self._on_checkpoint_timer_tick)
        self._checkpoint_timer.start()
        self._cached_has_remote = False
        self._is_refreshing_status = (
            False  # Sprint PERF-1: prevent concurrent status refreshes
        )
        self._is_updating_upstream = (
            False  # Sprint PERF-1: prevent concurrent upstream updates
        )
        self._doc_observer = None
        self._current_storage_mode = storage_mode.DEFAULT_MODE
        self._group_git_check = None
        self._group_repo_selector = None
        self._group_status = None
        self._group_branch = None
        self._group_actions = None
        self._actions_extra_container = None
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

        # Hidden/dormant sections (System check, Branch) don't participate
        # in the visible layout either way.
        self._build_git_check_section(main_layout)
        self._build_branch_section(main_layout)

        # Repository / Status / Actions share a single row of columns
        # instead of stacking as full-width blocks, so the panel stays
        # short when docked at the bottom.
        columns_row = QtWidgets.QHBoxLayout()
        columns_row.setSpacing(8)
        self._build_repo_selector(columns_row)
        self._build_status_section(columns_row)
        self._build_changes_section(main_layout)
        self._wire_changes_popup()
        self._build_buttons_section(columns_row)
        columns_row.setStretchFactor(self._group_repo_selector, 3)
        columns_row.setStretchFactor(self._group_status, 2)
        columns_row.setStretchFactor(self._group_actions, 4)
        main_layout.addLayout(columns_row)

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

    def _set_meta_label(self, label, color="gray"):
        label_style.set_meta_label(label, color, self._meta_font_size)

    def _set_strong_label(self, label, color="black"):
        label_style.set_strong_label(label, color, self._strong_font_size)

    def _deferred_initialization(self):
        """Run heavy initialization after panel is shown (Sprint PERF-2: fully async)."""
        try:
            # G3: recover from a compression scope left active by a
            # previous session that crashed mid-save (see core/settings.py)
            settings.recover_stuck_compression_scope()

            # Sprint PERF-2: Check git availability in background (immediate)
            QtCore.QTimer.singleShot(10, self._check_git_available_async)

            # Sprint PERF-2: Load saved repo path and validate in background (immediate)
            QtCore.QTimer.singleShot(20, self._load_saved_repo_path_async)

            # Register document observer to auto-refresh on save
            self._register_document_observer()

            # Load GitHub connection status (Sprint OAUTH-1) - slightly delayed
            QtCore.QTimer.singleShot(
                50, self._connections_dialog._github_auth.refresh_connection_status
            )
            # Sprint OAUTH-2: Auto-verify identity in background with cooldown
            QtCore.QTimer.singleShot(
                100, self._connections_dialog._github_auth.maybe_auto_verify_identity
            )

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
                self._doc_observer = _DocumentObserver(self)
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

        if self._current_repo_root:
            try:
                session_lock.release_lock(self._current_repo_root)
            except Exception as e:
                log.debug(f"Failed to release session lock on close: {e}")

        super().closeEvent(event)

    def open_connections_dialog(self):
        """Show the GitHub/other-host connections dialog (GitPDM menu entry)."""
        self._connections_dialog.show()
        self._connections_dialog.raise_()
        self._connections_dialog.activateWindow()

    def _on_lock_refresh_tick(self):
        """Heartbeat: keep our session lock's timestamp fresh (R2.3)."""
        if self._current_repo_root:
            try:
                session_lock.refresh_lock(self._current_repo_root)
            except Exception as e:
                log.debug(f"Failed to refresh session lock: {e}")

    def _on_checkpoint_timer_tick(self):
        """
        Scheduler poll (Phase G6 / R2.5): ask the pure should_checkpoint()
        decision whether this tick should actually run a checkpoint, and if
        so, run one via core/checkpoint.py's FreeCAD-agnostic orchestration.
        """
        if not self._current_repo_root:
            return
        try:
            now = time.time()
            max_interval = checkpoint.max_interval_seconds_for_repo(
                self._current_repo_root
            )
            if not checkpoint.should_checkpoint(
                self._checkpoint_state, now, max_interval_seconds=max_interval
            ):
                return

            result = checkpoint.run_checkpoint(
                self._git_client,
                self._current_repo_root,
                is_busy=self._is_freecad_busy,
                save_if_dirty=self._save_active_document_if_dirty,
            )
            if result.ok:
                self._checkpoint_state.note_checkpoint(now)
                log.debug(
                    f"Checkpoint committed {result.sha[:8]}"
                    + (" (pushed)" if result.pushed else "")
                )
            elif result.skipped_reason == "busy":
                log.debug("Checkpoint deferred: FreeCAD is mid-edit")
            else:
                log.debug(f"Checkpoint failed: {result.message}")
        except Exception as e:
            log.debug(f"Checkpoint tick failed: {e}")

    def _is_freecad_busy(self):
        """
        Best-effort "don't save mid-edit" guard (R2.5). Fails CLOSED (treats
        an unreadable state as busy and skips this tick) rather than open,
        since the failure mode of a wrongly-skipped checkpoint is just a
        delayed one, while the failure mode of saving mid-edit could corrupt
        in-progress work.

        `Control.activeDialog()` returns a bool (True when a task dialog/
        panel is active, e.g. mid-sketch-edit), not the dialog object or
        None -- checking it with `is not None` is always True regardless of
        the actual state (`False is not None` == True), which made this
        method permanently report "busy" and silently block every
        checkpoint. Found live 2026-07-19 via a real FreeCAD session.
        """
        try:
            import FreeCAD
            import FreeCADGui

            doc = FreeCAD.ActiveDocument
            if doc is not None and getattr(doc, "HasPendingTransaction", False):
                return True
            if FreeCADGui.Control.activeDialog():
                return True
            return False
        except Exception as e:
            log.debug(f"Busy check failed, treating as busy: {e}")
            return True

    def _save_active_document_if_dirty(self):
        """
        Perform FreeCAD's blocking whole-document save, but only if there
        are unsaved changes to a document that has already been saved once
        (a never-saved document has nothing on disk yet for a checkpoint to
        capture, and forcing a first Save-As dialog would defeat the point
        of a background checkpoint). NOTE: not live-verified (same caveat
        as _is_freecad_busy above).
        """
        try:
            import FreeCAD

            doc = FreeCAD.ActiveDocument
            if doc is None or not doc.FileName:
                return
            if hasattr(doc, "isTouched") and not doc.isTouched():
                return
            doc.save()
            log.debug("Checkpoint triggered a document save")
        except Exception as e:
            log.debug(f"Checkpoint save-if-dirty failed: {e}")

    def _clear_recovery_checkpoint_clicked(self):
        """GitPDM menu entry: manually clear the recovery branch (Phase G6 /
        R2.5's prune offer, available on demand rather than only after the
        next real commit)."""
        if not self._current_repo_root:
            return
        status = checkpoint.recovery_branch_status(
            self._git_client, self._current_repo_root
        )
        if not status.available:
            QtWidgets.QMessageBox.information(
                self,
                "No Recovery Checkpoint",
                "There is no recovery checkpoint to clear.",
            )
            return
        reply = QtWidgets.QMessageBox.question(
            self,
            "Clear Recovery Checkpoint?",
            f"Clear the recovery checkpoint ({status.recovery_sha[:8]})?\n\n"
            "This does not affect your committed history or working files.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            checkpoint.prune_recovery_branch(self._git_client, self._current_repo_root)
            log.info("Recovery checkpoint cleared via GitPDM menu")

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
        self.git_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.git_label.setStyleSheet("color: orange;")
        group_layout.addRow("Git", self.git_label)

        layout.addWidget(group)
        # Hide the System section per request
        group.setVisible(False)
        self._group_git_check = group

    def _check_git_available(self):
        """Check if git is available on system (synchronous - for backward compatibility)."""
        is_available = self._git_client.is_git_available()
        if is_available:
            version = self._git_client.git_version()
            self.git_label.setText(f"● OK ({version})")
            self.git_label.setStyleSheet("color: green;")
        else:
            self.git_label.setText("● Not found")
            self.git_label.setStyleSheet("color: red;")
            log.warning("Git not available on PATH")

    def _check_git_available_async(self):
        """Check if git is available on system (Sprint PERF-2: async version)."""

        def _check_git():
            is_available = self._git_client.is_git_available()
            version = self._git_client.git_version() if is_available else None
            return {"is_available": is_available, "version": version}

        self._job_runner.run_callable(
            "check_git",
            _check_git,
            on_success=self._on_git_check_complete,
            on_error=lambda e: log.error(f"Git check error: {e}"),
        )

    def _on_git_check_complete(self, result):
        """Callback when async git check completes (Sprint PERF-2)."""
        is_available = result.get("is_available")
        version = result.get("version")

        if is_available:
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

        # First-run guidance (Phase G5 / R2.4b) - shown only when no repo
        # path has been configured yet, so a fresh install doesn't just show
        # blank fields with no indication of what to do next. Entirely
        # framing: the buttons it points at ("Join Team Project…", "Start
        # New Project…") already exist and already require no terminal.
        self._first_run_hint = QtWidgets.QLabel(
            "No repository yet — clone an existing one or start a new one "
            "below to get started."
        )
        self._first_run_hint.setWordWrap(True)
        self._first_run_hint.setStyleSheet(
            "color: #0066cc; font-style: italic; font-size: 10px;"
        )
        self._first_run_hint.setVisible(False)
        group_layout.addWidget(self._first_run_hint)

        # Repo name (bold header) on its own line.
        self.repo_name_label = QtWidgets.QLabel("No repository selected")
        self._set_strong_label(self.repo_name_label, "black")
        self.repo_name_label.setWordWrap(True)
        group_layout.addWidget(self.repo_name_label)

        # Path field on its own line -- still the real, editable field
        # (programmatic .setText()/.text() used throughout the codebase),
        # just visually de-emphasized under the bold name above.
        self.repo_path_field = QtWidgets.QLineEdit()
        self.repo_path_field.setPlaceholderText("Select your project folder...")
        self.repo_path_field.setToolTip(
            "The folder where your FreeCAD project files are stored\n"
            "(Git term: 'repository' or 'repo' - the project folder tracked by Git)"
        )
        self.repo_path_field.setStyleSheet("color: gray;")
        self.repo_path_field.editingFinished.connect(
            self._on_repo_path_editing_finished
        )
        self.repo_path_field.textChanged.connect(self._on_repo_path_text_changed)
        group_layout.addWidget(self.repo_path_field)

        # Browse / Join / Start New: three separate, always-visible buttons
        # (not nested behind a dropdown) since switching/starting projects
        # is something people reach for often.
        switch_row = QtWidgets.QHBoxLayout()
        switch_row.setSpacing(4)

        browse_btn = QtWidgets.QPushButton("Browse…")
        browse_btn.setToolTip(
            "Select an existing project folder on your computer\n"
            "(Git term: open a local 'repository')"
        )
        browse_btn.clicked.connect(self._on_browse_clicked)
        switch_row.addWidget(browse_btn)

        clone_btn = QtWidgets.QPushButton("Join Team…")
        clone_btn.setToolTip(
            "Download a project from GitHub to work on with your team\n"
            "(Git term: 'clone' - makes a local copy of a remote repository)"
        )
        clone_btn.clicked.connect(self._on_open_clone_repo_clicked)
        switch_row.addWidget(clone_btn)

        new_repo_btn = QtWidgets.QPushButton("New Project…")
        new_repo_btn.setToolTip(
            "Create a brand new project and store it on GitHub\n"
            "(Git term: 'init' + create remote 'repository')"
        )
        new_repo_btn.clicked.connect(self._on_new_repo_clicked)
        switch_row.addWidget(new_repo_btn)

        group_layout.addLayout(switch_row)

        # Shallow-clone banner (Phase G5 / R2.4) - hidden unless the active
        # repo is a shallow clone, so history-truncated state is visible
        # and recoverable without leaving the panel.
        self._shallow_banner = QtWidgets.QWidget()
        shallow_layout = QtWidgets.QHBoxLayout()
        shallow_layout.setContentsMargins(0, 0, 0, 0)
        shallow_layout.setSpacing(6)
        self._shallow_banner.setLayout(shallow_layout)

        shallow_label = QtWidgets.QLabel("History truncated (shallow clone)")
        shallow_label.setStyleSheet(
            "color: #b35900; font-style: italic; font-size: 10px;"
        )
        shallow_layout.addWidget(shallow_label)

        self._deepen_btn = QtWidgets.QPushButton("Deepen")
        self._deepen_btn.setToolTip(
            "Fetch older history so log/diff/blame views aren't truncated"
        )
        self._deepen_btn.clicked.connect(self._on_deepen_clicked)
        shallow_layout.addWidget(self._deepen_btn)
        shallow_layout.addStretch()

        self._shallow_banner.setVisible(False)
        group_layout.addWidget(self._shallow_banner)

        # Repo root label (resolved path, read-only)
        # Root details (collapsed by default)
        self.root_toggle_btn = QtWidgets.QToolButton()
        self.root_toggle_btn.setText("Show root")
        self.root_toggle_btn.setArrowType(QtCore.Qt.RightArrow)
        self.root_toggle_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.root_toggle_btn.setCheckable(True)
        self.root_toggle_btn.setEnabled(False)
        self.root_toggle_btn.toggled.connect(self._on_root_toggle)
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
        self.repo_root_label.setStyleSheet("color: gray; font-size: 10px;")
        self.repo_root_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
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
        self.validate_label.setStyleSheet("color: gray; font-style: italic;")
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

    def _build_status_section(self, layout):
        """
        Build the simple status row: pending changes + sync status only.

        Everything denser (branch, upstream ref, last-checked time, storage
        mode) still gets built and kept live-updated by the exact same code
        paths as before (repo_validator.py / fetch_pull.py / branch_ops.py /
        commit_push.py all still call .setText() on these widgets by name),
        it's just not laid out on screen any more -- it surfaces as tooltip
        text on the two visible chips instead (see
        _refresh_status_chip_tooltips), consistent with "simple status bar
        that only shows pending changes and sync status".
        """
        group = QtWidgets.QGroupBox("Status")
        group_layout = QtWidgets.QVBoxLayout()
        group_layout.setContentsMargins(6, 4, 6, 4)
        group_layout.setSpacing(4)
        group.setLayout(group_layout)

        # Compact row: pending-changes chip (clickable, pops the changes
        # list -- see _wire_changes_popup) + sync-status chip + operation
        # status, right-aligned.
        chip_row = QtWidgets.QHBoxLayout()
        chip_row.setSpacing(8)

        self.working_tree_label = QtWidgets.QToolButton()
        self.working_tree_label.setText("—")
        self.working_tree_label.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.working_tree_label.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.working_tree_label.setAutoRaise(True)
        self._set_strong_label(self.working_tree_label, "black")
        chip_row.addWidget(self.working_tree_label)

        self.ahead_behind_label = QtWidgets.QLabel("—")
        self.ahead_behind_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self._set_strong_label(self.ahead_behind_label, "black")
        chip_row.addWidget(self.ahead_behind_label)

        chip_row.addStretch()

        self.operation_status_label = QtWidgets.QLabel("Ready")
        self.operation_status_label.setStyleSheet("color: gray; font-size: 9px;")
        self.operation_status_label.setAlignment(QtCore.Qt.AlignRight)
        chip_row.addWidget(self.operation_status_label)

        group_layout.addLayout(chip_row)

        # Dense fields (branch/upstream/last-checked/storage mode): built
        # exactly as before, wrapped in a hidden container instead of a
        # visible grid. Their update call sites elsewhere in the codebase
        # are untouched.
        dense_container = QtWidgets.QWidget()
        dense_layout = QtWidgets.QGridLayout()
        dense_layout.setContentsMargins(0, 0, 0, 0)
        dense_container.setLayout(dense_layout)

        self.branch_label = QtWidgets.QLabel("—")
        self.upstream_label = QtWidgets.QLabel("—")
        self.last_fetch_label = QtWidgets.QLabel("—")
        self.storage_mode_label = QtWidgets.QLabel("—")
        dense_layout.addWidget(self.branch_label, 0, 0)
        dense_layout.addWidget(self.upstream_label, 0, 1)
        dense_layout.addWidget(self.last_fetch_label, 0, 2)
        dense_layout.addWidget(self.storage_mode_label, 0, 3)
        self.storage_mode_change_btn = QtWidgets.QPushButton("Change…")
        self.storage_mode_change_btn.setEnabled(False)
        self.storage_mode_change_btn.setToolTip(
            "Switch between Delta (free, default) and LFS (opt-in, for "
            "teams) storage modes for *.FCStd files"
        )
        self.storage_mode_change_btn.clicked.connect(
            self._repo_validator.change_storage_mode_clicked
        )
        dense_layout.addWidget(self.storage_mode_change_btn, 0, 4)
        dense_container.setVisible(False)
        group_layout.addWidget(dense_container)

        # Error/message area (Sprint 2)
        self.status_message_label = QtWidgets.QLabel("")
        self.status_message_label.setWordWrap(True)
        self.status_message_label.setStyleSheet("color: red; font-size: 10px;")
        self.status_message_label.hide()
        group_layout.addWidget(self.status_message_label)

        layout.addWidget(group)
        self._group_status = group

    def _refresh_status_chip_tooltips(self):
        """Compose the dense branch/upstream/storage info (no longer laid
        out visibly) into tooltips on the two status chips."""
        changes_tip = (
            "Files you've modified but haven't saved as a version yet\n"
            "(Git term: 'working tree status' or 'dirty/clean state')\n\n"
            f"Work version: {self.branch_label.text()}\n"
            f"Storage mode: {self.storage_mode_label.text()}"
        )
        self.working_tree_label.setToolTip(changes_tip)

        sync_tip = (
            "How many changes you need to share or get from your team\n"
            "(Git term: 'ahead/behind' - commits to push/pull)\n\n"
            f"GitHub version: {self.upstream_label.text()}\n"
            f"Last checked: {self.last_fetch_label.text()}"
        )
        self.ahead_behind_label.setToolTip(sync_tip)

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

    def _build_changes_section(self, layout):
        """
        Build the changed-files list as popup content for the pending-changes
        chip in the status row, rather than an always-visible group -- see
        _wire_changes_popup, called right after this in __init__ once
        working_tree_label (the chip) exists too.

        Args:
            layout: Parent layout of the main panel (unused; kept for
                symmetry with the other _build_* methods and because this
                content is still logically part of the same build pass).
        """
        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout()
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(4)
        content.setLayout(content_layout)

        info_label = QtWidgets.QLabel("Files modified since your last save checkpoint.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        content_layout.addWidget(info_label)

        self.changes_list = QtWidgets.QListWidget()
        self.changes_list.setMinimumSize(260, 140)
        self.changes_list.setEnabled(False)
        content_layout.addWidget(self.changes_list)

        self._changes_popup_content = content

    def _wire_changes_popup(self):
        """Attach the changes-list popup content to the pending-changes chip."""
        menu = QtWidgets.QMenu(self.working_tree_label)
        action = QtWidgets.QWidgetAction(menu)
        action.setDefaultWidget(self._changes_popup_content)
        menu.addAction(action)
        self.working_tree_label.setMenu(menu)

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

        row1_layout.addStretch()

        self.stage_all_checkbox = QtWidgets.QCheckBox("Include all changed files")
        self.stage_all_checkbox.setChecked(True)
        self.stage_all_checkbox.setEnabled(False)
        self.stage_all_checkbox.setToolTip(
            "When saving, include all files you've modified (recommended)\n"
            "(Git term: 'stage' or 'add' - marks files to include in the next commit)"
        )
        self.stage_all_checkbox.stateChanged.connect(self._update_button_states)
        row1_layout.addWidget(self.stage_all_checkbox)

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
        self.commit_message.setMaximumHeight(40)
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

    def _handle_repo_picker_result(self, dlg):
        """Shared post-dialog handling for any successful RepoPickerDialog
        clone, regardless of which provider it browsed."""
        cloned_path = dlg.cloned_path()
        if not cloned_path:
            return

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
                lambda: self._set_freecad_working_directory(self._current_repo_root),
            )
            QtCore.QTimer.singleShot(
                500,
                lambda: self._set_freecad_working_directory(self._current_repo_root),
            )

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
                self._handle_repo_picker_result(dlg)
        except Exception as e:
            log.error(f"Open/Clone flow failed: {e}")
            QtWidgets.QMessageBox.warning(
                self,
                "Open/Clone Repo",
                "Failed to open repo picker. See logs for details.",
            )

    def _on_new_repo_clicked(self):
        """Open New Repo wizard to create a repo (GitHub, or any other git
        remote) + local scaffold. GitHub connection is optional (Phase G4):
        the wizard's provider page offers "another git remote" when it's
        unavailable, so it's never a hard requirement to get started."""
        try:
            from freecad_gitpdm.ui.new_repo_wizard import NewRepoWizard

            # GitHub is one option among several; not connecting just means
            # the wizard defaults to the generic-remote path.
            api_client = self._create_github_client()

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

    def _on_repo_path_text_changed(self, text):
        """Keep the bold repo-name header row 1 chip in sync with the path
        field, whichever way its text changed (typed or set programmatically)."""
        name = os.path.basename(os.path.normpath(text)) if text else ""
        self.repo_name_label.setText(name or "No repository selected")

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

    def _check_shallow_clone_status(self, repo_root):
        """Show/hide the shallow-clone banner for repo_root (Phase G5 / R2.4)."""
        if not repo_root:
            self._shallow_banner.setVisible(False)
            return

        def _check():
            return self._git_client.is_shallow_repo(repo_root)

        self._job_runner.run_callable(
            "check_shallow_repo",
            _check,
            on_success=self._on_shallow_status_checked,
            on_error=lambda e: log.debug(f"Shallow-clone check failed: {e}"),
        )

    def _on_shallow_status_checked(self, is_shallow):
        self._shallow_banner.setVisible(bool(is_shallow))

    def _on_deepen_clicked(self):
        """Fetch older history into a shallow clone (Phase G5 / R2.4)."""
        if not self._current_repo_root:
            return
        repo_root = self._current_repo_root
        self._deepen_btn.setEnabled(False)
        self._deepen_btn.setText("Deepening…")

        self._job_runner.run_callable(
            "deepen_repo",
            lambda: self._git_client.deepen_repo(repo_root),
            on_success=lambda result: self._on_deepen_finished(repo_root, result),
            on_error=lambda e: self._on_deepen_finished(repo_root, None, error=e),
        )

    def _on_deepen_finished(self, repo_root, result, error=None):
        self._deepen_btn.setEnabled(True)
        self._deepen_btn.setText("Deepen")

        if error is not None or result is None or not getattr(result, "ok", False):
            detail = str(error) if error is not None else getattr(result, "stderr", "")
            log.warning(f"Deepen failed: {detail}")
            self._show_status_message("Failed to fetch older history", is_error=True)
            return

        log.info(f"Deepened history for {repo_root}")
        self._show_status_message("Fetched older history", is_error=False)
        if repo_root == self._current_repo_root:
            self._check_shallow_clone_status(repo_root)

    def _update_upstream_info(self, repo_root):
        """
        Update upstream ref and ahead/behind counts (async via job_runner).
        Uses tracking upstream (@{u}) if available, otherwise falls back to default.

        Args:
            repo_root: str - repository root path
        """
        # Sprint PERF-1: Move to background to avoid blocking UI
        if not repo_root:
            return

        # Prevent concurrent upstream updates
        if self._is_updating_upstream:
            log.debug("Upstream update already in progress, skipping")
            return

        self._is_updating_upstream = True

        # Check remote status (fast, local operation)
        self._cached_has_remote = self._git_client.has_remote(
            repo_root, self._remote_name
        )

        if not self._cached_has_remote:
            self._is_updating_upstream = False
            self._ahead_count = 0
            self._behind_count = 0
            self.upstream_label.setText("(no remote)")
            self._set_meta_label(self.upstream_label, "gray")
            self.ahead_behind_label.setText("(unknown)")
            self._set_strong_label(self.ahead_behind_label, "gray")
            self._upstream_ref = None
            self._update_button_states()
            return

        # Show calculating state
        self.ahead_behind_label.setText("Calculating…")
        self._set_strong_label(self.ahead_behind_label, "gray")

        # Run ahead/behind calculation in background
        def _fetch_upstream():
            ab_result = self._git_client.get_ahead_behind_with_upstream(repo_root)
            return ab_result

        self._job_runner.run_callable(
            "update_upstream",
            _fetch_upstream,
            on_success=self._on_upstream_update_complete,
            on_error=self._on_upstream_update_error,
        )

    def _on_upstream_update_complete(self, ab_result):
        """Callback when async upstream update completes (Sprint PERF-1)."""
        try:
            self._is_updating_upstream = False

            upstream_ref = ab_result.get("upstream")

            # Log upstream status
            msg = f"Upstream: {upstream_ref if upstream_ref else '(not set)'}"
            log.info(msg)

            if not upstream_ref:
                # No upstream configured for this branch
                self._ahead_count = 0
                self._behind_count = 0
                self.upstream_label.setText("(not set)")
                self._set_meta_label(self.upstream_label, "orange")
                self.ahead_behind_label.setText("(unknown)")
                self._set_strong_label(self.ahead_behind_label, "gray")
                self._upstream_ref = None
                self._refresh_status_chip_tooltips()
                self._update_button_states()
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

                if ahead == 0 and behind == 0:
                    ab_text = "Up to date"
                elif ahead > 0 and behind > 0:
                    ab_text = f"{ahead} to share | {behind} to get"
                elif ahead > 0:
                    ab_text = f"{ahead} to share \u2191"
                else:
                    ab_text = f"{behind} to get \u2193"

                if ahead == 0 and behind == 0:
                    self._set_strong_label(self.ahead_behind_label, "green")
                elif behind > 0:
                    self._set_strong_label(self.ahead_behind_label, "orange")
                else:
                    self._set_strong_label(self.ahead_behind_label, "#4db6ac")

                self.ahead_behind_label.setText(ab_text)
            else:
                self.ahead_behind_label.setText("(error)")
                self._set_strong_label(self.ahead_behind_label, "red")
                if ab_result["error"]:
                    log.debug(f"Ahead/behind error: {ab_result['error']}")

            self._refresh_status_chip_tooltips()
            self._update_button_states()
            log.debug("Upstream update complete")
        except Exception as e:
            log.error(f"Error processing upstream update result: {e}")
            self._is_updating_upstream = False

    def _on_upstream_update_error(self, error):
        """Callback when async upstream update fails (Sprint PERF-1)."""
        self._is_updating_upstream = False
        log.warning(f"Upstream update error: {error}")
        self.ahead_behind_label.setText("(error)")
        self._set_strong_label(self.ahead_behind_label, "red")
        self._refresh_status_chip_tooltips()
        self._update_button_states()

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
        Show a status message in the status section

        Args:
            message: str - message to display
            is_error: bool - whether this is an error message
        """
        if message:
            self.status_message_label.setText(message)
            if is_error:
                self.status_message_label.setStyleSheet("color: red; font-size: 10px;")
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
        Update the operation status label.

        Args:
            status_text: str - status message
        """
        self.operation_status_label.setText(status_text)
        if status_text == "Ready":
            self.operation_status_label.setStyleSheet("color: gray; font-size: 9px;")
        elif "…" in status_text:
            self.operation_status_label.setStyleSheet("color: orange; font-size: 9px;")
        elif status_text == "Synced":
            self.operation_status_label.setStyleSheet("color: green; font-size: 9px;")
        else:
            self.operation_status_label.setStyleSheet("color: red; font-size: 9px;")

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
        Display working tree status in UI

        Args:
            status: dict - status summary from GitClient
        """
        if status["is_clean"]:
            self.working_tree_label.setText("No changes")
            self._set_strong_label(self.working_tree_label, "green")
        else:
            parts = []
            if status["modified"] > 0:
                parts.append(f"{status['modified']} modified")
            if status["added"] > 0:
                parts.append(f"{status['added']} new")
            if status["deleted"] > 0:
                parts.append(f"{status['deleted']} deleted")
            if status["untracked"] > 0:
                parts.append(f"{status['untracked']} unsaved")

            status_str = " | ".join(parts)
            self.working_tree_label.setText(status_str)
            self._set_strong_label(self.working_tree_label, "orange")

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

            self._refresh_status_chip_tooltips()
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
        """Update changes list widget with current file statuses using friendly labels."""
        self.changes_list.clear()

        if not self._file_statuses:
            return

        for entry in self._file_statuses:
            # Convert Git status codes to user-friendly text with icons
            status_text = self._friendly_status_text(entry.x, entry.y)
            text = f"{status_text} {entry.path}"
            self.changes_list.addItem(text)

    def _friendly_status_text(self, x, y):
        """
        Convert Git status codes to friendly text with visual indicators.

        Args:
            x: index status character
            y: working tree status character

        Returns:
            str: Friendly status text with icon/emoji
        """
        # Handle common two-character combinations first
        code = f"{x}{y}"

        # Modified in working tree
        if code in [" M", "MM", "AM"]:
            return "📝 Modified"

        # New file (untracked or added)
        if code in ["??", "A ", "AM"]:
            return "➕ New"

        # Deleted
        if code in [" D", "D ", "AD"]:
            return "➖ Deleted"

        # Renamed
        if code in ["R ", "RM"]:
            return "📋 Renamed"

        # Copied
        if code in ["C ", "CM"]:
            return "📋 Copied"

        # Updated but unmerged (conflict)
        if code in ["UU", "AA", "DD"]:
            return "⚠️ Conflict"

        # Default: show the code if we don't recognize it
        return f"[{code}]"

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

    def _update_storage_mode_label(self):
        """Refresh the Storage Mode row (label text + Change… enabled state)."""
        has_repo = bool(self._current_repo_root)
        if has_repo:
            self.storage_mode_label.setText(self._current_storage_mode)
        else:
            self.storage_mode_label.setText("—")
        self.storage_mode_change_btn.setEnabled(has_repo)
        self._refresh_status_chip_tooltips()

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
        if self.stage_previews_checkbox.isChecked() and result.rel_dir:
            git_cmd = self._git_client._get_git_command()
            png_rel = result.rel_dir + "preview.png"
            json_rel = result.rel_dir + "preview.json"
            args = [
                git_cmd,
                "-C",
                self._current_repo_root,
                "add",
                "--",
                png_rel,
                json_rel,
            ]
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
        self._first_run_hint.setVisible(not saved_path)
        if saved_path:
            self.repo_path_field.blockSignals(True)
            self.repo_path_field.setText(saved_path)
            self.repo_path_field.blockSignals(False)
            self._on_repo_path_text_changed(saved_path)
            # Auto-validate on load
            self._validate_repo_path(saved_path)
            log.info(f"Restored repo path from settings: {saved_path}")
        # Initialize preview status area
        self._update_preview_status_labels()

    def _load_saved_repo_path_async(self):
        """Load saved repository path and validate in background (Sprint PERF-2)."""
        saved_path = settings.load_repo_path()
        self._first_run_hint.setVisible(not saved_path)
        if saved_path:
            # Display path immediately
            self.repo_path_field.blockSignals(True)
            self.repo_path_field.setText(saved_path)
            self.repo_path_field.blockSignals(False)
            self._on_repo_path_text_changed(saved_path)
            log.info(f"Restored repo path from settings: {saved_path}")
            # Validate in background (non-blocking)
            self._validate_repo_path(saved_path)
        # Initialize preview status area
        self._update_preview_status_labels()

    # ========== GitHub client factory (used by repo-picker/new-repo-wizard) =====
    # Connect/disconnect/verify UI now lives in ConnectionsDialog
    # (freecad_gitpdm/ui/connections_dialog.py); this factory stays here since
    # it's consumed by this panel's own Join Team Project / Start New Project
    # flows.

    def _create_github_client(self):
        """Construct a GitHubApiClient using stored token; returns None if not connected."""
        try:
            return self._services.github_api_client()
        except Exception as e:
            log.debug(f"Failed to create GitHub client: {e}")
            return None
