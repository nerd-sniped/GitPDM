"""
Action-based Commit/Push Handler
Phase 2: Clean handlers using the actions layer
"""

from PySide6 import QtCore, QtWidgets
from freecad.gitpdm.core import log
from freecad.gitpdm.actions import (
    create_action_context,
    commit_changes,
    push_changes,
)


class ActionCommitPushHandler:
    """
    Simplified commit/push handler using actions layer.
    
    Much simpler than the old CommitPushHandler - all git logic
    is in actions, this just handles UI state and async execution.
    """

    def __init__(self, parent, git_client, job_runner):
        """
        Initialize action-based handler.

        Args:
            parent: GitPDMDockWidget
            git_client: GitClient (for creating action context)
            job_runner: JobRunner (for async operations)
        """
        self._parent = parent
        self._git_client = git_client
        self._job_runner = job_runner
        
        # Operation state
        self._is_committing = False
        self._is_pushing = False
        self._pending_message = ""
    
    def is_busy(self):
        """Check if handler is busy with an operation."""
        return self._is_committing or self._is_pushing
    
    def commit_clicked(self):
        """
        Handle Commit button click.
        
        Uses actions layer - much simpler than old implementation!
        """
        # Check if busy
        if self.is_busy() or self._job_runner.is_busy():
            log.debug("Job running, commit ignored")
            return
        
        # Get repo root
        repo_root = self._parent._current_repo_root
        if not repo_root:
            self._parent._show_status_message("No repository selected", is_error=True)
            return
        
        # Get commit message
        message = self._get_commit_message()
        if not message:
            self._parent._show_status_message("Commit message required", is_error=True)
            return
        
        # Check for lock violations (if lock handler available)
        if hasattr(self._parent, '_lock_handler'):
            has_violations, error_msg, locked_files = self._parent._lock_handler.check_lock_violations()
            if has_violations:
                log.warning(f"Commit blocked: {len(locked_files)} files locked by others")
                QtWidgets.QMessageBox.critical(
                    self._parent,
                    "🔒 Files Locked by Others",
                    error_msg
                )
                return
        
        # Warn if behind
        if self._parent._behind_count > 0:
            msg = f"You're {self._parent._behind_count} commits behind. Consider Pull first."
            self._parent._show_status_message(msg, is_error=False)
        
        # Start commit in background
        self._start_commit_async(repo_root, message)
    
    def _get_commit_message(self):
        """Get commit message from UI fields."""
        # Try main editor first
        if hasattr(self._parent, "commit_message"):
            message = self._parent.commit_message.toPlainText().strip()
            if message:
                return message
        
        # Try compact field
        if hasattr(self._parent, "compact_commit_message"):
            message = self._parent.compact_commit_message.text().strip()
            if message:
                return message
        
        return ""
    
    def _start_commit_async(self, repo_root, message):
        """Run commit action in background."""
        self._is_committing = True
        self._pending_message = message
        self._update_ui_state("Committing…")
        
        def _do_commit():
            """Worker function - runs in background thread."""
            # Create action context
            ctx = create_action_context(
                git_client=self._git_client,
                repo_root=repo_root
            )
            
            # Run action (synchronous, but in worker thread)
            return commit_changes(ctx, message, stage_all=True)
        
        def _on_success(result):
            """Success callback - runs on UI thread."""
            self._is_committing = False
            
            if result.ok:
                log.info(f"Commit successful: {message}")
                self._parent._show_status_message(result.message, is_error=False)
                
                # Clear commit message
                self._clear_commit_message()
                
                # Refresh status
                self._parent._refresh_status_views(repo_root)
            else:
                # Handle specific errors
                if result.error_code == "nothing_to_commit":
                    self._parent._show_status_message("No changes to commit", is_error=False)
                else:
                    self._parent._show_status_message(
                        f"Commit failed: {result.message}",
                        is_error=True
                    )
            
            self._update_ui_state()
        
        def _on_error(error):
            """Error callback - runs on UI thread."""
            self._is_committing = False
            log.error(f"Commit error: {error}")
            self._parent._show_status_message(f"Commit error: {error}", is_error=True)
            self._update_ui_state()
        
        # Run async
        self._job_runner.run_callable(
            "commit_action",
            _do_commit,
            on_success=_on_success,
            on_error=_on_error
        )
    
    def push_clicked(self):
        """
        Handle Push button click.
        
        Uses actions layer - simpler than old implementation!
        """
        # Check if busy
        if self.is_busy() or self._job_runner.is_busy():
            log.debug("Job running, push ignored")
            return
        
        # Get repo root
        repo_root = self._parent._current_repo_root
        if not repo_root:
            self._parent._show_status_message("No repository selected", is_error=True)
            return
        
        # Warn if behind
        if self._parent._behind_count > 0:
            choice = QtWidgets.QMessageBox.question(
                self._parent,
                "Behind Remote",
                f"You're {self._parent._behind_count} commits behind the remote.\n\n"
                "Pushing may cause conflicts. Pull first?\n\n"
                "Push anyway?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            if choice != QtWidgets.QMessageBox.Yes:
                log.info("User cancelled push due to being behind")
                return
        
        # Start push in background
        self._start_push_async(repo_root)
    
    def _start_push_async(self, repo_root):
        """Run push action in background."""
        self._is_pushing = True
        self._update_ui_state("Pushing…")
        
        def _do_push():
            """Worker function - runs in background thread."""
            ctx = create_action_context(
                git_client=self._git_client,
                repo_root=repo_root
            )
            return push_changes(ctx)
        
        def _on_success(result):
            """Success callback - runs on UI thread."""
            self._is_pushing = False
            
            if result.ok:
                log.info(f"Push successful")
                self._parent._show_status_message(result.message, is_error=False)
                
                # Refresh status
                self._parent._refresh_status_views(repo_root)
            else:
                # Handle specific errors
                if result.error_code == "no_remote":
                    choice = QtWidgets.QMessageBox.question(
                        self._parent,
                        "No Remote",
                        "No remote repository configured.\n\n"
                        "Would you like to add a remote now?",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                    )
                    if choice == QtWidgets.QMessageBox.Yes:
                        self._parent._start_connect_remote_flow()
                else:
                    self._parent._show_status_message(
                        f"Push failed: {result.message}",
                        is_error=True
                    )
            
            self._update_ui_state()
        
        def _on_error(error):
            """Error callback - runs on UI thread."""
            self._is_pushing = False
            log.error(f"Push error: {error}")
            self._parent._show_status_message(f"Push error: {error}", is_error=True)
            self._update_ui_state()
        
        # Run async
        self._job_runner.run_callable(
            "push_action",
            _do_push,
            on_success=_on_success,
            on_error=_on_error
        )
    
    def commit_push_clicked(self):
        """
        Handle combined Commit+Push button click.
        
        Chains commit and push actions.
        """
        # Check if busy
        if self.is_busy() or self._job_runner.is_busy():
            log.debug("Job running, commit+push ignored")
            return
        
        # Get repo root
        repo_root = self._parent._current_repo_root
        if not repo_root:
            self._parent._show_status_message("No repository selected", is_error=True)
            return
        
        # Get commit message
        message = self._get_commit_message()
        if not message:
            self._parent._show_status_message("Commit message required", is_error=True)
            return
        
        # Check locks (same as commit)
        if hasattr(self._parent, '_lock_handler'):
            has_violations, error_msg, locked_files = self._parent._lock_handler.check_lock_violations()
            if has_violations:
                QtWidgets.QMessageBox.critical(
                    self._parent,
                    "🔒 Files Locked by Others",
                    error_msg
                )
                return
        
        # Warn if behind
        if self._parent._behind_count > 0:
            choice = QtWidgets.QMessageBox.question(
                self._parent,
                "Behind Remote",
                f"You're {self._parent._behind_count} commits behind.\n\n"
                "Continue with commit and push?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            if choice != QtWidgets.QMessageBox.Yes:
                return
        
        # Chain commit → push
        self._start_commit_push_async(repo_root, message)
    
    def _start_commit_push_async(self, repo_root, message):
        """Run commit+push sequence in background."""
        self._is_committing = True
        self._is_pushing = True
        self._pending_message = message
        self._update_ui_state("Committing…")
        
        def _do_commit_push():
            """Worker function - commit then push."""
            ctx = create_action_context(
                git_client=self._git_client,
                repo_root=repo_root
            )
            
            # Step 1: Commit
            commit_result = commit_changes(ctx, message, stage_all=True)
            if not commit_result.ok:
                return commit_result
            
            # Step 2: Push
            return push_changes(ctx)
        
        def _on_success(result):
            """Success callback."""
            self._is_committing = False
            self._is_pushing = False
            
            if result.ok:
                log.info("Commit+push successful")
                self._parent._show_status_message(
                    "Committed and pushed successfully",
                    is_error=False
                )
                self._clear_commit_message()
                self._parent._refresh_status_views(repo_root)
            else:
                self._parent._show_status_message(
                    f"Failed: {result.message}",
                    is_error=True
                )
            
            self._update_ui_state()
        
        def _on_error(error):
            """Error callback."""
            self._is_committing = False
            self._is_pushing = False
            log.error(f"Commit+push error: {error}")
            self._parent._show_status_message(f"Error: {error}", is_error=True)
            self._update_ui_state()
        
        # Run async
        self._job_runner.run_callable(
            "commit_push_action",
            _do_commit_push,
            on_success=_on_success,
            on_error=_on_error
        )
    
    def _clear_commit_message(self):
        """Clear commit message fields."""
        if hasattr(self._parent, "commit_message"):
            try:
                self._parent.commit_message.blockSignals(True)
                self._parent.commit_message.setPlainText("")
                self._parent.commit_message.blockSignals(False)
            except Exception:
                pass
        
        if hasattr(self._parent, "compact_commit_message"):
            try:
                self._parent.compact_commit_message.clear()
            except Exception:
                pass
    
    def _update_ui_state(self, label=None):
        """Update UI button states and labels."""
        # Update button label
        if hasattr(self._parent, "commit_push_btn"):
            if label:
                self._parent.commit_push_btn.setText(label)
            else:
                self.update_commit_push_button_label()
        
        # Update button states
        if hasattr(self._parent, "_update_button_states"):
            self._parent._update_button_states()
        
        # Update busy feedback
        if label:
            if hasattr(self._parent, "_start_busy_feedback"):
                self._parent._start_busy_feedback(label)
        else:
            if hasattr(self._parent, "_stop_busy_feedback"):
                self._parent._stop_busy_feedback()
    
    def update_commit_push_button_label(self):
        """Update the commit/push button label based on state."""
        if not hasattr(self._parent, "commit_push_btn"):
            return
        
        if self._is_committing:
            self._parent.commit_push_btn.setText("Committing…")
        elif self._is_pushing:
            self._parent.commit_push_btn.setText("Pushing…")
        else:
            # Default label
            ahead = self._parent._ahead_count if hasattr(self._parent, "_ahead_count") else 0
            if ahead > 0:
                self._parent.commit_push_btn.setText(f"Commit & Push ({ahead})")
            else:
                self._parent.commit_push_btn.setText("Commit & Push")
