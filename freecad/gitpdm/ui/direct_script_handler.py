"""
Direct Script Handler - Simple Git Operations

Executes PowerShell/Bash scripts directly for Git operations.
Clean, simple architecture: Button → Handler → Script → Git

For adding new git operations, see BUTTON_API.md
"""

try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide6 import QtWidgets

from freecad.gitpdm.core.script_executor import (
    script_commit,
    script_push,
    script_fetch,
    script_pull,
    script_validate,
    execute_script
)


class DirectScriptHandler:
    """
    Handles button clicks for Git operations by executing scripts directly.
    
    Architecture:
        Button Click → Handler Method (2-5 lines) → Script Execution → Git Command
    """
    
    def __init__(self, panel):
        """Initialize handler with reference to parent panel."""
        self.panel = panel
    
    def commit_clicked(self):
        """Handle commit button click."""
        msg = self.panel.commit_message.toPlainText().strip()
        if not msg:
            return
        
        result = script_commit(self.panel._current_repo_root, msg, stage_all=True)
        self._show_result(result, "Commit")
    
    def push_clicked(self):
        """Handle push button click."""
        result = script_push(self.panel._current_repo_root)
        self._show_result(result, "Push")
    
    def fetch_clicked(self):
        """Handle fetch button click."""
        result = script_fetch(self.panel._current_repo_root)
        self._show_result(result, "Fetch")
    
    def pull_clicked(self):
        """Handle pull button click."""
        result = script_pull(self.panel._current_repo_root)
        self._show_result(result, "Pull")
    
    def validate_clicked(self):
        """Handle validate button click."""
        result = script_validate(self.panel._current_repo_root)
        self._show_result(result, "Validate")
    
    def commit_and_push_clicked(self):
        """Handle combined commit and push button click."""
        msg = self.panel.commit_message.toPlainText().strip()
        if not msg:
            return
        
        # Commit first
        result = script_commit(self.panel._current_repo_root, msg, stage_all=True)
        if not result.success:
            self._show_result(result, "Commit")
            return
        
        # Then push
        result = script_push(self.panel._current_repo_root)
        self._show_result(result, "Commit & Push")
    
    def add_remote_clicked(self):
        """Handle add remote button click - prompts for URL."""
        url, ok = QtWidgets.QInputDialog.getText(
            self.panel, "Add Remote", "Enter remote URL:"
        )
        if not ok or not url:
            return
        
        result = execute_script(
            "git_add_remote.ps1",
            repo_path=self.panel._current_repo_root,
            name="origin",
            url=url
        )
        self._show_result(result, "Add Remote")
    
    # ========================================================================
    # Panel Compatibility Methods
    # ========================================================================
    
    def validate_repo_path(self, path):
        """Validate repository path - returns True if valid."""
        result = script_validate(path)
        return result.success
    
    def refresh_clicked(self):
        """Refresh status - delegates to panel."""
        if hasattr(self.panel, '_refresh_git_status'):
            self.panel._refresh_git_status()
    
    def connect_remote_clicked(self):
        """Connect remote - same as add_remote."""
        self.add_remote_clicked()
    
    def is_busy(self):
        """Check if busy - always False (scripts are synchronous)."""
        return False
    
    # Stub methods for panel compatibility
    def update_commit_push_button_label(self):
        """Update button label (no-op)."""
        pass
    
    def handle_fetch_result(self, job):
        """Handle fetch result (no-op)."""
        pass
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _show_result(self, result, operation: str):
        """Display operation result in a message box."""
        if result.success:
            QtWidgets.QMessageBox.information(
                self.panel,
                f"{operation} Success",
                result.output or f"{operation} completed successfully"
            )
        else:
            QtWidgets.QMessageBox.critical(
                self.panel,
                f"{operation} Failed",
                result.error or f"{operation} failed"
            )

