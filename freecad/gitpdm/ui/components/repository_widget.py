"""
Repository Widget Component
Sprint 5 Phase 1: Repository selector and management

Extracted from monolithic panel.py for better maintainability.
Handles: Repository path selection, browsing, cloning, creating, validation.
"""

# Qt compatibility layer
from PySide6 import QtCore, QtWidgets

import os
from freecad.gitpdm.ui.components.base_widget import BaseWidget
from freecad.gitpdm.core import log, settings


class RepositoryWidget(BaseWidget):
    """
    Widget for repository selection and management.
    
    Shows:
    - Repository path selector field
    - Browse, Clone, New buttons
    - Root path display (optional)
    - Validation status
    - Create Repo / Connect Remote buttons (conditional)
    
    Signals:
        repository_changed: Emitted when repository path changes
        repository_validated: Emitted when validation completes
        browse_requested: Emitted when user clicks Browse
        clone_requested: Emitted when user clicks Clone
        new_repo_requested: Emitted when user clicks New
        create_repo_requested: Emitted when user clicks Create Repo
        connect_remote_requested: Emitted when user clicks Connect Remote
        refresh_requested: Emitted when user clicks Refresh
    """
    
    repository_changed = QtCore.Signal(str)  # New repo path
    repository_validated = QtCore.Signal(dict)  # Validation result
    browse_requested = QtCore.Signal()
    clone_requested = QtCore.Signal()
    new_repo_requested = QtCore.Signal()
    create_repo_requested = QtCore.Signal()
    connect_remote_requested = QtCore.Signal()
    refresh_requested = QtCore.Signal()
    
    def __init__(self, parent=None, git_client=None, job_runner=None):
        """
        Initialize repository widget.
        
        Args:
            parent: Parent widget (main panel)
            git_client: GitClient instance
            job_runner: JobRunner instance
        """
        super().__init__(parent, git_client, job_runner)
        
        # State
        self._current_path = ""
        self._current_root = None
        self._is_valid_repo = False
        self._show_root_details = False
        
        # Build UI
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        self._build_ui(layout)
        self.setLayout(layout)
        
        log.debug("RepositoryWidget initialized")
    
    # =========================================================================
    # UI Construction
    # =========================================================================
    
    def _build_ui(self, layout):
        """Build the repository selector UI."""
        group = self.create_group_box("Repository")
        group_layout = QtWidgets.QVBoxLayout()
        group_layout.setContentsMargins(6, 3, 6, 3)
        group_layout.setSpacing(2)
        group.setLayout(group_layout)
        
        # Repo path row
        path_layout = QtWidgets.QHBoxLayout()
        path_layout.setSpacing(4)
        
        self.repo_path_field = QtWidgets.QLineEdit()
        self.repo_path_field.setPlaceholderText("Select your project folder...")
        self.repo_path_field.setToolTip(
            "The folder where your FreeCAD project files are stored\n"
            "(Git term: 'repository' or 'repo' - the project folder tracked by Git)"
        )
        self.repo_path_field.editingFinished.connect(self._on_path_editing_finished)
        path_layout.addWidget(self.repo_path_field)
        
        browse_btn = QtWidgets.QPushButton("Browse...")
        browse_btn.setToolTip(
            "Select an existing project folder on your computer\n"
            "(Git term: open a local 'repository')"
        )
        browse_btn.clicked.connect(lambda: self.browse_requested.emit())
        path_layout.addWidget(browse_btn)
        
        clone_btn = QtWidgets.QPushButton("Join Team Project…")
        clone_btn.setToolTip(
            "Download a project from GitHub to work on with your team\n"
            "(Git term: 'clone' - makes a local copy of a remote repository)"
        )
        clone_btn.clicked.connect(lambda: self.clone_requested.emit())
        path_layout.addWidget(clone_btn)
        
        new_repo_btn = QtWidgets.QPushButton("Start New Project…")
        new_repo_btn.setToolTip(
            "Create a brand new project and store it on GitHub\n"
            "(Git term: 'init' + create remote 'repository')"
        )
        new_repo_btn.clicked.connect(lambda: self.new_repo_requested.emit())
        path_layout.addWidget(new_repo_btn)
        
        group_layout.addLayout(path_layout)
        
        # Root details (collapsed by default)
        self.root_toggle_btn = QtWidgets.QToolButton()
        self.root_toggle_btn.setText("Show root")
        self.root_toggle_btn.setArrowType(QtCore.Qt.RightArrow)
        self.root_toggle_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.root_toggle_btn.setCheckable(True)
        self.root_toggle_btn.setEnabled(False)
        self.root_toggle_btn.toggled.connect(self._on_root_toggle)
        self.root_toggle_btn.setVisible(False)  # Hidden by default
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
        
        self.validate_caption = QtWidgets.QLabel("Validate:")
        self.validate_caption.setVisible(False)  # Hidden by default
        validation_layout.addWidget(self.validate_caption)
        
        self.validate_label = QtWidgets.QLabel("Not checked")
        self.validate_label.setStyleSheet("color: gray; font-style: italic;")
        self.validate_label.setVisible(False)  # Hidden by default
        validation_layout.addWidget(self.validate_label)
        validation_layout.addStretch()
        
        self.create_repo_btn = QtWidgets.QPushButton("Create Repo")
        self.create_repo_btn.setMinimumWidth(130)
        self.create_repo_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.create_repo_btn.clicked.connect(lambda: self.create_repo_requested.emit())
        self.create_repo_btn.setVisible(False)
        validation_layout.addWidget(self.create_repo_btn)
        
        self.connect_remote_btn = QtWidgets.QPushButton("Connect Remote")
        self.connect_remote_btn.setMinimumWidth(130)
        self.connect_remote_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.connect_remote_btn.clicked.connect(lambda: self.connect_remote_requested.emit())
        self.connect_remote_btn.setVisible(False)
        validation_layout.addWidget(self.connect_remote_btn)
        
        refresh_btn = QtWidgets.QPushButton("Refresh Status")
        refresh_btn.setMinimumWidth(130)
        refresh_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,
        )
        refresh_btn.clicked.connect(lambda: self.refresh_requested.emit())
        refresh_btn.setVisible(False)  # Hidden by default
        validation_layout.addWidget(refresh_btn)
        
        group_layout.addLayout(validation_layout)
        
        layout.addWidget(group)
        self._group_repo = group
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    def get_path(self):
        """
        Get current repository path.
        
        Returns:
            str: Current path from field
        """
        return self.repo_path_field.text()
    
    def set_path(self, path: str):
        """
        Set repository path.
        
        Args:
            path: Path to set
        """
        self.repo_path_field.setText(path)
        self._current_path = path
    
    def get_root(self):
        """
        Get current repository root.
        
        Returns:
            str: Current repository root or None
        """
        return self._current_root
    
    def update_validation(self, is_valid: bool, root: str = None, message: str = ""):
        """
        Update validation status display.
        
        Args:
            is_valid: True if repository is valid
            root: Repository root path
            message: Validation message
        """
        self._is_valid_repo = is_valid
        self._current_root = root
        
        if is_valid and root:
            self.repo_root_label.setText(root)
            self.root_toggle_btn.setEnabled(True)
        else:
            self.repo_root_label.setText("—")
            self.root_toggle_btn.setEnabled(False)
    
    def show_create_repo_button(self, show: bool):
        """
        Show/hide Create Repo button.
        
        Args:
            show: True to show button
        """
        self.create_repo_btn.setVisible(show)
    
    def show_connect_remote_button(self, show: bool):
        """
        Show/hide Connect Remote button.
        
        Args:
            show: True to show button
        """
        self.connect_remote_btn.setVisible(show)
    
    def load_saved_path(self):
        """Load last used repository path from settings."""
        saved_path = settings.load_repo_path()
        if saved_path:
            self.set_path(saved_path)
            return saved_path
        return None
    
    def save_current_path(self):
        """Save current path to settings."""
        path = self.get_path()
        if path:
            settings.save_repo_path(path)
    
    # =========================================================================
    # BaseWidget Overrides
    # =========================================================================
    
    def update_for_repository(self, repo_root: str):
        """Update UI for new repository."""
        self._current_root = repo_root
        if repo_root:
            self._is_valid_repo = True
            self.repo_root_label.setText(repo_root)
            self.root_toggle_btn.setEnabled(True)
        else:
            self._is_valid_repo = False
            self.repo_root_label.setText("—")
            self.root_toggle_btn.setEnabled(False)
    
    def refresh(self):
        """Refresh repository information."""
        self.refresh_requested.emit()
    
    # =========================================================================
    # Internal Helpers
    # =========================================================================
    
    def _on_path_editing_finished(self):
        """Handle when user finishes editing path."""
        new_path = self.repo_path_field.text()
        if new_path != self._current_path:
            self._current_path = new_path
            self.save_current_path()
            self.repository_changed.emit(new_path)
    
    def _on_root_toggle(self, checked: bool):
        """Handle root details toggle."""
        self._show_root_details = checked
        self.repo_root_row.setVisible(checked)
        
        if checked:
            self.root_toggle_btn.setArrowType(QtCore.Qt.DownArrow)
            self.root_toggle_btn.setText("Hide root")
        else:
            self.root_toggle_btn.setArrowType(QtCore.Qt.RightArrow)
            self.root_toggle_btn.setText("Show root")
