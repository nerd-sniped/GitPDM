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


__all__ = [
    "UncommittedChangesWarningDialog",
    "PullErrorDialog",
    "PushErrorDialog",
]
