# -*- coding: utf-8 -*-
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
        from PySide2 import QtCore, QtWidgets
    except ImportError as e:
        raise ImportError(
            "Neither PySide6 nor PySide2 found. FreeCAD installation may be incomplete."
        ) from e

from freecad_gitpdm.core import log
from freecad_gitpdm.gitcad import load_gitcad_config, save_gitcad_config


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
        self.config_auto_populated = False  # Track if we auto-populated the path
        
        self.setWindowTitle("GitCAD Configuration")
        self.setModal(True)
        self.resize(550, 300)
        
        self._load_config()
        self._setup_ui()
        
    def _load_config(self):
        """Load the current configuration."""
        result = load_gitcad_config(str(self.repo_root))
        if result.ok:
            self.config = result.value
            log.debug("Loaded GitCAD config")
            
            # Auto-populate empty Python path with FreeCAD executable
            if not self.config.freecad_python_instance_path:
                try:
                    import sys
                    self.config.freecad_python_instance_path = sys.executable
                    self.config_auto_populated = True
                    log.info(f"Auto-populated Python path: {sys.executable}")
                except Exception as e:
                    log.debug(f"Could not auto-detect Python path: {e}")
        else:
            error_msg = result.error.message if result.error else "Unknown error"
            log.warning(f"Could not load GitCAD config: {error_msg}")
            # Create empty config with auto-detected path
            from freecad_gitpdm.gitcad.config import GitCADConfig
            try:
                import sys
                python_path = sys.executable
                self.config_auto_populated = True
            except:
                python_path = ""
            self.config = GitCADConfig(
                freecad_python_instance_path=python_path
            )
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Title
        title = QtWidgets.QLabel("<h2>GitCAD Configuration</h2>")
        layout.addWidget(title)
        
        # Form layout for settings
        form = QtWidgets.QFormLayout()
        form.setSpacing(12)
        
        # Python path
        python_path_label = QtWidgets.QLabel("Python Path:")
        python_path_label.setToolTip(
            "Path to Python interpreter for GitCAD scripts.\n"
            "Leave empty to use system default."
        )
        
        python_path_row = QtWidgets.QHBoxLayout()
        self.python_path_edit = QtWidgets.QLineEdit()
        self.python_path_edit.setText(self.config.freecad_python_instance_path)
        self.python_path_edit.setPlaceholderText("e.g., /usr/bin/python3 or leave empty")
        self.python_path_edit.textChanged.connect(self._on_config_changed)
        python_path_row.addWidget(self.python_path_edit)
        
        python_browse_btn = QtWidgets.QPushButton("Browse...")
        python_browse_btn.clicked.connect(self._browse_python)
        python_path_row.addWidget(python_browse_btn)
        
        python_path_help = QtWidgets.QLabel(
            "Optional: Specify Python interpreter if GitCAD scripts need a specific version"
        )
        python_path_help.setWordWrap(True)
        python_path_help.setStyleSheet("color: gray; font-size: 9pt;")
        
        form.addRow(python_path_label, python_path_row)
        form.addRow("", python_path_help)
        
        layout.addLayout(form)
        layout.addStretch()
        
        # Info box
        info_box = QtWidgets.QTextEdit()
        info_box.setReadOnly(True)
        info_box.setMaximumHeight(80)
        info_box.setHtml(
            "<b>Configuration Location:</b><br>"
            f"<code>{self.repo_root / 'FreeCAD_Automation' / 'config.json'}</code>"
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
        # Enable save button if we auto-populated the path
        self.save_btn.setEnabled(self.config_auto_populated)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def _on_config_changed(self):
        """Mark configuration as modified."""
        self.config_modified = True
        self.save_btn.setEnabled(True)
    
    def _browse_python(self):
        """Browse for Python executable."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Python Executable",
            "",
            "Executables (*.exe);;All Files (*)" if QtCore.QSysInfo.productType() == "windows" else "All Files (*)"
        )
        
        if path:
            self.python_path_edit.setText(path)
    
    def _save_config(self):
        """Save the configuration."""
        # Update config object
        self.config.freecad_python_instance_path = self.python_path_edit.text().strip()
        
        # Save to file
        result = save_gitcad_config(str(self.repo_root), self.config)
        
        if result.ok:
            QtWidgets.QMessageBox.information(
                self,
                "Configuration Saved",
                "GitCAD configuration has been saved successfully."
            )
            self.accept()
        else:
            error_msg = result.error.message if result.error else "Unknown error"
            QtWidgets.QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save configuration:\n\n{error_msg}"
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
