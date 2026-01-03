# -*- coding: utf-8 -*-
"""
GitCAD Initialization Wizard Module
Handles installing GitCAD automation into repositories that don't have it.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Tuple

# Qt compatibility layer
try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtWidgets
    except ImportError as e:
        raise ImportError(
            "Neither PySide6 nor PySide2 found. FreeCAD installation may be incomplete."
        ) from e

from freecad_gitpdm.core import log
from freecad_gitpdm.gitcad import create_default_config


class GitCADInitWizard(QtWidgets.QDialog):
    """
    Wizard dialog for initializing GitCAD in a repository.
    
    Guides the user through:
    1. Confirming they want to install GitCAD
    2. Selecting the GitCAD reference directory (where FreeCAD_Automation lives)
    3. Installing files and setting up git LFS
    4. Configuring initial settings
    """
    
    def __init__(self, repo_root: str, parent=None):
        """
        Initialize the wizard.
        
        Args:
            repo_root: Path to repository where GitCAD will be installed
            parent: Parent widget
        """
        super().__init__(parent)
        self.repo_root = Path(repo_root)
        self.gitcad_reference = None
        self.success = False
        
        self.setWindowTitle("Initialize GitCAD")
        self.setModal(True)
        self.resize(600, 400)
        
        self._setup_ui()
        self._find_default_reference()
    
    def _setup_ui(self):
        """Set up the wizard UI."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Title
        title = QtWidgets.QLabel("<h2>Initialize GitCAD File Locking</h2>")
        layout.addWidget(title)
        
        # Repository info
        repo_info = QtWidgets.QLabel(f"<b>Repository:</b> {self.repo_root}")
        repo_info.setWordWrap(True)
        layout.addWidget(repo_info)
        
        layout.addSpacing(10)
        
        # Description
        desc = QtWidgets.QLabel(
            "GitCAD provides automatic file locking, compression, and version "
            "control for FreeCAD files.\n\n"
            "<b>The following will be installed in your repository:</b>\n"
            "• FreeCAD_Automation/ - Scripts and tools for git filters\n"
            "• .gitattributes - Git filter configuration\n"
            "• config.json - Default GitCAD configuration\n\n"
            "<b>Requirements:</b>\n"
            "• Git LFS must be installed for file locking to work\n"
            "• Files will be automatically decompressed for version control\n\n"
            "<i>Note: This works with both new and existing repositories. "
            "Existing files will not be affected.</i>"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(20)
        
        
        # Status label - shows detection status
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Info message if manual setup needed
        self.manual_setup_widget = QtWidgets.QTextEdit()
        self.manual_setup_widget.setReadOnly(True)
        self.manual_setup_widget.setMaximumHeight(100)
        self.manual_setup_widget.setVisible(False)
        layout.addWidget(self.manual_setup_widget)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.install_btn = QtWidgets.QPushButton("Initialize GitCAD")
        self.install_btn.setDefault(True)
        self.install_btn.clicked.connect(self._install_gitcad)
        self.install_btn.setEnabled(False)
        button_layout.addWidget(self.install_btn)
        
        layout.addLayout(button_layout)
    
    def _find_default_reference(self):
        """Try to find a default GitCAD reference directory automatically."""
    def _find_default_reference(self):
        """Try to find a default GitCAD reference directory automatically."""
        # Check if GitCAD-main is in the same parent directory
        potential_paths = [
            self.repo_root / "GitCAD-main",
            self.repo_root.parent / "GitCAD-main",
            Path(__file__).parent.parent.parent / "GitCAD-main",
        ]
        
        for path in potential_paths:
            if self._is_valid_reference(path):
                self.gitcad_reference = path
                self.status_label.setText(f"✓ Found GitCAD reference at: {path}")
                self.status_label.setStyleSheet("color: green;")
                self.install_btn.setEnabled(True)
                log.info(f"Auto-detected GitCAD reference: {path}")
                return
        
        # Not found - show error with instructions
        self.status_label.setText(
            "⚠ GitCAD reference not found\n\n"
            "GitCAD-main folder (containing FreeCAD_Automation) was not found.\n"
            "Please ensure GitCAD-main is in the same directory as your GitPDM installation."
        )
        self.status_label.setStyleSheet("color: orange;")
        self.install_btn.setEnabled(False)
        
        # Show manual setup instructions
        self.manual_setup_widget.setHtml(
            "<b>Manual Setup:</b><br>"
            "1. Clone or download GitCAD-main to the same folder as GitPDM<br>"
            "2. Ensure it contains the FreeCAD_Automation folder<br>"
            "3. Reopen this dialog to try again"
        )
        self.manual_setup_widget.setVisible(True)
    
    def _is_valid_reference(self, path: Path) -> bool:
        """Check if a path is a valid GitCAD reference."""
        if not path.exists():
            return False
        
        automation_dir = path / "FreeCAD_Automation"
        if not automation_dir.is_dir():
            return False
        
        # Check for key files
        required_files = [
            automation_dir / "FCStdFileTool.py",
            automation_dir / "git",
        ]
        
        return all(f.exists() for f in required_files)
    
    def _install_gitcad(self):
        """Install GitCAD into the repository."""
        if not self.gitcad_reference:
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid Reference",
                "Please select a valid GitCAD reference directory."
            )
            return
        
        self.install_btn.setEnabled(False)
        self.status_label.setText("Installing GitCAD...")
        QtWidgets.QApplication.processEvents()
        
        try:
            # Install files
            self._copy_automation_directory()
            self._copy_gitattributes()
            self._create_config()
            
            self.success = True
            self.status_label.setText("✓ GitCAD installed successfully!")
            self.status_label.setStyleSheet("color: green;")
            
            QtWidgets.QMessageBox.information(
                self,
                "Installation Complete",
                "GitCAD has been installed successfully!\n\n"
                "Next steps:\n"
                "1. Ensure Git LFS is installed: git lfs install\n"
                "2. Commit the new files to your repository\n"
                "3. Other collaborators will need Git LFS to use locking"
            )
            
            self.accept()
            
        except Exception as e:
            log.error(f"Error installing GitCAD: {e}")
            self.status_label.setText(f"✗ Installation failed: {e}")
            self.status_label.setStyleSheet("color: red;")
            self.install_btn.setEnabled(True)
            
            QtWidgets.QMessageBox.critical(
                self,
                "Installation Failed",
                f"Failed to install GitCAD:\n\n{e}"
            )
    
    def _copy_automation_directory(self):
        """Copy the FreeCAD_Automation directory."""
        source = self.gitcad_reference / "FreeCAD_Automation"
        dest = self.repo_root / "FreeCAD_Automation"
        
        if dest.exists():
            # Backup existing directory
            backup = self.repo_root / "FreeCAD_Automation.backup"
            if backup.exists():
                shutil.rmtree(backup)
            shutil.move(str(dest), str(backup))
            log.info(f"Backed up existing FreeCAD_Automation to {backup}")
        
        shutil.copytree(str(source), str(dest))
        log.info(f"Copied FreeCAD_Automation to {dest}")
    
    def _copy_gitattributes(self):
        """Copy .gitattributes file if it doesn't exist."""
        source = self.gitcad_reference / ".gitattributes"
        dest = self.repo_root / ".gitattributes"
        
        if not dest.exists() and source.exists():
            shutil.copy2(str(source), str(dest))
            log.info(f"Copied .gitattributes to {dest}")
        elif dest.exists():
            log.info(".gitattributes already exists, skipping")
        else:
            log.warning("Source .gitattributes not found, skipping")
    
    def _create_config(self):
        """Create default config.json."""
        result = create_default_config(str(self.repo_root), "")
        if not result.ok:
            error_msg = result.error.message if result.error else "Unknown error"
            raise RuntimeError(f"Failed to create config.json: {error_msg}")
        log.info(f"Created config.json at {self.repo_root / 'FreeCAD_Automation' / 'config.json'}")


def show_init_wizard(repo_root: str, parent=None) -> bool:
    """
    Show the GitCAD initialization wizard.
    
    Args:
        repo_root: Path to repository
        parent: Parent widget
        
    Returns:
        bool: True if installation was successful
    """
    wizard = GitCADInitWizard(repo_root, parent)
    wizard.exec_()
    return wizard.success
