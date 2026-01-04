# -*- coding: utf-8 -*-
"""
Fetch/Pull Handler Module
Sprint 4: Extracted from panel.py to manage fetch and pull operations.
"""

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

from datetime import datetime, timezone

from freecad_gitpdm.core import log, settings
from freecad_gitpdm.ui import dialogs


class FetchPullHandler:
    """
    Handles fetch and pull operations.

    Manages:
    - Fetch from remote
    - Pull (fetch + fast-forward merge)
    - Pull sequence (fetch, pull, refresh)
    - Last fetch timestamp display
    - Error handling and user dialogs
    """

    def __init__(self, parent, git_client, job_runner):
        """
        Initialize fetch/pull handler.

        Args:
            parent: GitPDMDockWidget - parent panel with UI widgets and state
            git_client: GitClient - for git operations
            job_runner: JobRunner - for background operations
        """
        self._parent = parent
        self._git_client = git_client
        self._job_runner = job_runner

        # Operation state
        self._is_fetching = False
        self._is_pulling = False

    # ========== Public API ==========

    def fetch_clicked(self):
        """
        Handle Fetch button click.
        Run fetch in background via job runner.
        """
        if not self._parent._current_repo_root:
            log.warning("No repository to fetch")
            return

        if self._is_fetching:
            log.debug("Fetch already in progress, ignoring click")
            return

        # Clear previous messages
        self._parent._clear_status_message()

        # Set fetching state
        self._is_fetching = True
        self._parent.fetch_btn.setText("Fetching…")
        self._parent.fetch_btn.setEnabled(False)
        self._parent._start_busy_feedback("Fetching…")

        log.info(f"Starting fetch from {self._parent._remote_name}")

        # Build command
        git_cmd = self._git_client._get_git_command()
        command = [
            git_cmd,
            "-C",
            self._parent._current_repo_root,
            "fetch",
            self._parent._remote_name,
        ]

        # Run via job runner
        self._job_runner.run_job("fetch", command, callback=self._on_fetch_finished)

    def pull_clicked(self):
        """
        Handle Pull button click.
        Check for uncommitted changes; if present, show warning.
        Then run pull sequence: fetch -> pull -> refresh.
        """
        log.info("Pull button clicked!")

        if not self._parent._current_repo_root:
            log.warning("No repository to pull")
            return

        if self._is_pulling or self._is_fetching:
            log.debug("Pull/fetch already in progress")
            return

        # CRITICAL Guard: block pull while ANY FreeCAD files are open
        # Pull can modify working tree files, corrupting open .FCStd files
        open_docs = self._parent._get_all_open_fcstd_documents()
        if open_docs:
            details_lines = ["Open FreeCAD documents:"]
            details_lines.extend([f"  - {p}" for p in open_docs[:10]])
            if len(open_docs) > 10:
                details_lines.append(f"  ... and {len(open_docs) - 10} more")

            QtWidgets.QMessageBox.critical(
                self._parent,
                "Close ALL Files First",
                "⚠️ CRITICAL: Close ALL FreeCAD documents before pulling!\n\n"
                "Git pull can modify files in the working tree, which will corrupt "
                ".FCStd files that are currently open in FreeCAD.\n\n"
                "Please close ALL FreeCAD documents (File → Close All) and try again.\n\n"
                + "\n".join(details_lines),
            )
            log.warning("Pull blocked - open FreeCAD documents detected")
            return

        log.info(f"Starting pull for repo: {self._parent._current_repo_root}")

        # Clear previous messages
        self._parent._clear_status_message()

        # Check for uncommitted changes
        has_changes = self._git_client.has_uncommitted_changes(
            self._parent._current_repo_root
        )

        log.info(f"Has uncommitted changes: {has_changes}")

        if has_changes:
            # Show warning dialog
            dlg = dialogs.UncommittedChangesWarningDialog(self._parent)
            if not dlg.show_and_ask():
                log.info("User cancelled pull due to changes")
                return

        # Start pull sequence
        self._start_pull_sequence()

    def display_last_fetch(self):
        """
        Display the last fetch timestamp.
        Sprint 5 Phase 1.2: Delegated to StatusWidget.
        """
        last_fetch = settings.load_last_fetch_at()
        if last_fetch:
            # Parse ISO timestamp and format for display
            try:
                dt = datetime.fromisoformat(last_fetch)
                display_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                display_time = last_fetch
        else:
            display_time = "(never)"
        
        self._parent._status_widget.update_last_fetch_time(display_time)

    def handle_fetch_result(self, job):
        """
        Handle fetch job completion

        Args:
            job: dict - job result from job runner
        """
        result = job.get("result", {})
        success = result.get("success", False)

        # Reset fetching state
        self._is_fetching = False
        self._parent.fetch_btn.setText("Fetch")
        self._parent._stop_busy_feedback()

        if success:
            # Fetch succeeded
            fetch_time = datetime.now(timezone.utc).isoformat()
            settings.save_last_fetch_at(fetch_time)

            # Update UI
            self.display_last_fetch()

            # Re-evaluate upstream and ahead/behind
            if self._parent._current_repo_root:
                self._parent._update_upstream_info(self._parent._current_repo_root)

            self._parent._show_status_message(
                "Fetch completed successfully", is_error=False
            )
            log.info("Fetch completed successfully")

            # Clear success message after 3 seconds
            QtCore.QTimer.singleShot(3000, self._parent._clear_status_message)
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

            self._parent._show_status_message(error_msg, is_error=True)
            log.warning(f"Fetch failed: {stderr}")

        # Update button states
        self._parent._update_button_states()

    def is_busy(self):
        """Check if fetch or pull operation is in progress."""
        return self._is_fetching or self._is_pulling

    # ========== Private Implementation ==========

    def _on_fetch_finished(self, job):
        """Callback when fetch job finishes (delegates to handle_fetch_result)."""
        self.handle_fetch_result(job)

    def _start_pull_sequence(self):
        """
        Start the pull sequence: fetch -> pull -> refresh.
        This is an async workflow that keeps UI responsive.
        """
        if not self._parent._current_repo_root or not self._parent._upstream_ref:
            log.warning("Cannot start pull sequence")
            return

        self._is_pulling = True
        self._parent.pull_btn.setEnabled(False)
        self._parent.fetch_btn.setEnabled(False)
        self._parent._update_operation_status("Pulling…")
        self._parent._start_busy_feedback("Pulling…")

        # Step 1: Fetch from origin
        git_cmd = self._git_client._get_git_command()
        command = [
            git_cmd,
            "-C",
            self._parent._current_repo_root,
            "fetch",
            self._parent._remote_name,
        ]

        log.info("Pull sequence: starting fetch")
        self._job_runner.run_job(
            "pull_fetch", command, callback=self._on_pull_fetch_completed
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
            log.warning(f"Pull sequence aborted: fetch failed: {stderr}")
            self._handle_pull_failed("Fetch failed before pull")
            return

        log.info("Pull sequence: fetch completed, starting pull")

        # Step 2: Pull with ff-only
        if not self._parent._current_repo_root or not self._parent._upstream_ref:
            self._handle_pull_failed("Repository lost during pull")
            return

        git_cmd = self._git_client._get_git_command()
        # Extract branch from upstream (e.g., origin/main -> main)
        if "/" in self._parent._upstream_ref:
            branch = self._parent._upstream_ref.split("/", 1)[1]
        else:
            branch = self._parent._upstream_ref

        command = [
            git_cmd,
            "-C",
            self._parent._current_repo_root,
            "pull",
            "--ff-only",
            self._parent._remote_name,
            branch,
        ]

        self._job_runner.run_job(
            "pull_main", command, callback=self._on_pull_main_completed
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
            error_code = self._git_client._classify_pull_error(stderr)
            log.warning(f"Pull failed with error {error_code}: {stderr}")
            self._show_pull_error_dialog(error_code, stderr)
            self._is_pulling = False
            self._parent._update_operation_status("Error")
            self._parent._stop_busy_feedback()
            self._parent._update_button_states()
            return

        log.info("Pull completed successfully")
        self._parent._update_operation_status("Synced")
        self._parent._stop_busy_feedback()

        if self._parent._current_repo_root:
            branch = self._git_client.current_branch(self._parent._current_repo_root)
            self._parent.branch_label.setText(branch)

            self._parent._refresh_status_views(self._parent._current_repo_root)

            self._parent._update_upstream_info(self._parent._current_repo_root)
            # Refresh repo browser after pull
            self._parent._file_browser.refresh_files()

            pull_time = datetime.now(timezone.utc).isoformat()
            settings.save_last_pull_at(pull_time)

        self._is_pulling = False
        self._parent._show_status_message("Synced to latest", is_error=False)

        # Clear success message after 3 seconds
        QtCore.QTimer.singleShot(3000, self._parent._clear_status_message)

        self._parent._update_button_states()

    def _handle_pull_failed(self, message):
        """
        Handle pull failure.

        Args:
            message: str - failure message
        """
        self._is_pulling = False
        self._parent._update_operation_status("Error")
        self._parent._show_status_message(message, is_error=True)
        self._parent._stop_busy_feedback()
        self._parent._update_button_states()

    def _show_pull_error_dialog(self, error_code, stderr):
        """
        Show detailed error dialog for pull failure.

        Args:
            error_code: str - error classification
            stderr: str - raw error output
        """
        dlg = dialogs.PullErrorDialog(error_code, stderr, self._parent)
        dlg.exec()
