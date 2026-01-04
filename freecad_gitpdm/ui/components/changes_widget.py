# -*- coding: utf-8 -*-
"""
Changes Widget Component
Sprint 5 Phase 1: File changes list and staging

Extracted from monolithic panel.py for better maintainability.
Handles: Display of changed files, stage all checkbox, file status formatting.
"""

# Qt compatibility layer
try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets

from freecad_gitpdm.ui.components.base_widget import BaseWidget
from freecad_gitpdm.core import log


class ChangesWidget(BaseWidget):
    """
    Widget for displaying and managing file changes.
    
    Shows:
    - List of changed files with status icons
    - Stage all checkbox
    - Info label explaining changes
    
    Signals:
        stage_all_changed: Emitted when stage all checkbox changes
        files_selected: Emitted when user selects files
    """
    
    stage_all_changed = QtCore.Signal(bool)  # New state
    files_selected = QtCore.Signal(list)  # Selected file paths
    
    def __init__(self, parent=None, git_client=None, job_runner=None):
        """
        Initialize changes widget.
        
        Args:
            parent: Parent widget (main panel)
            git_client: GitClient instance
            job_runner: JobRunner instance
        """
        super().__init__(parent, git_client, job_runner)
        
        # State
        self._file_statuses = []
        self._stage_all = True
        
        # Build UI
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        self._build_ui(layout)
        self.setLayout(layout)
        
        log.debug("ChangesWidget initialized")
    
    # =========================================================================
    # UI Construction
    # =========================================================================
    
    def _build_ui(self, layout):
        """Build the changes list UI."""
        group = self.create_group_box("Changes")
        group_layout = QtWidgets.QVBoxLayout()
        group_layout.setContentsMargins(6, 4, 6, 4)
        group_layout.setSpacing(4)
        group.setLayout(group_layout)
        
        info_label = QtWidgets.QLabel(
            "These files have been modified since your last save checkpoint."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        info_label.setToolTip(
            "Files that you've changed and haven't saved as a version yet\n"
            "(Git term: 'working tree' or 'unstaged changes' - modified but not committed)"
        )
        group_layout.addWidget(info_label)
        
        self.changes_list = QtWidgets.QListWidget()
        self.changes_list.setMaximumHeight(50)
        self.changes_list.setEnabled(False)
        self.changes_list.itemSelectionChanged.connect(self._on_selection_changed)
        group_layout.addWidget(self.changes_list)
        
        stage_layout = QtWidgets.QHBoxLayout()
        stage_layout.setSpacing(4)
        
        self.stage_all_checkbox = QtWidgets.QCheckBox("Include all changed files")
        self.stage_all_checkbox.setChecked(True)
        self.stage_all_checkbox.setEnabled(False)
        self.stage_all_checkbox.setToolTip(
            "When saving, include all files you've modified (recommended)\n"
            "(Git term: 'stage' or 'add' - marks files to include in the next commit)"
        )
        self.stage_all_checkbox.stateChanged.connect(self._on_stage_all_changed)
        stage_layout.addWidget(self.stage_all_checkbox)
        stage_layout.addStretch()
        
        group_layout.addLayout(stage_layout)
        
        layout.addWidget(group)
        self._group_changes = group
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    def update_changes(self, file_statuses: list):
        """
        Update the changes list with new file statuses.
        
        Args:
            file_statuses: List of file status dicts from git client
        """
        self._file_statuses = file_statuses
        self.changes_list.clear()
        
        if not file_statuses:
            self.changes_list.setEnabled(False)
            self.stage_all_checkbox.setEnabled(False)
            return
        
        self.changes_list.setEnabled(True)
        self.stage_all_checkbox.setEnabled(True)
        
        for entry in file_statuses:
            status_text = self._friendly_status_text(entry.x, entry.y)
            text = f"{status_text} {entry.path}"
            self.changes_list.addItem(text)
    
    def get_stage_all(self):
        """
        Get current stage all checkbox state.
        
        Returns:
            bool: True if stage all is checked
        """
        return self.stage_all_checkbox.isChecked()
    
    def set_stage_all(self, checked: bool):
        """
        Set stage all checkbox state.
        
        Args:
            checked: True to check the box
        """
        self.stage_all_checkbox.setChecked(checked)
    
    def get_file_statuses(self):
        """
        Get current file statuses.
        
        Returns:
            list: List of file status objects
        """
        return self._file_statuses
    
    def has_changes(self):
        """
        Check if there are any changes.
        
        Returns:
            bool: True if changes exist
        """
        return len(self._file_statuses) > 0
    
    def clear_changes(self):
        """Clear the changes list."""
        self._file_statuses = []
        self.changes_list.clear()
        self.changes_list.setEnabled(False)
        self.stage_all_checkbox.setEnabled(False)
    
    # =========================================================================
    # BaseWidget Overrides
    # =========================================================================
    
    def update_for_repository(self, repo_root: str):
        """Update changes for new repository."""
        self.clear_changes()
    
    def refresh(self):
        """Refresh changes information (trigger parent refresh)."""
        # Changes are refreshed by parent calling update_changes()
        pass
    
    # =========================================================================
    # Internal Helpers
    # =========================================================================
    
    def _on_stage_all_changed(self, state):
        """Handle stage all checkbox change."""
        self._stage_all = self.stage_all_checkbox.isChecked()
        self.stage_all_changed.emit(self._stage_all)
    
    def _on_selection_changed(self):
        """Handle file selection change."""
        selected_items = self.changes_list.selectedItems()
        # Extract file paths from items (remove status prefix)
        selected_paths = []
        for item in selected_items:
            text = item.text()
            # Split on first space after status icon
            parts = text.split(" ", 1)
            if len(parts) > 1:
                selected_paths.append(parts[1])
        
        self.files_selected.emit(selected_paths)
    
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
