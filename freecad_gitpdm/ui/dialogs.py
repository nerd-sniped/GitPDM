# -*- coding: utf-8 -*-
"""
GitPDM Dialog UI Module
Sprint 3: Dialogs for pull workflow
"""

# Qt compatibility layer - try PySide6 first, then PySide2
try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError as e:
        raise ImportError(
            "Neither PySide6 nor PySide2 found. "
            "FreeCAD installation may be incomplete."
        ) from e

from freecad_gitpdm.core import log


class UncommittedChangesWarningDialog(QtWidgets.QDialog):
    """Warning dialog shown before pull when local changes exist."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Uncommitted Changes")
        self.setModal(True)
        self.setMinimumWidth(380)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        main_layout = QtWidgets.QHBoxLayout()
        icon = QtWidgets.QLabel()
        icon.setPixmap(
            self.style().standardIcon(
                QtWidgets.QStyle.SP_MessageBoxWarning
            ).pixmap(40, 40)
        )
        main_layout.addWidget(icon)

        message = QtWidgets.QLabel(
            "You have local changes.\n\n"
            "Pull (fast-forward) may fail.\n"
            "Consider committing or stashing first."
        )
        message.setWordWrap(True)
        main_layout.addWidget(message)

        layout.addLayout(main_layout)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.setDefault(True)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        continue_btn = QtWidgets.QPushButton("Continue")
        continue_btn.clicked.connect(self.accept)
        btn_layout.addWidget(continue_btn)

        layout.addLayout(btn_layout)

    def show_and_ask(self):
        """Show dialog and return True if user chooses Continue."""
        return self.exec() == QtWidgets.QDialog.Accepted


class PullErrorDialog(QtWidgets.QDialog):
    """Dialog showing categorized pull error with details."""

    def __init__(self, error_code, stderr, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pull Failed")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        self._error_code = error_code
        self._stderr = stderr

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        header_layout = QtWidgets.QHBoxLayout()
        icon_label = QtWidgets.QLabel()
        icon_label.setPixmap(
            self.style().standardIcon(
                QtWidgets.QStyle.SP_MessageBoxCritical
            ).pixmap(48, 48)
        )
        header_layout.addWidget(icon_label)

        message_label = QtWidgets.QLabel(
            self._friendly_message(error_code)
        )
        message_label.setWordWrap(True)
        header_layout.addWidget(message_label)

        layout.addLayout(header_layout)

        details_group = QtWidgets.QGroupBox("Details")
        details_layout = QtWidgets.QVBoxLayout()
        details_group.setLayout(details_layout)

        details_text = QtWidgets.QTextEdit()
        details_text.setReadOnly(True)
        details_text.setMaximumHeight(150)
        details_text.setText(self._stderr)
        details_text.setFont(QtGui.QFont("Courier", 9))
        details_layout.addWidget(details_text)

        copy_layout = QtWidgets.QHBoxLayout()
        copy_btn = QtWidgets.QPushButton("Copy Details")
        copy_btn.clicked.connect(self._on_copy_details)
        copy_layout.addWidget(copy_btn)
        copy_layout.addStretch()
        details_layout.addLayout(copy_layout)

        layout.addWidget(details_group)

        close_layout = QtWidgets.QHBoxLayout()
        close_layout.addStretch()
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)

    def _friendly_message(self, code):
        """Return user-friendly message for error code."""
        if code == "WORKING_TREE_DIRTY":
            return (
                "Pull failed: Uncommitted changes.\n\n"
                "Commit or stash using GitHub Desktop, then pull."
            )
        if code == "DIVERGED_OR_NON_FF":
            return (
                "Fast-forward not possible: branches diverged.\n\n"
                "Fix without terminal:\n"
                " 1) Open GitHub Desktop and pull (merge or rebase).\n"
                " 2) Resolve conflicts there if prompted and finish pull.\n"
                " 3) Back in GitPDM: Refresh Status, then Push."
            )
        if code == "AUTH_OR_PERMISSION":
            return (
                "Authentication or permission issue.\n\n"
                "Sign in via GitHub Desktop, then try again."
            )
        if code == "NO_REMOTE":
            return (
                "Remote not found. Check remote config and network."
            )
        if code == "TIMEOUT":
            return (
                "Pull timed out (>2 minutes). Check connection and retry."
            )
        return (
            "Pull failed due to an unexpected error. Check details below."
        )

    def _on_copy_details(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self._stderr)
        log.info("Pull error details copied to clipboard")


class PushErrorDialog(QtWidgets.QDialog):
    """Dialog showing categorized push error with details."""

    def __init__(self, error_code, stderr, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Push Failed")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        self._error_code = error_code
        self._stderr = stderr

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        header_layout = QtWidgets.QHBoxLayout()
        icon_label = QtWidgets.QLabel()
        icon_label.setPixmap(
            self.style().standardIcon(
                QtWidgets.QStyle.SP_MessageBoxCritical
            ).pixmap(48, 48)
        )
        header_layout.addWidget(icon_label)

        message_label = QtWidgets.QLabel(
            self._friendly_message(error_code)
        )
        message_label.setWordWrap(True)
        header_layout.addWidget(message_label)

        layout.addLayout(header_layout)

        details_group = QtWidgets.QGroupBox("Details")
        details_layout = QtWidgets.QVBoxLayout()
        details_group.setLayout(details_layout)

        details_text = QtWidgets.QTextEdit()
        details_text.setReadOnly(True)
        details_text.setMaximumHeight(150)
        details_text.setText(self._stderr)
        details_text.setFont(QtGui.QFont("Courier", 9))
        details_layout.addWidget(details_text)

        copy_layout = QtWidgets.QHBoxLayout()
        copy_btn = QtWidgets.QPushButton("Copy Details")
        copy_btn.clicked.connect(self._on_copy_details)
        copy_layout.addWidget(copy_btn)
        copy_layout.addStretch()
        details_layout.addLayout(copy_layout)

        layout.addWidget(details_group)

        close_layout = QtWidgets.QHBoxLayout()
        close_layout.addStretch()
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)

    def _friendly_message(self, code):
        """Return user-friendly message for error code."""
        if code == "AUTH_OR_PERMISSION":
            return (
                "Authentication or permission issue.\n\n"
                "Sign in via GitHub Desktop, then try again."
            )
        if code == "NO_UPSTREAM":
            return (
                "No upstream branch set.\n\n"
                "Push should auto-detect this, but upstream may be needed."
            )
        if code == "NO_REMOTE":
            return "Remote not found. Check remote config and network."
        if code == "REJECTED":
            return (
                "Push rejected. You may need to pull first.\n\n"
                "Consider Pull before Push."
            )
        if code == "TIMEOUT":
            return (
                "Push timed out (>3 minutes). Check connection and retry."
            )
        return "Push failed due to an unexpected error. Check details."

    def _on_copy_details(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self._stderr)
        log.info("Push error details copied to clipboard")


class NewBranchDialog(QtWidgets.QDialog):
    """Dialog for creating a new branch."""

    def __init__(self, parent=None, default_start_point="HEAD", open_docs=None, lock_files=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Branch")
        self.setModal(True)
        self.setMinimumWidth(400)

        self.branch_name = ""
        self.start_point = default_start_point
        self._open_docs = open_docs or []
        self._lock_files = lock_files or []
        self._has_open_files = bool(self._open_docs or self._lock_files)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Warning if files are open
        if self._has_open_files:
            warning_frame = QtWidgets.QFrame()
            warning_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
            warning_frame.setStyleSheet(
                "QFrame { background-color: #fff3cd; border: 1px solid #ffc107; "
                "border-radius: 4px; padding: 8px; }"
            )
            warning_layout = QtWidgets.QVBoxLayout()
            warning_frame.setLayout(warning_layout)
            
            warning_icon_label = QtWidgets.QLabel("⚠️  Files Must Be Closed")
            warning_icon_label.setStyleSheet("font-weight: bold; color: #856404;")
            warning_layout.addWidget(warning_icon_label)
            
            warning_text = QtWidgets.QLabel(
                "CRITICAL: Git operations can corrupt .FCStd files that are open in FreeCAD!\n\n"
                "All FreeCAD documents must be closed before creating and switching to a new branch. "
                "This includes files from other worktrees or folders.\n\n"
                "Please close ALL FreeCAD files (File -> Close All) before proceeding:"
            )
            warning_text.setWordWrap(True)
            warning_text.setStyleSheet("color: #856404;")
            warning_layout.addWidget(warning_text)
            
            # List open files
            files_text = ""
            if self._open_docs:
                files_text += "Open documents:\n"
                for doc in self._open_docs[:5]:
                    import os
                    files_text += f"  • {os.path.basename(doc)}\n"
                if len(self._open_docs) > 5:
                    files_text += f"  ... and {len(self._open_docs) - 5} more\n"
            
            if self._lock_files:
                if files_text:
                    files_text += "\n"
                files_text += "Lock files detected:\n"
                for lock in self._lock_files[:5]:
                    import os
                    files_text += f"  • {os.path.basename(lock)}\n"
                if len(self._lock_files) > 5:
                    files_text += f"  ... and {len(self._lock_files) - 5} more\n"
            
            files_label = QtWidgets.QLabel(files_text.strip())
            files_label.setStyleSheet(
                "font-family: monospace; font-size: 9px; color: #856404; "
                "background-color: #fffbf0; padding: 4px; border-radius: 2px;"
            )
            warning_layout.addWidget(files_label)
            
            layout.addWidget(warning_frame)

        # Branch name
        name_layout = QtWidgets.QFormLayout()
        name_layout.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.ExpandingFieldsGrow
        )
        
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("e.g., feature/my-feature")
        self.name_edit.textChanged.connect(self._on_name_changed)
        name_layout.addRow("Branch name:", self.name_edit)
        
        layout.addLayout(name_layout)

        # Start point
        start_layout = QtWidgets.QFormLayout()
        start_layout.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.ExpandingFieldsGrow
        )
        
        self.start_edit = QtWidgets.QLineEdit()
        self.start_edit.setText(default_start_point)
        start_layout.addRow("Start point:", self.start_edit)
        
        layout.addLayout(start_layout)

        # Info label
        info_label = QtWidgets.QLabel(
            "The new branch will be created from the specified start point\n"
            "and you will be automatically switched to it.\n"
            "(e.g., origin/main, HEAD, or a specific commit)."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 9px;")
        layout.addWidget(info_label)

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.ok_button = button_box.button(QtWidgets.QDialogButtonBox.Ok)
        self.ok_button.setEnabled(False)

        self.name_edit.setFocus()
        
        # Update button state based on initial conditions
        self._on_name_changed()

    def _on_name_changed(self):
        """Enable OK button only if name is not empty AND no files are open."""
        has_name = bool(self.name_edit.text().strip())
        # OK button is only enabled if there's a name AND no files are open
        self.ok_button.setEnabled(has_name and not self._has_open_files)

    def _on_accept(self):
        """Handle OK button click."""
        self.branch_name = self.name_edit.text().strip()
        self.start_point = self.start_edit.text().strip()
        if not self.start_point:
            self.start_point = "HEAD"
        self.accept()


__all__ = [
    "UncommittedChangesWarningDialog",
    "PullErrorDialog",
    "PushErrorDialog",
    "NewBranchDialog",
]

