"""
Action-based Fetch/Pull Handler
Phase 2: Uses actions layer instead of direct GitClient calls
"""

from datetime import datetime, timezone

# Qt compatibility layer
try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    try:
        from PySide6 import QtCore, QtWidgets
    except ImportError as e:
        raise ImportError(
            "PySide6 not found. FreeCAD installation may be incomplete."
        ) from e

from freecad.gitpdm.core import log, settings
from freecad.gitpdm.actions import (
    fetch_from_remote,
    pull_from_remote,
    create_action_context,
)


class ActionFetchPullHandler:
    """
    Action-based fetch/pull handler.
    
    Uses actions layer for fetch and pull operations.
    Replaces direct GitClient calls with action functions.
    """

    def __init__(self, parent, git_client, job_runner):
        """
        Initialize action fetch/pull handler.

        Args:
            parent: GitPDMDockWidget - parent panel with UI widgets and state
            git_client: GitClient - wrapped by action backend
            job_runner: JobRunner - for background operations
        """
        self._parent = parent
        self._git_client = git_client
        self._job_runner = job_runner

        # Operation state
        self._is_fetching = False
        self._is_pulling = False

    # ========== Public API ==========

    def is_busy(self):
        """Check if fetch or pull operation is in progress."""
        return self._is_fetching or self._is_pulling

    def fetch_clicked(self):
        """
        Handle Fetch button click using actions layer.
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

        # Run fetch via actions layer
        def _run_fetch():
            ctx = create_action_context(
                self._git_client,
                self._parent._current_repo_root
            )
            result = fetch_from_remote(ctx, self._parent._remote_name)
            return result

        self._job_runner.run_callable(
            "fetch",
            _run_fetch,
            on_success=self._on_fetch_complete,
            on_error=self._on_fetch_error,
        )

    def pull_clicked(self):
        """
        Handle Pull button click using actions layer.
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
                "any open .FCStd files.\n\n"
                "Please:\n"
                "1. Save your work\n"
                "2. Close ALL FreeCAD documents (File → Close All)\n"
                "3. Try pull again\n\n"
                + "\n".join(details_lines),
            )
            return

        # Check for uncommitted changes
        has_changes = self._parent._changes_widget.has_changes()
        if has_changes:
            reply = QtWidgets.QMessageBox.question(
                self._parent,
                "Uncommitted Changes",
                "You have uncommitted changes. Pull may fail or create a merge.\n\n"
                "Recommended: Commit your changes first.\n\n"
                "Continue with pull anyway?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                log.info("Pull cancelled due to uncommitted changes")
                return

        # Start pull sequence
        self._start_pull_sequence()

    def display_last_fetch(self):
        """Display the last fetch timestamp in the UI."""
        last_fetch = settings.load_last_fetch_at()
        if last_fetch:
            try:
                dt = datetime.fromisoformat(last_fetch)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                self._parent.last_fetch_label.setText(f"Last fetch: {time_str}")
            except Exception as e:
                log.warning(f"Failed to parse last fetch time: {e}")
                self._parent.last_fetch_label.setText("Last fetch: (unknown)")
        else:
            self._parent.last_fetch_label.setText("Last fetch: (never)")

    # ========== Private Implementation ==========

    def _on_fetch_complete(self, result):
        """Callback when fetch completes successfully."""
        self._is_fetching = False
        self._parent.fetch_btn.setText("Check for Updates")
        self._parent.fetch_btn.setEnabled(True)
        self._parent._stop_busy_feedback()

        if result.ok:
            # Save fetch timestamp
            settings.save_last_fetch_at(
                datetime.now(timezone.utc).isoformat()
            )
            self.display_last_fetch()

            # Update upstream info
            self._parent._update_upstream_info(self._parent._current_repo_root)

            self._parent._show_status_message("Fetch completed", is_error=False)
            log.info("Fetch completed successfully")
        else:
            self._parent._show_status_message(
                f"Fetch failed: {result.message}", is_error=True
            )
            log.error(f"Fetch failed: {result.message}")

    def _on_fetch_error(self, error_message):
        """Callback when fetch encounters an error."""
        self._is_fetching = False
        self._parent.fetch_btn.setText("Check for Updates")
        self._parent.fetch_btn.setEnabled(True)
        self._parent._stop_busy_feedback()

        self._parent._show_status_message(
            f"Fetch error: {error_message}", is_error=True
        )
        log.error(f"Fetch error: {error_message}")

    def _start_pull_sequence(self):
        """Start the pull sequence: fetch then pull."""
        self._is_pulling = True
        self._parent.pull_btn.setText("Pulling…")
        self._parent.pull_btn.setEnabled(False)
        self._parent._start_busy_feedback("Pulling updates…")

        # First fetch to get latest remote info
        def _run_fetch():
            ctx = create_action_context(
                self._git_client,
                self._parent._current_repo_root
            )
            return fetch_from_remote(ctx, self._parent._remote_name)

        self._job_runner.run_callable(
            "pull_fetch",
            _run_fetch,
            on_success=self._on_pull_fetch_complete,
            on_error=self._on_pull_error,
        )

    def _on_pull_fetch_complete(self, fetch_result):
        """Callback when fetch part of pull completes."""
        if not fetch_result.ok:
            self._is_pulling = False
            self._parent.pull_btn.setText("Get Updates")
            self._parent.pull_btn.setEnabled(True)
            self._parent._stop_busy_feedback()
            
            self._parent._show_status_message(
                f"Pull failed during fetch: {fetch_result.message}", is_error=True
            )
            return

        # Now run the actual pull
        def _run_pull():
            ctx = create_action_context(
                self._git_client,
                self._parent._current_repo_root
            )
            return pull_from_remote(ctx, self._parent._remote_name)

        self._job_runner.run_callable(
            "pull_merge",
            _run_pull,
            on_success=self._on_pull_complete,
            on_error=self._on_pull_error,
        )

    def _on_pull_complete(self, result):
        """Callback when pull completes successfully."""
        self._is_pulling = False
        self._parent.pull_btn.setText("Get Updates")
        self._parent.pull_btn.setEnabled(True)
        self._parent._stop_busy_feedback()

        if result.ok:
            # Save fetch timestamp
            settings.save_last_fetch_at(
                datetime.now(timezone.utc).isoformat()
            )
            self.display_last_fetch()

            # Refresh status
            self._parent._refresh_status_views(self._parent._current_repo_root)
            self._parent._update_upstream_info(self._parent._current_repo_root)

            # Show success message
            message = result.message or "Pull completed successfully"
            self._parent._show_status_message(message, is_error=False)
            log.info(f"Pull completed: {message}")

            # Show dialog if there were actual changes
            if result.data and result.data.get("had_changes"):
                QtWidgets.QMessageBox.information(
                    self._parent,
                    "Pull Complete",
                    f"✓ Updated from remote\n\n{message}",
                )
        else:
            self._parent._show_status_message(
                f"Pull failed: {result.message}", is_error=True
            )
            log.error(f"Pull failed: {result.message}")

            # Show error dialog
            QtWidgets.QMessageBox.warning(
                self._parent,
                "Pull Failed",
                f"Failed to pull updates:\n\n{result.message}\n\n"
                "Check the log for details.",
            )

    def _on_pull_error(self, error_message):
        """Callback when pull encounters an error."""
        self._is_pulling = False
        self._parent.pull_btn.setText("Get Updates")
        self._parent.pull_btn.setEnabled(True)
        self._parent._stop_busy_feedback()

        self._parent._show_status_message(
            f"Pull error: {error_message}", is_error=True
        )
        log.error(f"Pull error: {error_message}")

        QtWidgets.QMessageBox.critical(
            self._parent,
            "Pull Error",
            f"An error occurred during pull:\n\n{error_message}",
        )
