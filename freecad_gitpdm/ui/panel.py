# -*- coding: utf-8 -*-
"""
GitPDM Panel UI Module
Sprint 0: Main dockable panel implementation
"""

# Qt compatibility layer - try PySide2 first, then PySide6
try:
    from PySide2 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError as e:
        raise ImportError(
            "Neither PySide2 nor PySide6 found. "
            "FreeCAD installation may be incomplete."
        ) from e

from freecad_gitpdm.core import log, settings


class GitPDMDockWidget(QtWidgets.QDockWidget):
    """
    Main GitPDM dock widget panel
    Sprint 0: Placeholder UI with all sections
    """

    def __init__(self):
        super().__init__()
        self.setObjectName("GitPDM_DockWidget")
        self.setWindowTitle("Git PDM")
        self.setMinimumWidth(300)

        # Create main widget and layout
        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)

        # Build UI sections
        self._build_repo_selector(main_layout)
        self._build_status_section(main_layout)
        self._build_changes_section(main_layout)
        self._build_buttons_section(main_layout)
        self._build_repo_browser_section(main_layout)

        # Add stretch at bottom to push everything up
        main_layout.addStretch()

        # Load saved repo path
        self._load_saved_repo_path()

        log.info("GitPDM dock panel initialized")

    def _build_repo_selector(self, layout):
        """
        Build the repository selector section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("Repository")
        group_layout = QtWidgets.QVBoxLayout()
        group.setLayout(group_layout)

        # Repo path row
        path_layout = QtWidgets.QHBoxLayout()
        self.repo_path_field = QtWidgets.QLineEdit()
        self.repo_path_field.setPlaceholderText(
            "Select repository folder..."
        )
        self.repo_path_field.textChanged.connect(
            self._on_repo_path_changed
        )
        path_layout.addWidget(self.repo_path_field)

        browse_btn = QtWidgets.QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_clicked)
        path_layout.addWidget(browse_btn)

        group_layout.addLayout(path_layout)

        # Validation label
        self.validate_label = QtWidgets.QLabel("Not checked")
        self.validate_label.setStyleSheet("color: gray; font-style: italic;")
        group_layout.addWidget(self.validate_label)

        layout.addWidget(group)

    def _build_status_section(self, layout):
        """
        Build the status information section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("Status")
        group_layout = QtWidgets.QFormLayout()
        group.setLayout(group_layout)

        # Branch label
        self.branch_label = QtWidgets.QLabel("—")
        self.branch_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        group_layout.addRow("Branch:", self.branch_label)

        # Ahead/Behind label
        self.sync_label = QtWidgets.QLabel("—")
        self.sync_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        group_layout.addRow("Sync:", self.sync_label)

        layout.addWidget(group)

    def _build_changes_section(self, layout):
        """
        Build the changes list section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("Changes")
        group_layout = QtWidgets.QVBoxLayout()
        group.setLayout(group_layout)

        # Info label
        info_label = QtWidgets.QLabel(
            "Modified, staged, and untracked files will appear here."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        group_layout.addWidget(info_label)

        # Changes list widget (placeholder)
        self.changes_list = QtWidgets.QListWidget()
        self.changes_list.setMaximumHeight(150)
        self.changes_list.setEnabled(False)  # Disabled in Sprint 0
        group_layout.addWidget(self.changes_list)

        layout.addWidget(group)

    def _build_buttons_section(self, layout):
        """
        Build the action buttons section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("Actions")
        group_layout = QtWidgets.QVBoxLayout()
        group.setLayout(group_layout)

        # First row: Fetch, Pull
        row1_layout = QtWidgets.QHBoxLayout()
        self.fetch_btn = QtWidgets.QPushButton("Fetch")
        self.fetch_btn.setEnabled(False)
        row1_layout.addWidget(self.fetch_btn)

        self.pull_btn = QtWidgets.QPushButton("Pull")
        self.pull_btn.setEnabled(False)
        row1_layout.addWidget(self.pull_btn)

        group_layout.addLayout(row1_layout)

        # Second row: Commit, Push
        row2_layout = QtWidgets.QHBoxLayout()
        self.commit_btn = QtWidgets.QPushButton("Commit")
        self.commit_btn.setEnabled(False)
        row2_layout.addWidget(self.commit_btn)

        self.push_btn = QtWidgets.QPushButton("Push")
        self.push_btn.setEnabled(False)
        row2_layout.addWidget(self.push_btn)

        group_layout.addLayout(row2_layout)

        # Third row: Publish
        self.publish_btn = QtWidgets.QPushButton("Publish Branch")
        self.publish_btn.setEnabled(False)
        group_layout.addWidget(self.publish_btn)

        layout.addWidget(group)

    def _build_repo_browser_section(self, layout):
        """
        Build the repository browser section
        
        Args:
            layout: Parent layout to add widgets to
        """
        group = QtWidgets.QGroupBox("Repository Browser")
        group_layout = QtWidgets.QVBoxLayout()
        group.setLayout(group_layout)

        # Info label
        info_label = QtWidgets.QLabel(
            "Browse commits, branches, and tags here (coming soon)."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        group_layout.addWidget(info_label)

        # Tree/list widget placeholder
        self.repo_tree = QtWidgets.QTreeWidget()
        self.repo_tree.setHeaderLabels(["Item", "Details"])
        self.repo_tree.setMaximumHeight(100)
        self.repo_tree.setEnabled(False)  # Disabled in Sprint 0
        group_layout.addWidget(self.repo_tree)

        layout.addWidget(group)

    def _on_browse_clicked(self):
        """
        Handle Browse button click - open folder dialog
        """
        current_path = self.repo_path_field.text()
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Repository Folder",
            current_path if current_path else "",
            QtWidgets.QFileDialog.ShowDirsOnly
        )

        if folder:
            self.repo_path_field.setText(folder)
            log.info(f"Selected repo folder: {folder}")

    def _on_repo_path_changed(self, text):
        """
        Handle repo path text field changes
        
        Args:
            text: New text value
        """
        # Save to persistent storage
        settings.save_repo_path(text)

        # Update validation label (no real validation yet)
        if text:
            self.validate_label.setText("Not validated (Sprint 0)")
            self.validate_label.setStyleSheet(
                "color: orange; font-style: italic;"
            )
        else:
            self.validate_label.setText("Not checked")
            self.validate_label.setStyleSheet(
                "color: gray; font-style: italic;"
            )

    def _load_saved_repo_path(self):
        """
        Load the saved repository path from settings
        """
        saved_path = settings.load_repo_path()
        if saved_path:
            self.repo_path_field.setText(saved_path)
            log.info(f"Restored repo path from settings: {saved_path}")
