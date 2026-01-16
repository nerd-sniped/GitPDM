"""
Ultra-Minimal Direct Script Handler

Example of wiring buttons DIRECTLY to PowerShell scripts with minimal Python.

Button click → Script execution → Show result (3-5 lines total)
No action layer, no backend abstraction, no business logic.

This is the tightest possible loop.
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
    Ultra-minimal handler that executes scripts directly.
    
    Each button handler is 3-5 lines:
    1. Get inputs
    2. Call script
    3. Show result
    """
    
    def __init__(self, panel):
        self.panel = panel
    
    def commit_clicked(self):
        """Commit button - 4 lines."""
        msg = self.panel.commit_message.toPlainText().strip()
        if not msg:
            return
        
        result = script_commit(self.panel._current_repo_root, msg, stage_all=True)
        self._show_result(result, "Commit")
    
    def push_clicked(self):
        """Push button - 2 lines."""
        result = script_push(self.panel._current_repo_root)
        self._show_result(result, "Push")
    
    def fetch_clicked(self):
        """Fetch button - 2 lines."""
        result = script_fetch(self.panel._current_repo_root)
        self._show_result(result, "Fetch")
    
    def pull_clicked(self):
        """Pull button - 2 lines."""
        result = script_pull(self.panel._current_repo_root)
        self._show_result(result, "Pull")
    
    def validate_clicked(self):
        """Validate button - 2 lines."""
        result = script_validate(self.panel._current_repo_root)
        self._show_result(result, "Validate")
    
    def commit_and_push_clicked(self):
        """Combined button - 5 lines."""
        msg = self.panel.commit_message.toPlainText().strip()
        if not msg:
            return
        
        # Commit
        result = script_commit(self.panel._current_repo_root, msg, stage_all=True)
        if not result.success:
            self._show_result(result, "Commit")
            return
        
        # Push
        result = script_push(self.panel._current_repo_root)
        self._show_result(result, "Commit & Push")
    
    def add_remote_clicked(self):
        """Add remote - 5 lines (needs dialog for URL)."""
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
    # Additional Methods for Compatibility
    # ========================================================================
    
    def validate_repo_path(self, path):
        """Validate repository path - minimal implementation."""
        result = script_validate(path)
        # Silently validates - panel will handle UI updates
        return result.success
    
    def fetch_branch_and_status(self, repo_root):
        """Fetch branch and status - triggers panel refresh."""
        # Panel will handle status updates via its own mechanisms
        if hasattr(self.panel, '_refresh_git_status'):
            self.panel._refresh_git_status()
    
    def refresh_clicked(self):
        """Refresh button - triggers panel refresh."""
        if hasattr(self.panel, '_refresh_git_status'):
            self.panel._refresh_git_status()
    
    def create_repo_clicked(self):
        """Create repo button - shows not implemented message."""
        QtWidgets.QMessageBox.information(
            self.panel,
            "Create Repository",
            "Repository creation wizard not yet implemented in minimal mode."
        )
    
    def connect_remote_clicked(self):
        """Connect remote button - delegates to add_remote."""
        self.add_remote_clicked()
    
    def is_busy(self):
        """Check if handler is busy - always False for synchronous scripts."""
        return False
    
    def update_commit_push_button_label(self):
        """Update button label - no-op for minimal mode."""
        pass
    
    def handle_fetch_result(self, job):
        """Handle fetch result - no-op for minimal mode."""
        pass
    
    def _set_freecad_working_directory(self, directory):
        """Set FreeCAD working directory - delegates to panel."""
        if hasattr(self.panel, '_set_freecad_working_directory'):
            self.panel._set_freecad_working_directory(directory)
    
    def _show_result(self, result, operation: str):
        """Show script result - 1 helper method."""
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


# ============================================================================
# EXAMPLE: Wiring buttons to scripts in panel.py
# ============================================================================

"""
# In panel.py __init__:

from freecad.gitpdm.ui.direct_script_handler import DirectScriptHandler

self._script_handler = DirectScriptHandler(self)


# Wire buttons (1 line each):

self.commit_btn.clicked.connect(self._script_handler.commit_clicked)
self.push_btn.clicked.connect(self._script_handler.push_clicked)
self.fetch_btn.clicked.connect(self._script_handler.fetch_clicked)
self.pull_btn.clicked.connect(self._script_handler.pull_clicked)
self.commit_push_btn.clicked.connect(self._script_handler.commit_and_push_clicked)


# Total per button:
# - 1 line to wire button
# - 2-5 lines in handler method
# - 1 line to execute script
# = 4-7 lines total from button to script execution
"""


# ============================================================================
# COMPARISON: Action Layer vs Direct Scripts
# ============================================================================

"""
ACTION LAYER APPROACH (current):
==================================
Button Click (panel.py - 1 line)
    ↓
Action Handler (action_commit_push.py - 15-20 lines)
    ↓
Action Function (actions/commit_push.py - 25-30 lines)
    ↓
Backend (script_backend.py - 10 lines)
    ↓
Script (git_commit.ps1 - 15 lines)
    ↓
Git Command

Total: ~60-75 lines of Python before script


DIRECT SCRIPT APPROACH (this):
===============================
Button Click (panel.py - 1 line)
    ↓
Script Handler (direct_script_handler.py - 3-5 lines)
    ↓
Script Executor (script_executor.py - 1 function call)
    ↓
Script (git_commit.ps1 - 15 lines)
    ↓
Git Command

Total: ~5-7 lines of Python before script


REDUCTION: 60-75 lines → 5-7 lines = 90% less Python code
"""
