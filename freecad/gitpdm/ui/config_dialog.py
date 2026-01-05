"""
GitCAD Configuration Editor Module
Provides UI for editing GitCAD config.json settings.
"""

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
from freecad.gitpdm.core.config_manager import load_config, save_config


class GitCADConfigDialog(QtWidgets.QDialog):
    """
    Dialog for editing GitCAD configuration.
    
    Allows editing:
    - git_relative_project_path: Subdirectory within repo for FreeCAD files
    - python_path: Path to Python interpreter for GitCAD scripts
    """
    
    def __init__(self, repo_root: str, parent=None):
        """
        Initialize the configuration dialog.
        
        Args:
            repo_root: Path to repository root
            parent: Parent widget
        """
        super().__init__(parent)
        self.repo_root = Path(repo_root)
        self.config = None
        self.config_modified = False
        
        self.setWindowTitle("GitPDM Configuration")
        self.setModal(True)
        self.resize(550, 300)
        
        self._load_config()
        self._setup_ui()
        
    def _load_config(self):
        """Load the current configuration."""
        try:
            self.config = load_config(self.repo_root)
            log.debug("Loaded config")
        except Exception as e:
            log.warning(f"Could not load config: {e}")
            # Create default config
            from freecad.gitpdm.core.config_manager import FCStdConfig
            self.config = FCStdConfig()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Title
        title = QtWidgets.QLabel("<h2>GitPDM Configuration</h2>")
        layout.addWidget(title)
        
        # Form layout for settings
        form = QtWidgets.QFormLayout()
        form.setSpacing(12)
        
        # Uncompressed suffix
        suffix_label = QtWidgets.QLabel("Uncompressed Suffix:")
        suffix_label.setToolTip("Suffix added to uncompressed directory names")
        self.suffix_edit = QtWidgets.QLineEdit(self.config.uncompressed_suffix)
        self.suffix_edit.textChanged.connect(self._on_config_changed)
        form.addRow(suffix_label, self.suffix_edit)
        
        # Compression enabled
        compress_label = QtWidgets.QLabel("Compress Binaries:")
        compress_label.setToolTip("Compress binary files (*.brp, etc.) separately")
        self.compress_check = QtWidgets.QCheckBox("Enabled")
        self.compress_check.setChecked(self.config.compress_binaries)
        self.compress_check.stateChanged.connect(self._on_config_changed)
        form.addRow(compress_label, self.compress_check)
        
        # Require lock
        lock_label = QtWidgets.QLabel("Require Lock:")
        lock_label.setToolTip("Require Git LFS lock before modifying FCStd files")
        self.lock_check = QtWidgets.QCheckBox("Enabled")
        self.lock_check.setChecked(self.config.require_lock)
        self.lock_check.stateChanged.connect(self._on_config_changed)
        form.addRow(lock_label, self.lock_check)
        
        layout.addLayout(form)
        layout.addStretch()
        
        # Info box
        info_box = QtWidgets.QTextEdit()
        info_box.setReadOnly(True)
        info_box.setMaximumHeight(80)
        info_box.setHtml(
            "<b>Configuration Location:</b><br>"
            f"<code>{self.repo_root / '.gitpdm' / 'config.json'}</code><br>"
            f"<small>(Legacy: <code>{self.repo_root / 'FreeCAD_Automation' / 'config.json'}</code>)</small>"
        )
        layout.addWidget(info_box)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.save_btn = QtWidgets.QPushButton("Save")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._save_config)
        self.save_btn.setEnabled(False)  # Disabled until changes made
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def _on_config_changed(self):
        """Mark configuration as modified."""
        self.config_modified = True
        self.save_btn.setEnabled(True)
    
    def _save_config(self):
        """Save the configuration."""
        # Update config object from UI
        self.config.uncompressed_suffix = self.suffix_edit.text().strip()
        self.config.compress_binaries = self.compress_check.isChecked()
        self.config.require_lock = self.lock_check.isChecked()
        
        # Save to file
        try:
            save_config(self.repo_root, self.config)
            QtWidgets.QMessageBox.information(
                self,
                "Configuration Saved",
                "Configuration has been saved successfully."
            )
            self.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save configuration:\n\n{e}"
            )


def show_config_dialog(repo_root: str, parent=None) -> bool:
    """
    Show the GitCAD configuration dialog.
    
    Args:
        repo_root: Path to repository
        parent: Parent widget
        
    Returns:
        bool: True if configuration was saved
    """
    dialog = GitCADConfigDialog(repo_root, parent)
    return dialog.exec_() == QtWidgets.QDialog.Accepted
