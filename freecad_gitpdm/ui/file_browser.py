# -*- coding: utf-8 -*-
"""
File Browser Handler Module
Sprint 4: Extracted from panel.py to manage repository file browsing.
"""

# Qt compatibility layer
try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError as e:
        raise ImportError(
            "Neither PySide6 nor PySide2 found. FreeCAD installation may be incomplete."
        ) from e

import os
import sys
import subprocess as sp
import json
from pathlib import Path

from freecad_gitpdm.core import log, paths as core_paths
from freecad_gitpdm.export import mapper


class FileBrowserHandler:
    """
    Handles repository file browser functionality.

    Manages:
    - File listing from git (ls-files)
    - File searching/filtering
    - File preview display
    - File opening in FreeCAD
    - Context menu operations
    - Browser UI state
    """

    def __init__(self, parent, git_client, job_runner):
        """
        Initialize file browser handler.

        Args:
            parent: GitPDMDockWidget - parent panel with UI widgets
            git_client: GitClient - for git operations
            job_runner: JobRunner - for background operations
        """
        self._parent = parent
        self._git_client = git_client
        self._job_runner = job_runner

        # Browser state
        self._all_cad_files = []
        self._is_listing_files = False
        self._browser_dock = None
        self._browser_content = None
        self._current_backup_file = (
            None  # Track currently selected file for backup config
        )

    # ========== Public API ==========

    def create_browser_content(self):
        """Create the shared browser content widget once."""
        if self._browser_content:
            return self._browser_content

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        container.setLayout(layout)

        # Add branch/worktree indicator at top
        self._parent.repo_branch_indicator = QtWidgets.QLabel("—")
        self._parent.repo_branch_indicator.setWordWrap(True)
        self._parent.repo_branch_indicator.setStyleSheet(
            "font-weight: bold; padding: 4px;"
        )
        self._parent.repo_branch_indicator.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._parent.repo_branch_indicator.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(self._parent.repo_branch_indicator)

        self._parent.repo_info_label = QtWidgets.QLabel("Repo not selected.")
        self._parent.repo_info_label.setWordWrap(True)
        self._parent.repo_info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self._parent.repo_info_label)

        # Backup configuration panel (shown when FCStd file is selected)
        self._parent.backup_config_panel = QtWidgets.QFrame()
        backup_layout = QtWidgets.QVBoxLayout()
        backup_layout.setContentsMargins(8, 6, 8, 6)
        backup_layout.setSpacing(6)
        self._parent.backup_config_panel.setLayout(backup_layout)
        # Use styled panel to inherit theme colors
        self._parent.backup_config_panel.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._parent.backup_config_panel.setFrameShadow(QtWidgets.QFrame.Raised)

        # Title
        backup_title = QtWidgets.QLabel("📦 Backup Settings")
        backup_title.setStyleSheet("font-weight: bold;")
        backup_layout.addWidget(backup_title)

        # Controls row
        controls_row = QtWidgets.QHBoxLayout()
        controls_row.setSpacing(8)

        # Unlimited checkbox
        self._parent.backup_unlimited_checkbox = QtWidgets.QCheckBox("Keep all backups")
        self._parent.backup_unlimited_checkbox.setToolTip(
            "When checked, all backup files will be kept (no limit)"
        )
        self._parent.backup_unlimited_checkbox.stateChanged.connect(
            self._on_backup_unlimited_changed
        )
        controls_row.addWidget(self._parent.backup_unlimited_checkbox)

        controls_row.addStretch()

        # Max backups label and spinbox
        self._parent.backup_limit_label = QtWidgets.QLabel("Max backups:")
        controls_row.addWidget(self._parent.backup_limit_label)

        self._parent.backup_spinbox = QtWidgets.QSpinBox()
        self._parent.backup_spinbox.setMinimum(0)
        self._parent.backup_spinbox.setMaximum(100)
        self._parent.backup_spinbox.setValue(3)
        self._parent.backup_spinbox.setToolTip(
            "Maximum number of timestamped backup files to keep.\n"
            "0 = No backups, 1-100 = Keep this many recent backups"
        )
        self._parent.backup_spinbox.setMinimumWidth(60)
        self._parent.backup_spinbox.valueChanged.connect(self._on_backup_limit_changed)
        controls_row.addWidget(self._parent.backup_spinbox)

        backup_layout.addLayout(controls_row)

        # Initially disabled until a FCStd file is selected
        self._parent.backup_config_panel.setEnabled(False)
        layout.addWidget(self._parent.backup_config_panel)

        top_row = QtWidgets.QHBoxLayout()
        self._parent.repo_search = QtWidgets.QLineEdit()
        self._parent.repo_search.setPlaceholderText("Filter files…")
        self._parent.repo_search.textChanged.connect(self._on_search_changed)
        top_row.addWidget(self._parent.repo_search)

        self._parent.repo_refresh_btn = QtWidgets.QPushButton("Refresh Files")
        self._parent.repo_refresh_btn.clicked.connect(self._on_refresh_clicked)
        top_row.addWidget(self._parent.repo_refresh_btn)
        layout.addLayout(top_row)

        self._parent.repo_list = QtWidgets.QListWidget()
        self._parent.repo_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._parent.repo_list.customContextMenuRequested.connect(
            self._on_list_context_menu
        )
        self._parent.repo_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._parent.repo_list.currentItemChanged.connect(self._on_item_selected)
        layout.addWidget(self._parent.repo_list)

        self._parent.repo_preview_label = QtWidgets.QLabel("Select a file to preview")
        self._parent.repo_preview_label.setAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )
        self._parent.repo_preview_label.setMinimumHeight(180)
        self._parent.repo_preview_label.setStyleSheet(
            "color: gray; border: 1px dashed #ccc;"
        )
        layout.addWidget(self._parent.repo_preview_label)

        # Initial disabled state
        self._parent.repo_search.setEnabled(False)
        self._parent.repo_refresh_btn.setEnabled(False)
        self._parent.repo_list.setEnabled(False)

        self._browser_content = container
        return container

    def ensure_browser_host(self):
        """Create the dockable browser host; fallback to floating if needed."""
        if self._browser_dock:
            return self._browser_dock

        content = self.create_browser_content()

        dock = QtWidgets.QDockWidget("Repository Browser", self._parent)
        dock.setObjectName("GitPDM_RepoBrowserDock")
        dock.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea
            | QtCore.Qt.RightDockWidgetArea
            | QtCore.Qt.BottomDockWidgetArea
        )
        dock.setFeatures(
            QtWidgets.QDockWidget.DockWidgetClosable
            | QtWidgets.QDockWidget.DockWidgetMovable
            | QtWidgets.QDockWidget.DockWidgetFloatable
        )
        dock.setWidget(content)

        main_window = None
        try:
            import FreeCADGui

            main_window = FreeCADGui.getMainWindow()
        except Exception:
            main_window = None

        if main_window:
            # Try to tab with the Model tree view for better integration
            # Try multiple possible names for the tree view dock
            tree_view = None
            for name in ["Tree view", "Model", "Combo View"]:
                tree_view = main_window.findChild(QtWidgets.QDockWidget, name)
                if tree_view:
                    break

            if tree_view:
                main_window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)
                main_window.tabifyDockWidget(tree_view, dock)
                # Keep tree view as the active tab by default
                tree_view.raise_()
            else:
                # Fallback: just add to left area
                main_window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)
        else:
            dock.setParent(self._parent)
            dock.setFloating(True)

        self._browser_dock = dock
        return dock

    def open_browser(self):
        """Show the dockable repository browser (dock or floating)."""
        dock = self.ensure_browser_host()
        dock.show()
        dock.raise_()
        dock.activateWindow()

    def clear_browser(self):
        """Reset repo browser UI to empty state."""
        self.ensure_browser_host()
        self._all_cad_files = []
        self._parent.repo_list.clear()
        self._parent.repo_info_label.setText("Repo not selected.")
        self._parent.repo_info_label.setStyleSheet("color: gray; font-style: italic;")
        self._parent.repo_branch_indicator.setText("—")
        self._parent.repo_search.setEnabled(False)
        self._parent.repo_refresh_btn.setEnabled(False)
        self._parent.repo_list.setEnabled(False)

    def refresh_files(self):
        """
        Load tracked CAD files asynchronously using git ls-files.
        Always uses self._parent._current_repo_root to ensure correct worktree/branch files.
        """
        self.ensure_browser_host()
        if not self._git_client.is_git_available():
            self._parent.repo_info_label.setText("Git not available.")
            self._parent.repo_info_label.setStyleSheet(
                "color: red; font-style: italic;"
            )
            self._parent.repo_branch_indicator.setText("—")
            self._parent.repo_search.setEnabled(False)
            self._parent.repo_refresh_btn.setEnabled(False)
            self._parent.repo_list.setEnabled(False)
            return

        if not self._parent._current_repo_root:
            self.clear_browser()
            return

        if self._is_listing_files or self._job_runner.is_busy():
            # Avoid overlapping jobs; user can re-click later
            return

        # Update branch/worktree indicator
        current_branch = self._git_client.current_branch(
            self._parent._current_repo_root
        )
        repo_name = os.path.basename(os.path.normpath(self._parent._current_repo_root))
        if current_branch:
            self._parent.repo_branch_indicator.setText(
                f"📂 {repo_name}  •  🌿 {current_branch}"
            )
        else:
            self._parent.repo_branch_indicator.setText(f"📂 {repo_name}")

        self._is_listing_files = True
        self._parent.repo_info_label.setText("Loading…")
        self._parent.repo_info_label.setStyleSheet("color: orange; font-style: italic;")
        self._parent.repo_search.setEnabled(False)
        self._parent.repo_refresh_btn.setEnabled(False)
        self._parent.repo_refresh_btn.setText("Loading…")
        self._parent.repo_list.setEnabled(False)
        self._parent.repo_list.clear()

        git_cmd = self._git_client._get_git_command()
        # CRITICAL: Always use self._parent._current_repo_root to list files from correct worktree
        args = [git_cmd, "-C", self._parent._current_repo_root, "ls-files", "-z"]

        log.info(
            f"Listing files from: {self._parent._current_repo_root} (branch: {current_branch})"
        )

        self._job_runner.run_job(
            "list_files",
            args,
            callback=self._on_list_files_finished,
        )

    def show_preview(self, rel):
        """Load and display preview PNG for the given repo-relative file."""
        try:
            if not hasattr(self._parent, "repo_preview_label"):
                return
            if not self._parent._current_repo_root:
                self.clear_preview()
                return
            rel = (rel or "").strip()
            if not rel:
                self.clear_preview()
                return

            preview_dir = mapper.to_preview_dir_rel(rel)
            # Extract part name from source path for consistent naming
            from pathlib import Path

            part_name = Path(rel).stem
            png_rel = preview_dir + f"{part_name}.png"
            abs_png = core_paths.safe_join_repo(
                self._parent._current_repo_root, png_rel
            )
            if not abs_png or not abs_png.exists():
                self._parent.repo_preview_label.setText("No preview found")
                self._parent.repo_preview_label.setPixmap(QtGui.QPixmap())
                return

            pix = QtGui.QPixmap(str(abs_png))
            if pix.isNull():
                self._parent.repo_preview_label.setText("Preview could not be loaded")
                self._parent.repo_preview_label.setPixmap(QtGui.QPixmap())
                return

            target = self._parent.repo_preview_label.size() - QtCore.QSize(8, 8)
            scaled = pix.scaled(
                max(16, target.width()),
                max(16, target.height()),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
            self._parent.repo_preview_label.setPixmap(scaled)
            self._parent.repo_preview_label.setText("")
        except Exception as e:
            log.warning(f"Failed to load preview: {e}")
            self._parent.repo_preview_label.setText("Preview error")
            self._parent.repo_preview_label.setPixmap(QtGui.QPixmap())

    def clear_preview(self):
        """Clear the preview image."""
        if hasattr(self._parent, "repo_preview_label"):
            self._parent.repo_preview_label.setPixmap(QtGui.QPixmap())
            self._parent.repo_preview_label.setText("Select a file to preview")
        QtCore.QTimer.singleShot(3000, self._parent._clear_status_message)

    # ========== Private Implementation ==========

    def _on_refresh_clicked(self):
        """Manual refresh of repo browser files."""
        self.ensure_browser_host()
        self.refresh_files()

    def _on_list_files_finished(self, job):
        """Process ls-files output and populate browser."""
        self.ensure_browser_host()
        self._is_listing_files = False

        result = job.get("result", {})
        success = result.get("success", False)
        stdout = result.get("stdout", "")

        self._parent.repo_refresh_btn.setText("Refresh Files")

        if not success:
            err = result.get("stderr", "")
            self._parent.repo_info_label.setText("Failed to list files.")
            self._parent.repo_info_label.setStyleSheet(
                "color: red; font-style: italic;"
            )
            log.warning(f"ls-files failed: {err}")
            self._parent.repo_search.setEnabled(True)
            self._parent.repo_refresh_btn.setEnabled(True)
            self._parent.repo_list.setEnabled(True)
            return

        # Parse NUL-separated entries
        tokens = [t for t in stdout.split("\0") if t]

        # Filter strictly to FreeCAD native files; the browser only opens .FCStd
        fcstd_set = []
        for p in tokens:
            name = p.rsplit("/", 1)[-1]
            name = name.rsplit("\\", 1)[-1]
            if name.lower().endswith(".fcstd"):
                fcstd_set.append(p)

        self._all_cad_files = fcstd_set
        self._apply_filter_and_populate()

        self._parent.repo_search.setEnabled(True)
        self._parent.repo_refresh_btn.setEnabled(True)
        self._parent.repo_list.setEnabled(True)

        if not self._all_cad_files:
            self._parent.repo_info_label.setText("No FCStd files found.")
            self._parent.repo_info_label.setStyleSheet(
                "color: gray; font-style: italic;"
            )
        else:
            self._parent.repo_info_label.setText(
                f"Found {len(self._all_cad_files)} FCStd files."
            )
            self._parent.repo_info_label.setStyleSheet(
                "color: #4db6ac; font-style: italic;"
            )

    def _on_search_changed(self, _text):
        """Filter list on search text change (in-memory)."""
        self.ensure_browser_host()
        self._apply_filter_and_populate()

    def _apply_filter_and_populate(self):
        """Apply filter and update list widget."""
        self.ensure_browser_host()
        self._parent.repo_list.clear()
        self.clear_preview()
        q = self._parent.repo_search.text().strip().lower()
        if not self._all_cad_files:
            return
        for rel in self._all_cad_files:
            if not q or q in rel.lower():
                self._parent.repo_list.addItem(rel)

    def _on_item_double_clicked(self, item):
        """Open double-clicked file if it's a .FCStd."""
        self.ensure_browser_host()
        rel = item.text()
        self._open_file(rel)

    def _on_item_selected(self, current, _previous):
        """Show preview for the selected repository item."""
        if not current:
            self.clear_preview()
            self._parent.backup_config_panel.setEnabled(False)
            return
        rel = current.text()
        self.show_preview(rel)

        # Enable backup config panel only for FCStd files
        if rel.lower().endswith(".fcstd"):
            self._load_backup_settings(rel)
            self._parent.backup_config_panel.setEnabled(True)
        else:
            self._parent.backup_config_panel.setEnabled(False)

    def _on_list_context_menu(self, pos):
        """Show context menu for repo list items."""
        self.ensure_browser_host()
        item = self._parent.repo_list.itemAt(pos)
        menu = QtWidgets.QMenu(self._parent)

        act_open = menu.addAction("Open")
        act_reveal = menu.addAction("Reveal in Explorer/Finder")
        act_copy = menu.addAction("Copy Relative Path")

        # Add configure backups option for FCStd files
        act_backups = None
        rel = item.text() if item else None
        if rel and rel.lower().endswith(".fcstd"):
            menu.addSeparator()
            act_backups = menu.addAction("Configure Backups...")
            
            # Add lock/unlock actions if GitCAD is available
            if hasattr(self._parent, '_gitcad_lock') and self._parent._gitcad_lock._gitcad_available:
                menu.addSeparator()
                lock_info = self._parent._gitcad_lock.get_file_lock_status(rel)
                
                if lock_info:
                    # File is locked
                    if self._parent._gitcad_lock.is_locked_by_me(rel):
                        act_unlock = menu.addAction("🔓 Unlock")
                    else:
                        act_force_lock = menu.addAction(f"🔒 Force Lock (locked by {lock_info.owner})")
                        act_unlock = None
                else:
                    # File is not locked
                    act_lock = menu.addAction("🔒 Lock")
                    act_unlock = None
                    act_force_lock = None
        else:
            act_lock = None
            act_unlock = None
            act_force_lock = None

        chosen = menu.exec_(self._parent.repo_list.mapToGlobal(pos))
        if not chosen:
            return

        if chosen == act_copy and rel:
            QtWidgets.QApplication.clipboard().setText(rel)
            return

        if not rel:
            return

        if chosen == act_open:
            self._open_file(rel)
        elif chosen == act_reveal:
            self._reveal_in_file_manager(rel)
        elif chosen == act_backups:
            self._configure_backups(rel)
        elif 'act_lock' in locals() and chosen == act_lock:
            self._parent._gitcad_lock.lock_file(rel, force=False)
        elif 'act_unlock' in locals() and act_unlock and chosen == act_unlock:
            self._parent._gitcad_lock.unlock_file(rel, force=False)
        elif 'act_force_lock' in locals() and act_force_lock and chosen == act_force_lock:
            # Confirm force lock
            reply = QtWidgets.QMessageBox.question(
                self._parent,
                "Force Lock",
                f"This file is locked by {lock_info.owner}.\n\n"
                f"Force locking will steal the lock from them.\n"
                f"This should only be done if they are not actively using the file.\n\n"
                f"Are you sure?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                self._parent._gitcad_lock.lock_file(rel, force=True)

    def _open_file(self, rel):
        """Open the given repo-relative path in FreeCAD."""
        self.ensure_browser_host()
        if not self._parent._current_repo_root:
            log.warning("Cannot open file: no repo root set")
            return

        abs_path = os.path.normpath(os.path.join(self._parent._current_repo_root, rel))

        # Log which file we're opening and from which root
        log.info(f"Opening file from repo browser: {rel}")
        log.info(f"  Absolute path: {abs_path}")
        log.info(f"  Current repo root: {self._parent._current_repo_root}")

        # Only allow opening FCStd files
        name = abs_path.rsplit("/", 1)[-1]
        name = name.rsplit("\\", 1)[-1]
        is_fcstd = name.lower().endswith(".fcstd")
        if not is_fcstd:
            msg = QtWidgets.QMessageBox(self._parent)
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setWindowTitle("Unsupported File Type")
            msg.setText("Only .FCStd files can be opened directly.")
            msg.exec()
            return

        if not os.path.isfile(abs_path):
            log.error(f"File does not exist: {abs_path}")
            msg = QtWidgets.QMessageBox(self._parent)
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle("File Missing")
            msg.setText("File not present in working tree. Try Pull/Fetch.")
            msg.exec()
            return

        # Show preview (if available) even before opening
        self.show_preview(rel)

        # Check for unsaved documents (MVP best-effort)
        try:
            import FreeCAD

            docs = FreeCAD.listDocuments()
            has_dirty = False
            for d in docs.values():
                # Document.Modified may exist; ignore if missing
                try:
                    if getattr(d, "Modified", False):
                        has_dirty = True
                        break
                except Exception:
                    pass
            if has_dirty:
                ask = QtWidgets.QMessageBox(self._parent)
                ask.setIcon(QtWidgets.QMessageBox.Warning)
                ask.setWindowTitle("Unsaved Changes")
                ask.setText("There are unsaved changes. Open another file?")
                ask.setStandardButtons(
                    QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Yes
                )
                res = ask.exec()
                if res != QtWidgets.QMessageBox.Yes:
                    return
        except Exception:
            # If FreeCAD API differs, proceed without blocking
            pass

        # Set working directory to repo folder before opening
        # This ensures "Save As" dialog defaults to the repo folder
        self._parent._set_freecad_working_directory(self._parent._current_repo_root)

        # Open document in FreeCAD
        try:
            import FreeCAD

            FreeCAD.open(abs_path)
            log.info(f"Opened file in FreeCAD: {abs_path}")

            # Re-confirm working directory after opening (some FreeCAD versions reset it)
            self._parent._set_freecad_working_directory(self._parent._current_repo_root)
        except Exception:
            try:
                import FreeCADGui

                FreeCADGui.open(abs_path)
                log.info(f"Opened file via FreeCADGui: {abs_path}")

                # Re-confirm working directory
                self._parent._set_freecad_working_directory(
                    self._parent._current_repo_root
                )
            except Exception as e:
                log.error(f"Failed to open file: {e}")
                msg = QtWidgets.QMessageBox(self._parent)
                msg.setIcon(QtWidgets.QMessageBox.Critical)
                msg.setWindowTitle("Open Failed")
                msg.setText("Could not open the file in FreeCAD.")
                msg.exec()

    def _reveal_in_file_manager(self, rel):
        """Reveal the file in the OS file manager (MVP)."""
        if not self._parent._current_repo_root:
            return

        abs_path = os.path.normpath(os.path.join(self._parent._current_repo_root, rel))
        folder = os.path.dirname(abs_path)

        if sys.platform.startswith("win"):
            try:
                os.startfile(folder)
            except Exception as e:
                log.error(f"Reveal failed: {e}")
        elif sys.platform == "darwin":
            try:
                sp.run(["open", "-R", abs_path], timeout=10)
            except Exception as e:
                log.error(f"Reveal failed: {e}")
        else:
            try:
                sp.run(["xdg-open", folder], timeout=10)
            except Exception as e:
                log.error(f"Reveal failed: {e}")

    def _configure_backups(self, rel):
        """Configure the maximum number of backups for a part."""
        if not self._parent._current_repo_root:
            return

        # Get the preview JSON path
        preview_rel = mapper.to_preview_dir_rel(rel)
        json_rel = preview_rel + "/" + Path(rel).stem + ".json"
        json_abs = core_paths.safe_join_repo(self._parent._current_repo_root, json_rel)

        # Load current maxBackups value
        current_max = 3  # Default
        if json_abs and json_abs.exists():
            try:
                data = json.loads(json_abs.read_text(encoding="utf-8"))
                current_max = data.get("maxBackups", 3)
            except Exception as e:
                log.warning(f"Failed to read maxBackups from JSON: {e}")

        # Show dialog to configure
        dialog = QtWidgets.QDialog(self._parent)
        dialog.setWindowTitle("Configure Backups")
        dialog.setModal(True)

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(12)

        # Info label
        info_label = QtWidgets.QLabel(
            f"Configure backup retention for:\n{Path(rel).name}\n\n"
            "Set the maximum number of timestamped backup files (.FCBak) to keep.\n"
            "Older backups beyond this limit will be automatically removed."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Input for max backups
        input_layout = QtWidgets.QHBoxLayout()
        input_label = QtWidgets.QLabel("Max Backups:")
        input_layout.addWidget(input_label)

        spinbox = QtWidgets.QSpinBox()
        spinbox.setMinimum(0)
        spinbox.setMaximum(100)
        spinbox.setValue(current_max)
        spinbox.setToolTip(
            "0 = No backups kept (FCBak files deleted)\n"
            "1-100 = Keep this many recent backups"
        )
        input_layout.addWidget(spinbox)
        input_layout.addStretch()
        layout.addLayout(input_layout)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QtWidgets.QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        # Execute dialog
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            new_max = spinbox.value()
            if json_abs and json_abs.exists():
                try:
                    # Update the JSON file
                    data = json.loads(json_abs.read_text(encoding="utf-8"))
                    data["maxBackups"] = new_max
                    json_text = json.dumps(
                        data,
                        sort_keys=True,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    json_abs.write_text(json_text, encoding="utf-8", newline="\n")
                    log.info(f"Updated maxBackups to {new_max} for {rel}")

                    # If backups already exist, trigger cleanup
                    backup_dir = json_abs.parent / "Backup"
                    if backup_dir.exists():
                        from freecad_gitpdm.export.backup_manager import (
                            cleanup_old_backups,
                        )

                        cleanup_old_backups(backup_dir, Path(rel).stem, new_max)

                    QtWidgets.QMessageBox.information(
                        self._parent,
                        "Backups Configured",
                        f"Maximum backups set to {new_max} for this part.\n"
                        "This will take effect on the next save.",
                    )
                except Exception as e:
                    log.error(f"Failed to update maxBackups: {e}")
                    QtWidgets.QMessageBox.warning(
                        self._parent,
                        "Configuration Failed",
                        f"Failed to update backup settings:\n{e}",
                    )
            else:
                QtWidgets.QMessageBox.information(
                    self._parent,
                    "No Preview Generated",
                    "Generate a preview for this part first.\n"
                    "The backup setting will be saved then.",
                )

    def _load_backup_settings(self, rel):
        """Load and display backup settings for the selected file."""
        if not self._parent._current_repo_root:
            return

        # Store current file for save operations
        self._current_backup_file = rel

        # Get the preview JSON path
        preview_rel = mapper.to_preview_dir_rel(rel)
        json_rel = preview_rel + "/" + Path(rel).stem + ".json"
        json_abs = core_paths.safe_join_repo(self._parent._current_repo_root, json_rel)

        # Load current maxBackups value
        max_backups = 3  # Default
        if json_abs and json_abs.exists():
            try:
                data = json.loads(json_abs.read_text(encoding="utf-8"))
                max_backups = data.get("maxBackups", 3)
            except Exception as e:
                log.warning(f"Failed to read maxBackups from JSON: {e}")

        # Block signals while updating UI
        self._parent.backup_spinbox.blockSignals(True)
        self._parent.backup_unlimited_checkbox.blockSignals(True)

        # Check if unlimited (represented as -1 or very high number)
        if max_backups == -1 or max_backups >= 999:
            self._parent.backup_unlimited_checkbox.setChecked(True)
            self._parent.backup_spinbox.setEnabled(False)
            self._parent.backup_limit_label.setEnabled(False)
            self._parent.backup_spinbox.setValue(10)  # Display value when unchecked
        else:
            self._parent.backup_unlimited_checkbox.setChecked(False)
            self._parent.backup_spinbox.setEnabled(True)
            self._parent.backup_limit_label.setEnabled(True)
            self._parent.backup_spinbox.setValue(max_backups)

        # Unblock signals
        self._parent.backup_spinbox.blockSignals(False)
        self._parent.backup_unlimited_checkbox.blockSignals(False)

    def _on_backup_unlimited_changed(self, state):
        """Handle unlimited backups checkbox change."""
        is_unlimited = state == QtCore.Qt.Checked

        # Enable/disable spinbox
        self._parent.backup_spinbox.setEnabled(not is_unlimited)
        self._parent.backup_limit_label.setEnabled(not is_unlimited)

        # Save the setting
        if hasattr(self, "_current_backup_file"):
            self._save_backup_setting(
                self._current_backup_file,
                -1 if is_unlimited else self._parent.backup_spinbox.value(),
            )

    def _on_backup_limit_changed(self, value):
        """Handle backup limit spinbox change."""
        if (
            hasattr(self, "_current_backup_file")
            and not self._parent.backup_unlimited_checkbox.isChecked()
        ):
            self._save_backup_setting(self._current_backup_file, value)

    def _save_backup_setting(self, rel, max_backups):
        """Save the backup setting to the JSON file."""
        if not self._parent._current_repo_root:
            return

        # Get the preview JSON path
        preview_rel = mapper.to_preview_dir_rel(rel)
        json_rel = preview_rel + "/" + Path(rel).stem + ".json"
        json_abs = core_paths.safe_join_repo(self._parent._current_repo_root, json_rel)

        if json_abs and json_abs.exists():
            try:
                # Update the JSON file
                data = json.loads(json_abs.read_text(encoding="utf-8"))
                data["maxBackups"] = max_backups
                json_text = json.dumps(
                    data,
                    sort_keys=True,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                json_abs.write_text(json_text, encoding="utf-8", newline="\n")

                if max_backups == -1:
                    log.info(f"Set unlimited backups for {rel}")
                else:
                    log.info(f"Updated maxBackups to {max_backups} for {rel}")

                # If backups already exist and we have a limit, trigger cleanup
                if max_backups > 0:
                    backup_dir = json_abs.parent / "Backup"
                    if backup_dir.exists():
                        from freecad_gitpdm.export.backup_manager import (
                            cleanup_old_backups,
                        )

                        cleanup_old_backups(backup_dir, Path(rel).stem, max_backups)
            except Exception as e:
                log.error(f"Failed to update maxBackups: {e}")
        else:
            log.debug(
                f"No preview JSON exists yet for {rel}, will use setting on next save"
            )
