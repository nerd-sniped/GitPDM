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
            "Neither PySide6 nor PySide2 found. FreeCAD installation may be incomplete."
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
            self.style()
            .standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
            .pixmap(40, 40)
        )
        main_layout.addWidget(icon)

        message = QtWidgets.QLabel(
            "You have unsaved changes in your project.\n\n"
            "Getting updates from your team might not work until you save or undo your changes.\n\n"
            "What would you like to do?"
        )
        message.setWordWrap(True)
        main_layout.addWidget(message)

        layout.addLayout(main_layout)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QtWidgets.QPushButton("Go Back")
        cancel_btn.setDefault(True)
        cancel_btn.setToolTip("Return to the main panel to save your changes first")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        continue_btn = QtWidgets.QPushButton("Try Anyway")
        continue_btn.setToolTip("Attempt to get updates anyway (may not work)")
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
        self.setWindowTitle("Couldn't Get Updates")
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
            self.style()
            .standardIcon(QtWidgets.QStyle.SP_MessageBoxCritical)
            .pixmap(48, 48)
        )
        header_layout.addWidget(icon_label)

        message_label = QtWidgets.QLabel(self._friendly_message(error_code))
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
                "Can't get updates right now\n\n"
                "You have unsaved work that would be overwritten.\n\n"
                "Next steps:\n"
                "1. Go back to the panel\n"
                "2. Save your changes (use 'Save & Share' button)\n"
                "3. Then try getting updates again"
            )
        if code == "DIVERGED_OR_NON_FF":
            return (
                "Your version and your team's version are different\n\n"
                "Both you and your teammates have made changes.\n\n"
                "How to fix this:\n"
                "Option 1 (Easiest): Ask a team member who knows Git for help\n\n"
                "Option 2: Use GitHub Desktop\n"
                " 1. Open GitHub Desktop\n"
                " 2. Select your project\n"
                " 3. Click 'Fetch origin' then 'Pull origin'\n"
                " 4. If conflicts appear, GitHub Desktop will help you resolve them\n"
                " 5. Come back here and click 'Check for Updates'"
            )
        if code == "AUTH_OR_PERMISSION":
            return (
                "Can't access GitHub right now\n\n"
                "This could mean:\n"
                "\u2022 You need to sign in to GitHub again\n"
                "\u2022 You don't have permission to access this project\n"
                "\u2022 Your internet connection is down\n\n"
                "Try:\n"
                "1. Check your internet connection\n"
                "2. Click 'Verify / Refresh Account' in the GitHub section\n"
                "3. If that doesn't work, disconnect and reconnect GitHub"
            )
        return (
            "Something went wrong\n\n"
            "We couldn't get updates from GitHub.\n\n"
            "Try:\n"
            "\u2022 Check your internet connection\n"
            "\u2022 Make sure you're signed in to GitHub\n"
            "\u2022 Click 'Check for Updates' to try again\n\n"
            "If this keeps happening, you might need help from someone \n"
            "familiar with Git. Technical details are shown below."
        )

    def _on_copy_details(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self._stderr)
        log.info("Pull error details copied to clipboard")


class PushErrorDialog(QtWidgets.QDialog):
    """Dialog showing categorized push error with details."""

    def __init__(self, error_code, stderr, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Couldn't Share Changes")
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
            self.style()
            .standardIcon(QtWidgets.QStyle.SP_MessageBoxCritical)
            .pixmap(48, 48)
        )
        header_layout.addWidget(icon_label)

        message_label = QtWidgets.QLabel(self._friendly_message(error_code))
        message_label.setWordWrap(True)
        header_layout.addWidget(message_label)

        layout.addLayout(header_layout)

        details_group = QtWidgets.QGroupBox("Technical Details (for troubleshooting)")
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
        copy_btn.setToolTip("Copy technical details to share with someone who can help")
        copy_btn.clicked.connect(self._on_copy_details)
        copy_layout.addWidget(copy_btn)
        copy_layout.addStretch()
        details_layout.addLayout(copy_layout)

        layout.addWidget(details_group)

        close_layout = QtWidgets.QHBoxLayout()
        close_layout.addStretch()
        close_btn = QtWidgets.QPushButton("OK, I Understand")
        close_btn.setDefault(True)
        close_btn.setToolTip("Close this message and follow the steps above")
        close_btn.clicked.connect(self.accept)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)

    def _friendly_message(self, code):
        """Return user-friendly message for error code."""
        if code == "AUTH_OR_PERMISSION":
            return (
                "Can't access GitHub right now\n\n"
                "This could mean:\n"
                "\u2022 You need to sign in to GitHub again\n"
                "\u2022 You don't have permission to share to this project\n"
                "\u2022 Your internet connection is down\n\n"
                "Try:\n"
                "1. Check your internet connection\n"
                "2. Click 'Verify / Refresh Account' in the GitHub section\n"
                "3. If that doesn't work, disconnect and reconnect GitHub"
            )
        if code == "NO_UPSTREAM":
            return (
                "Your work version isn't connected to GitHub yet\n\n"
                "This usually fixes itself automatically.\n\n"
                "If the error keeps happening, try clicking 'Check for Updates'\n"
                "first, then try sharing again."
            )
        if code == "NO_REMOTE":
            return (
                "Can't find GitHub connection\n\n"
                "Your project might not be connected to GitHub, or there's\n"
                "a network problem.\n\n"
                "Try:\n"
                "\u2022 Check your internet connection\n"
                "\u2022 Make sure this project is connected to GitHub\n"
                "\u2022 Ask someone familiar with Git for help"
            )
        if code == "REJECTED":
            return (
                "Your team has made changes you don't have yet\n\n"
                "Before sharing your changes, you need to get your team's\n"
                "changes first.\n\n"
                "What to do:\n"
                "1. Click 'Check for Updates'\n"
                "2. If there are updates, click 'Get Updates'\n"
                "3. Then try sharing again"
            )
        if code == "TIMEOUT":
            return (
                "This is taking too long\n\n"
                "Sharing changes is taking more than 3 minutes.\n\n"
                "Try:\n"
                "\u2022 Check your internet connection\n"
                "\u2022 Try again in a few minutes\n"
                "\u2022 If it keeps failing, your files might be very large"
            )
        return (
            "Something went wrong\n\n"
            "We couldn't share your changes to GitHub.\n\n"
            "Try:\n"
            "\u2022 Check your internet connection\n"
            "\u2022 Make sure you're signed in to GitHub\n"
            "\u2022 Try sharing again\n\n"
            "If this keeps happening, you might need help from someone\n"
            "familiar with Git. Technical details are shown below."
        )

    def _on_copy_details(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self._stderr)
        log.info("Push error details copied to clipboard")


class NewBranchDialog(QtWidgets.QDialog):
    """Dialog for creating a new branch."""

    def __init__(
        self, parent=None, default_start_point="HEAD", open_docs=None, lock_files=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Create New Work Version")
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

            warning_icon_label = QtWidgets.QLabel(
                "⚠️  Please Close All FreeCAD Files First"
            )
            warning_icon_label.setStyleSheet("font-weight: bold; color: #856404;")
            warning_layout.addWidget(warning_icon_label)

            warning_text = QtWidgets.QLabel(
                "<b>Why?</b> Creating a new work version while files are open can corrupt your FreeCAD files!\n\n"
                "<b>What to do:</b>\n"
                "1. Go to File → Close All\n"
                "2. Make sure ALL FreeCAD documents are closed\n"
                "3. Come back here and try again\n\n"
                "<b>Important:</b> This includes files from any folder, not just this project.\n\n"
                "These files are currently open:"
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
        name_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)

        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("e.g., wheel-redesign or version-2.0")
        self.name_edit.setToolTip(
            "Give this work version a descriptive name\n"
            "Good names: wheel-redesign, lightweight-version, final-design\n"
            "Avoid spaces - use dashes instead\n\n"
            "Git term: 'branch name' - identifies this line of development"
        )
        self.name_edit.textChanged.connect(self._on_name_changed)
        name_layout.addRow("Version name:", self.name_edit)

        layout.addLayout(name_layout)

        # Start point
        start_layout = QtWidgets.QFormLayout()
        start_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)

        self.start_edit = QtWidgets.QLineEdit()
        self.start_edit.setText(default_start_point)
        self.start_edit.setToolTip(
            "Which version to start from (usually the main/latest version)\n"
            "Most of the time you can leave this as-is\n\n"
            "Git term: 'start point' or 'base branch' - where to branch from"
        )
        start_layout.addRow("Starting from:", self.start_edit)

        layout.addLayout(start_layout)

        # Info label
        info_label = QtWidgets.QLabel(
            "<b>What happens next:</b>\n"
            "1. A new work version will be created\n"
            "2. You'll automatically switch to working on this new version\n"
            "3. Your files will stay exactly as they are\n\n"
            "<i>Think of this like creating a new save file where you can try different ideas "
            "without affecting your original work.</i>\n\n"
            "<i>Git terms: This creates and checks out a new 'branch'</i>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #555; font-size: 9px;")
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
