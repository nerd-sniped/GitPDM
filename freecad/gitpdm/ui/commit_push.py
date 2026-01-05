"""
Commit/Push Handler Module
Sprint 4: Extracted from panel.py to manage commit and push operations.
"""

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

from freecad.gitpdm.core import log
from freecad.gitpdm.ui import dialogs


class CommitPushHandler:
    """
    Handles commit and push operations.

    Manages:
    - Commit workflow (stage, commit)
    - Push workflow (with upstream handling)
    - Combined commit & push sequence
    - Identity error dialogs
    - Behind upstream warnings
    """

    def __init__(self, parent, git_client, job_runner):
        """
        Initialize commit/push handler.

        Args:
            parent: GitPDMDockWidget - parent panel with UI widgets and state
            git_client: GitClient - for git operations
            job_runner: JobRunner - for background operations
        """
        self._parent = parent
        self._git_client = git_client
        self._job_runner = job_runner

        # Operation state
        self._is_committing = False
        self._is_pushing = False
        self._pending_commit_message = ""

    # ========== Public API ==========

    def commit_push_clicked(self):
        """Handle Commit & Push button click (routes to appropriate flow)."""
        if self._parent._workflow_mode == "both":
            self.start_commit_push_sequence()
        elif self._parent._workflow_mode == "commit":
            self.commit_clicked()
        elif self._parent._workflow_mode == "push":
            self.push_clicked()

    def commit_clicked(self):
        """Handle Commit button click."""
        if not self._parent._current_repo_root:
            log.warning("No repository to commit")
            return

        if self._is_committing or self._job_runner.is_busy():
            log.debug("Job running, commit ignored")
            return

        # Prefer message from main editor; fallback to compact field
        message = (
            self._parent.commit_message.toPlainText().strip()
            if hasattr(self._parent, "commit_message")
            else ""
        )
        if not message and hasattr(self._parent, "compact_commit_message"):
            message = self._parent.compact_commit_message.text().strip()
        if not message:
            self._parent._show_status_message("Commit message required", is_error=True)
            return

        if self._parent._behind_count > 0:
            behind_msg = (
                f"You're {self._parent._behind_count} commits behind upstream. "
                "Consider Pull before pushing."
            )
            self._parent._show_status_message(behind_msg, is_error=False)

        self._parent._clear_status_message()
        self._is_committing = True
        self._parent.commit_push_btn.setText("Committing…")
        self._pending_commit_message = message
        self._parent._update_button_states()
        self._parent._start_busy_feedback("Committing…")

        log.info("Starting commit sequence")

        git_cmd = self._git_client._get_git_command()
        args = [git_cmd, "-C", self._parent._current_repo_root, "add", "-A"]

        self._job_runner.run_job(
            "commit_stage",
            args,
            callback=self._on_commit_stage_completed,
        )

    def push_clicked(self):
        """Handle Push button click."""
        if not self._parent._current_repo_root:
            log.warning("No repository to push")
            return

        if self._is_pushing or self._job_runner.is_busy():
            log.debug("Job running, push ignored")
            return

        if self._parent._behind_count > 0:
            should_continue = self._show_push_behind_warning()
            if not should_continue:
                log.info("User cancelled push due to being behind")
                return

        self._parent._clear_status_message()
        self._is_pushing = True
        self._parent.commit_push_btn.setText("Pushing…")
        self._parent._update_button_states()
        self._parent._start_busy_feedback("Pushing…")

        log.info("Starting push")

        git_cmd = self._git_client._get_git_command()

        has_upstream = self._git_client.has_upstream(self._parent._current_repo_root)

        if has_upstream:
            args = [git_cmd, "-C", self._parent._current_repo_root, "push"]
        else:
            args = [
                git_cmd,
                "-C",
                self._parent._current_repo_root,
                "push",
                "-u",
                self._parent._remote_name,
                "HEAD",
            ]

        self._job_runner.run_job(
            "push_main",
            args,
            callback=self._on_push_main_completed,
        )

    def start_commit_push_sequence(self):
        """Start combined commit & push workflow."""
        if not self._parent._current_repo_root:
            log.warning("No repository to commit+push")
            return

        if self._is_committing or self._is_pushing or self._job_runner.is_busy():
            log.debug("Job running, commit+push ignored")
            return

        message = self._parent.commit_message.toPlainText().strip()
        if not message:
            self._parent._show_status_message("Commit message required", is_error=True)
            return

        self._parent._clear_status_message()
        self._is_committing = True
        self._parent.commit_push_btn.setText("Committing…")
        self._pending_commit_message = message
        self._parent._update_button_states()
        self._parent._start_busy_feedback("Committing…")

        log.info("Starting commit & push sequence")

        git_cmd = self._git_client._get_git_command()
        args = [git_cmd, "-C", self._parent._current_repo_root, "add", "-A"]

        self._job_runner.run_job(
            "commit_push_stage",
            args,
            callback=self._on_commit_push_stage_completed,
        )

    def update_commit_push_button_label(self):
        """Update the commit/push button to its default label based on workflow mode."""
        mode = self._parent._workflow_mode
        if mode == "both":
            self._parent.commit_push_btn.setText("Commit and Push")
        elif mode == "commit":
            self._parent.commit_push_btn.setText("Commit")
        elif mode == "push":
            self._parent.commit_push_btn.setText("Push")
        else:
            self._parent.commit_push_btn.setText("Commit and Push")

    def is_busy(self):
        """Check if commit or push operation is in progress."""
        return self._is_committing or self._is_pushing

    # ========== Private Implementation ==========

    def _on_commit_stage_completed(self, job):
        """Callback after staging completes."""
        result = job.get("result", {})
        if not result.get("success"):
            log.warning(f"Stage failed: {result.get('stderr', '')}")
            self._handle_commit_failed("Stage failed")
            return

        log.debug("Stage completed, running commit")

        if not self._parent._current_repo_root:
            self._handle_commit_failed("Repository lost")
            return

        message = self._pending_commit_message
        if not message:
            self._handle_commit_failed("No commit message")
            return

        git_cmd = self._git_client._get_git_command()
        args = [git_cmd, "-C", self._parent._current_repo_root, "commit", "-m", message]

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
        self.update_commit_push_button_label()
        self._pending_commit_message = ""
        self._parent._stop_busy_feedback()

        if not success:
            code = self._git_client._classify_commit_error(stderr)
            if code == "NOTHING_TO_COMMIT":
                self._parent._show_status_message(
                    "No changes to commit", is_error=False
                )
            elif code == "MISSING_IDENTITY":
                self._show_commit_identity_error_dialog()
            else:
                self._parent._show_status_message(
                    f"Commit failed: {stderr[:80]}", is_error=True
                )
            log.warning(f"Commit failed: {code}")
            self._parent._update_button_states()
            return

        log.info("Commit created successfully")
        if hasattr(self._parent, "commit_message"):
            self._parent.commit_message.clear()
        if hasattr(self._parent, "compact_commit_message"):
            self._parent.compact_commit_message.clear()

        if self._parent._current_repo_root:
            branch = self._git_client.current_branch(self._parent._current_repo_root)
            self._parent.branch_label.setText(branch)
            self._parent._refresh_status_views(self._parent._current_repo_root)
            self._parent._update_upstream_info(self._parent._current_repo_root)

        self._parent._show_status_message("Commit created", is_error=False)

        QtCore.QTimer.singleShot(2000, self._parent._clear_status_message)
        self._parent._update_button_states()

    def _handle_commit_failed(self, message):
        """Handle commit failure."""
        self._is_committing = False
        self.update_commit_push_button_label()
        self._parent._show_status_message(message, is_error=True)
        self._parent._stop_busy_feedback()
        self._parent._update_button_states()

    def _show_commit_identity_error_dialog(self):
        """Show error about missing git identity."""
        msg_box = QtWidgets.QMessageBox(self._parent)
        msg_box.setIcon(QtWidgets.QMessageBox.Warning)
        msg_box.setWindowTitle("Git Identity Not Configured")
        msg_box.setText("Git needs your name and email before committing.")
        details = (
            "Configure in GitHub Desktop or run:\n\n"
            'git config --global user.name "Your Name"\n'
            'git config --global user.email "your@email.com"'
        )
        msg_box.setInformativeText(details)
        msg_box.exec()

    def _on_push_main_completed(self, job):
        """Callback when push completes."""
        result = job.get("result", {})
        success = result.get("success", False)
        stderr = result.get("stderr", "")

        self._is_pushing = False
        self.update_commit_push_button_label()

        if not success:
            # Check for upstream mismatch error
            if (
                "upstream branch" in stderr.lower()
                and "does not match" in stderr.lower()
            ):
                # Upstream mismatch - offer to use current branch name
                reply = QtWidgets.QMessageBox.question(
                    self._parent,
                    "Upstream Branch Mismatch",
                    f"The current upstream configuration doesn't match your branch name.\n\n"
                    f"Do you want to push to 'origin/{self._git_client.current_branch(self._parent._current_repo_root)}' "
                    f"and set it as upstream?\n\n"
                    f"This will create a new remote branch with the same name.",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.Yes,
                )
                if reply == QtWidgets.QMessageBox.Yes:
                    # Retry with explicit branch name
                    self._retry_push_with_branch_name()
                    return

            code = self._git_client._classify_push_error(stderr)
            self._show_push_error_dialog(code, stderr)
            log.warning(f"Push failed: {code}")
            self._parent._stop_busy_feedback()
            self._parent._update_button_states()
            return

        log.info("Push completed successfully")

        # Clear any leftover commit message after a successful push
        if hasattr(self._parent, "commit_message"):
            self._parent.commit_message.clear()

        if self._parent._current_repo_root:
            self._parent._update_upstream_info(self._parent._current_repo_root)

        self._parent._show_status_message("Push completed", is_error=False)

        QtCore.QTimer.singleShot(2000, self._parent._clear_status_message)

        self._parent._stop_busy_feedback()

        self._parent._update_button_states()

    def _retry_push_with_branch_name(self):
        """Retry push using current branch name explicitly."""
        if not self._parent._current_repo_root:
            return

        current_branch = self._git_client.current_branch(
            self._parent._current_repo_root
        )
        if not current_branch or current_branch.startswith("("):
            QtWidgets.QMessageBox.warning(
                self._parent, "Cannot Push", "Cannot determine current branch name."
            )
            return

        self._is_pushing = True
        self._parent._start_busy_feedback("Pushing…")

        git_cmd = self._git_client._get_git_command()
        # Use: git push -u origin <branch>:<branch>
        # This explicitly pushes to a branch with the same name
        args = [
            git_cmd,
            "-C",
            self._parent._current_repo_root,
            "push",
            "-u",
            self._parent._remote_name,
            f"{current_branch}:{current_branch}",
        ]

        log.info(f"Retrying push with explicit branch: {current_branch}")

        self._job_runner.run_job(
            "push_retry",
            args,
            callback=self._on_push_main_completed,
        )

    def _show_push_behind_warning(self):
        """Show warning if behind upstream."""
        msg_box = QtWidgets.QMessageBox(self._parent)
        msg_box.setIcon(QtWidgets.QMessageBox.Warning)
        msg_box.setWindowTitle("Behind Upstream")
        msg_box.setText(
            f"You're {self._parent._behind_count} commits behind upstream. "
            "Push may be rejected."
        )
        msg_box.setInformativeText("Consider Pull first to sync with upstream.")
        msg_box.setStandardButtons(
            QtWidgets.QMessageBox.Cancel | QtWidgets.QMessageBox.Ok
        )
        msg_box.setDefaultButton(QtWidgets.QMessageBox.Cancel)
        result = msg_box.exec()
        return result == QtWidgets.QMessageBox.Ok

    def _show_push_error_dialog(self, error_code, stderr):
        """Show error dialog for push failure."""
        dlg = dialogs.PushErrorDialog(error_code, stderr, self._parent)
        dlg.exec()

    # ========== Commit & Push Sequence ==========

    def _on_commit_push_stage_completed(self, job):
        """Callback after staging in commit & push sequence."""
        result = job.get("result", {})
        if not result.get("success"):
            log.warning(f"Stage failed: {result.get('stderr', '')}")
            self._handle_commit_push_failed("Stage failed")
            return

        log.debug("Stage completed, running commit")

        if not self._parent._current_repo_root:
            self._handle_commit_push_failed("Repository lost")
            return

        message = self._pending_commit_message
        if not message:
            self._handle_commit_push_failed("No commit message")
            return

        git_cmd = self._git_client._get_git_command()
        args = [git_cmd, "-C", self._parent._current_repo_root, "commit", "-m", message]

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
                self._parent._show_status_message(
                    "No changes to commit", is_error=False
                )
            elif code == "MISSING_IDENTITY":
                self._show_commit_identity_error_dialog()
            else:
                self._parent._show_status_message(
                    f"Commit failed: {stderr[:80]}", is_error=True
                )
            log.warning(f"Commit failed: {code}")
            self._handle_commit_push_failed("Commit failed, skipping push")
            return

        log.info("Commit succeeded, now pushing")
        self._parent.commit_push_btn.setText("Pushing…")
        self._is_committing = False
        self._is_pushing = True
        self._parent._show_status_message("Pushing…", is_error=False)

        git_cmd = self._git_client._get_git_command()

        has_upstream = self._git_client.has_upstream(self._parent._current_repo_root)

        if has_upstream:
            args = [git_cmd, "-C", self._parent._current_repo_root, "push"]
        else:
            args = [
                git_cmd,
                "-C",
                self._parent._current_repo_root,
                "push",
                "-u",
                self._parent._remote_name,
                "HEAD",
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
        self.update_commit_push_button_label()
        self._parent._stop_busy_feedback()

        if not success:
            code = self._git_client._classify_push_error(stderr)
            self._show_push_error_dialog(code, stderr)
            log.warning(f"Push failed: {code}")
            self._parent._update_button_states()
            return

        log.info("Commit & push completed successfully")

        if hasattr(self._parent, "commit_message"):
            self._parent.commit_message.clear()
        if hasattr(self._parent, "compact_commit_message"):
            self._parent.compact_commit_message.clear()

        if self._parent._current_repo_root:
            branch = self._git_client.current_branch(self._parent._current_repo_root)
            self._parent.branch_label.setText(branch)

            self._parent._refresh_status_views(self._parent._current_repo_root)

            self._parent._update_upstream_info(self._parent._current_repo_root)

        self._parent._show_status_message("Commit & push completed", is_error=False)

        QtCore.QTimer.singleShot(2000, self._parent._clear_status_message)

        self._parent._update_button_states()

    def _handle_commit_push_failed(self, message):
        """Handle commit & push failure."""
        self._is_committing = False
        self._is_pushing = False
        self._parent.commit_push_btn.setText("Commit & Push")
        self._pending_commit_message = ""
        self._parent._stop_busy_feedback()
        self._parent._show_status_message(message, is_error=True)
        self._parent._update_button_states()
