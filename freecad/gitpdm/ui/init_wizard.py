"""
GitPDM Initialization Wizard Module
Handles initializing GitPDM configuration in repositories.

Sprint 7: Simplified to only create .gitpdm/config.json (no FreeCAD_Automation dependency)
"""

import os
from pathlib import Path
from typing import Optional

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
from freecad.gitpdm.core.config_manager import save_config, FCStdConfig, has_config


class GitPDMInitWizard(QtWidgets.QDialog):
    """
    Simple initialization dialog for GitPDM.
    
    Creates .gitpdm/config.json to enable file locking and other features.
    """
    
    def __init__(self, repo_root: str, parent=None):
        """
        Initialize the wizard.
        
        Args:
            repo_root: Path to repository where GitPDM will be initialized
            parent: Parent widget
        """
        super().__init__(parent)
        self.repo_root = Path(repo_root)
        self.success = False
        
        self.setWindowTitle("Initialize GitPDM")
        self.setModal(True)
        self.resize(500, 300)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the wizard UI."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Title
        title = QtWidgets.QLabel("<h2>Initialize GitPDM</h2>")
        layout.addWidget(title)
        
        # Repository info
        repo_info = QtWidgets.QLabel(f"<b>Repository:</b> {self.repo_root}")
        repo_info.setWordWrap(True)
        layout.addWidget(repo_info)
        
        layout.addSpacing(10)
        
        # Description
        desc = QtWidgets.QLabel(
            "GitPDM provides file locking, version control, and collaboration "
            "features for FreeCAD projects.\n\n"
            "<b>This will create:</b>\n"
            "• .gitpdm/config.json - Configuration for file handling\n\n"
            "<b>Features enabled:</b>\n"
            "• File locking via Git LFS (requires Git LFS to be installed)\n"
            "• Automatic file compression for large binaries\n"
            "• Export/import of .FCStd files for version control\n\n"
            "<b>Requirements:</b>\n"
            "• Git repository (already satisfied)\n"
            "• Git LFS for file locking (install separately if needed)\n\n"
            "<i>Note: This is a one-time setup. Existing files are not modified.</i>"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(20)
        
        # Status label
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.install_btn = QtWidgets.QPushButton("Initialize GitPDM")
        self.install_btn.setDefault(True)
        self.install_btn.clicked.connect(self._initialize_gitpdm)
        button_layout.addWidget(self.install_btn)
        
        layout.addLayout(button_layout)
    
    def _initialize_gitpdm(self):
        """Initialize GitPDM in the repository."""
        self.install_btn.setEnabled(False)
        self.status_label.setText("Initializing GitPDM...")
        QtWidgets.QApplication.processEvents()
        
        try:
            # Create default config
            config = FCStdConfig()
            save_config(self.repo_root, config)
            log.info(f"Created .gitpdm/config.json at {self.repo_root}")
            
            self.success = True
            self.status_label.setText("✓ GitPDM initialized successfully!")
            self.status_label.setStyleSheet("color: green;")
            
            QtWidgets.QMessageBox.information(
                self,
                "Initialization Complete",
                "GitPDM has been initialized!\n\n"
                "File locking and other features are now available.\n\n"
                "Next steps:\n"
                "• Install Git LFS if not already installed: git lfs install\n"
                "• Right-click .FCStd files to lock/unlock them\n"
                "• Commit .gitpdm/config.json to share settings with your team"
            )
            
            self.accept()
            
        except Exception as e:
            log.error(f"Error initializing GitPDM: {e}")
            self.status_label.setText(f"✗ Initialization failed: {e}")
            self.status_label.setStyleSheet("color: red;")
            self.install_btn.setEnabled(True)
            
            QtWidgets.QMessageBox.critical(
                self,
                "Initialization Failed",
                f"Failed to initialize GitPDM:\n\n{e}"
            )


def show_init_wizard(repo_root: str, parent=None) -> bool:
    """
    Show initialization wizard and return whether it succeeded.
    
    Args:
        repo_root: Path to repository
        parent: Parent widget
        
    Returns:
        True if initialization succeeded, False otherwise
    """
    # Check if already initialized
    if has_config(repo_root):
        result = QtWidgets.QMessageBox.question(
            parent,
            "Already Initialized",
            "GitPDM is already initialized in this repository.\n\n"
            "Do you want to reinitialize? This will overwrite .gitpdm/config.json.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if result != QtWidgets.QMessageBox.Yes:
            return False
    
    wizard = GitPDMInitWizard(repo_root, parent)
    wizard.exec()
    return wizard.success


def auto_initialize_if_needed(repo_root: str) -> bool:
    """
    Automatically initialize GitPDM if not already configured.
    
    This is called automatically when a repository is opened.
    Creates .gitpdm/config.json silently if it doesn't exist.
    
    Args:
        repo_root: Path to repository
        
    Returns:
        True if initialization was performed, False if already initialized
    """
    if has_config(repo_root):
        return False
    
    try:
        config = FCStdConfig()
        save_config(Path(repo_root), config)
        log.info(f"Auto-initialized GitPDM for repository: {repo_root}")
        return True
    except Exception as e:
        log.error(f"Failed to auto-initialize GitPDM: {e}")
        return False

