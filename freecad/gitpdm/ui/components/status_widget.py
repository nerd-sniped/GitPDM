"""
Status Widget Component
Sprint 5 Phase 1: Displays git status, branch info, and upstream tracking

Extracted from monolithic panel.py for better maintainability.
Handles: Git availability check, status display, branch info, upstream tracking.
"""

# Qt compatibility layer
from PySide6 import QtCore, QtGui, QtWidgets

from freecad.gitpdm.ui.components.base_widget import BaseWidget
from freecad.gitpdm.core import log


class StatusWidget(BaseWidget):
    """
    Widget for displaying repository status and branch information.
    
    Shows:
    - Git availability status
    - Current branch and working tree status
    - Upstream tracking (ahead/behind counts)
    - Last fetch time
    - Status messages (errors/info)
    
    Signals:
        status_updated: Emitted when status info changes
        refresh_requested: Emitted when user wants to refresh
        git_status_changed: Emitted when git availability changes
    """
    
    status_updated = QtCore.Signal(dict)  # Status info dict
    refresh_requested = QtCore.Signal()
    git_status_changed = QtCore.Signal(bool)  # True if git is available
    
    def __init__(self, parent=None, git_client=None, job_runner=None):
        """
        Initialize status widget.
        
        Args:
            parent: Parent widget (main panel)
            git_client: GitClient instance
            job_runner: JobRunner instance
        """
        super().__init__(parent, git_client, job_runner)
        
        # State
        self._current_repo_root = None
        self._upstream_ref = None
        self._ahead_count = 0
        self._behind_count = 0
        self._git_available = False
        self._is_updating_upstream = False
        
        # Build UI
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        self._build_git_check_section(layout)
        self._build_status_section(layout)
        
        self.setLayout(layout)
        
        log.debug("StatusWidget initialized")
    
    # =========================================================================
    # UI Construction
    # =========================================================================
    
    def _build_git_check_section(self, layout):
        """Build the Git availability check section."""
        group = self.create_group_box("Git")
        group_layout = QtWidgets.QVBoxLayout()
        group_layout.setContentsMargins(6, 4, 6, 4)
        group_layout.setSpacing(4)
        group.setLayout(group_layout)
        
        # Status row
        status_layout = QtWidgets.QHBoxLayout()
        status_layout.setSpacing(4)
        
        status_layout.addWidget(QtWidgets.QLabel("Status:"))
        
        self.git_status_label = self.create_strong_label("Checking...", "gray")
        status_layout.addWidget(self.git_status_label)
        status_layout.addStretch()
        
        group_layout.addLayout(status_layout)
        
        layout.addWidget(group)
        self._group_git_check = group
    
    def _build_status_section(self, layout):
        """Build the main status display section."""
        group = self.create_group_box("Status")
        group_layout = QtWidgets.QVBoxLayout()
        group_layout.setContentsMargins(6, 4, 6, 4)
        group_layout.setSpacing(4)
        group.setLayout(group_layout)
        
        # Status grid
        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setSpacing(4)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(2, 1)
        
        def add_field(row, col, label_text, value_widget):
            """Helper to add a field to the grid."""
            label = self.create_meta_label(label_text)
            grid_layout.addWidget(label, row * 2, col)
            grid_layout.addWidget(value_widget, row * 2 + 1, col)
        
        # Create value labels
        self.working_tree_label = self.create_strong_label("—", "gray")
        self.working_tree_label.setToolTip(
            "Number of files you've modified\n"
            "(Git term: 'working tree' - your local changes)"
        )
        
        self.ahead_behind_label = self.create_strong_label("—", "gray")
        self.ahead_behind_label.setToolTip(
            "How many changes you have to share vs. get from your team\n"
            "(Git term: 'ahead/behind' - commits to push/pull)"
        )
        
        self.branch_label = self.create_strong_label("—", "gray")
        self.branch_label.setToolTip(
            "Which version of the project you're currently working on\n"
            "(Git term: 'branch' - independent line of development)"
        )
        
        self.upstream_label = self.create_meta_label("—", "gray")
        self.upstream_label.setToolTip(
            "The GitHub version you're syncing with\n"
            "(Git term: 'upstream' or 'remote tracking branch')"
        )
        
        self.last_fetch_label = self.create_meta_label("—", "gray")
        self.last_fetch_label.setToolTip(
            "When you last checked for updates from your team\n"
            "(Git term: 'last fetch time')"
        )
        
        add_field(0, 0, "Your Changes", self.working_tree_label)
        add_field(0, 1, "Sync Status", self.ahead_behind_label)
        add_field(0, 2, "Work Version", self.branch_label)
        add_field(1, 0, "GitHub Version", self.upstream_label)
        add_field(1, 1, "Last checked", self.last_fetch_label)
        
        group_layout.addLayout(grid_layout)
        
        # Status message area
        self.status_message_label = QtWidgets.QLabel("")
        self.status_message_label.setWordWrap(True)
        self.status_message_label.setStyleSheet("color: red; font-size: 10px;")
        self.status_message_label.hide()
        group_layout.addWidget(self.status_message_label)
        
        layout.addWidget(group)
        self._group_status = group
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    def check_git_available(self):
        """Check if Git is available and update status display."""
        if not self._git_client:
            self._set_git_status(False, "No git client")
            return
        
        self.set_busy_state(True, "Checking git...")
        
        def _check():
            return self._git_client.is_git_available()
        
        def _on_complete(available):
            self.set_busy_state(False)
            self._set_git_status(available, "Available" if available else "Not found")
            self.git_status_changed.emit(available)
        
        self.run_async("check_git", _check, on_success=_on_complete)
    
    def update_working_tree_status(self, file_count: int):
        """
        Update working tree status display.
        
        Args:
            file_count: Number of modified files
        """
        if file_count == 0:
            self.working_tree_label.setText("Clean")
            self._set_strong_label_color(self.working_tree_label, "green")
        else:
            self.working_tree_label.setText(f"{file_count} file{'s' if file_count != 1 else ''}")
            self._set_strong_label_color(self.working_tree_label, "orange")
    
    def update_branch_info(self, branch_name: str):
        """
        Update current branch display.
        
        Args:
            branch_name: Name of current branch
        """
        if branch_name:
            self.branch_label.setText(branch_name)
            self._set_strong_label_color(self.branch_label, "#4db6ac")
        else:
            self.branch_label.setText("—")
            self._set_strong_label_color(self.branch_label, "gray")
    
    def update_upstream_info(self, repo_root: str):
        """
        Update upstream tracking information asynchronously.
        
        Args:
            repo_root: Path to repository root
        """
        if not self._git_client or self._is_updating_upstream:
            return
        
        self._is_updating_upstream = True
        self._current_repo_root = repo_root
        
        def _get_upstream_info():
            """Background task to get upstream info."""
            upstream_ref = self._git_client.get_upstream_ref(repo_root)
            
            ab_result = {"ok": False, "ahead": 0, "behind": 0, "error": None}
            if upstream_ref:
                ab_result = self._git_client.get_ahead_behind_with_upstream(repo_root)
            
            return {"upstream_ref": upstream_ref, "ab_result": ab_result}
        
        self.run_async(
            "update_upstream",
            _get_upstream_info,
            on_success=self._on_upstream_complete,
            on_error=self._on_upstream_error
        )
    
    def update_last_fetch_time(self, last_fetch_time: str):
        """
        Update last fetch time display.
        
        Args:
            last_fetch_time: Human-readable last fetch time
        """
        if last_fetch_time:
            self.last_fetch_label.setText(last_fetch_time)
            self._set_meta_label_color(self.last_fetch_label, "gray")
        else:
            self.last_fetch_label.setText("Never")
            self._set_meta_label_color(self.last_fetch_label, "gray")
    
    def show_status_message(self, message: str, is_error: bool = True):
        """
        Show a status message.
        
        Args:
            message: Message to display
            is_error: True for error (red), False for info (blue)
        """
        color = "red" if is_error else "#1976d2"
        self.status_message_label.setStyleSheet(f"color: {color}; font-size: 10px;")
        self.status_message_label.setText(message)
        self.status_message_label.show()
    
    def clear_status_message(self):
        """Clear the status message."""
        self.status_message_label.hide()
        self.status_message_label.setText("")
    
    def get_ahead_behind_counts(self):
        """
        Get current ahead/behind counts.
        
        Returns:
            tuple: (ahead_count, behind_count)
        """
        return (self._ahead_count, self._behind_count)
    
    def get_upstream_ref(self):
        """
        Get current upstream reference.
        
        Returns:
            str: Upstream ref or None
        """
        return self._upstream_ref
    
    # =========================================================================
    # BaseWidget Overrides
    # =========================================================================
    
    def update_for_repository(self, repo_root: str):
        """Update status for new repository."""
        self._current_repo_root = repo_root
        
        if repo_root:
            self.update_upstream_info(repo_root)
        else:
            self._reset_status()
    
    def refresh(self):
        """Refresh status information."""
        if self._current_repo_root:
            self.update_upstream_info(self._current_repo_root)
            self.refresh_requested.emit()
    
    # =========================================================================
    # Internal Helpers
    # =========================================================================
    
    def _set_git_status(self, available: bool, message: str):
        """Set git availability status."""
        self._git_available = available
        
        if available:
            self.git_status_label.setText(message)
            self._set_strong_label_color(self.git_status_label, "green")
        else:
            self.git_status_label.setText(message)
            self._set_strong_label_color(self.git_status_label, "red")
    
    def _on_upstream_complete(self, result):
        """Callback when upstream update completes."""
        self._is_updating_upstream = False
        
        try:
            upstream_ref = result.get("upstream_ref")
            ab_result = result.get("ab_result", {})
            
            # Update upstream display
            if not upstream_ref:
                self.upstream_label.setText("(not set)")
                self._set_meta_label_color(self.upstream_label, "orange")
                self.ahead_behind_label.setText("(unknown)")
                self._set_strong_label_color(self.ahead_behind_label, "gray")
                self._upstream_ref = None
                self.status_updated.emit({"upstream": None, "ahead": 0, "behind": 0})
                return
            
            self.upstream_label.setText(upstream_ref)
            self._set_meta_label_color(self.upstream_label, "#4db6ac")
            self._upstream_ref = upstream_ref
            
            # Update ahead/behind display
            if ab_result.get("ok"):
                ahead = ab_result.get("ahead", 0)
                behind = ab_result.get("behind", 0)
                
                self._ahead_count = ahead
                self._behind_count = behind
                
                if ahead == 0 and behind == 0:
                    ab_text = "Up to date"
                    color = "green"
                elif ahead > 0 and behind > 0:
                    ab_text = f"{ahead} to share | {behind} to get"
                    color = "orange"
                elif ahead > 0:
                    ab_text = f"{ahead} to share ↑"
                    color = "#4db6ac"
                else:
                    ab_text = f"{behind} to get ↓"
                    color = "orange"
                
                self.ahead_behind_label.setText(ab_text)
                self._set_strong_label_color(self.ahead_behind_label, color)
                
                self.status_updated.emit({
                    "upstream": upstream_ref,
                    "ahead": ahead,
                    "behind": behind
                })
            else:
                self.ahead_behind_label.setText("(error)")
                self._set_strong_label_color(self.ahead_behind_label, "red")
                log.debug(f"Ahead/behind error: {ab_result.get('error')}")
                
        except Exception as e:
            log.error(f"Error processing upstream result: {e}")
            self._is_updating_upstream = False
    
    def _on_upstream_error(self, error):
        """Callback when upstream update fails."""
        self._is_updating_upstream = False
        log.warning(f"Upstream update error: {error}")
        self.ahead_behind_label.setText("(error)")
        self._set_strong_label_color(self.ahead_behind_label, "red")
    
    def _reset_status(self):
        """Reset all status displays to default."""
        self.working_tree_label.setText("—")
        self._set_strong_label_color(self.working_tree_label, "gray")
        
        self.ahead_behind_label.setText("—")
        self._set_strong_label_color(self.ahead_behind_label, "gray")
        
        self.branch_label.setText("—")
        self._set_strong_label_color(self.branch_label, "gray")
        
        self.upstream_label.setText("—")
        self._set_meta_label_color(self.upstream_label, "gray")
        
        self.last_fetch_label.setText("—")
        self._set_meta_label_color(self.last_fetch_label, "gray")
        
        self._upstream_ref = None
        self._ahead_count = 0
        self._behind_count = 0
    
    def _set_strong_label_color(self, label: QtWidgets.QLabel, color: str):
        """Update strong label color."""
        label.setStyleSheet(
            f"font-weight: bold; color: {color}; font-size: {self._strong_font_size}px;"
        )
    
    def _set_meta_label_color(self, label: QtWidgets.QLabel, color: str):
        """Update meta label color."""
        label.setStyleSheet(f"color: {color}; font-size: {self._meta_font_size}px;")
