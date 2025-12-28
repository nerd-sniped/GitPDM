# -*- coding: utf-8 -*-
"""
Repository picker dialog for GitPDM.
Sprint OAUTH-3: List GitHub repos and clone asynchronously.
"""

from __future__ import annotations

import os
from typing import Callable, List, Optional

# Qt compatibility layer - try PySide6 first, then PySide2
try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "Neither PySide6 nor PySide2 found. "
            "FreeCAD installation may be incomplete."
        ) from e

from freecad_gitpdm.core import log, settings, jobs
from freecad_gitpdm.git.client import GitClient
from freecad_gitpdm.github.repos import RepoInfo, list_repos
from freecad_gitpdm.github.api_client import (
    GitHubApiClient,
    GitHubApiError,
    GitHubApiNetworkError,
)


class RepoPickerDialog(QtWidgets.QDialog):
    """Dialog to browse GitHub repositories and clone one."""

    def __init__(
        self,
        parent=None,
        job_runner=None,
        git_client: Optional[GitClient] = None,
        client_factory: Optional[Callable[[], Optional[GitHubApiClient]]] = None,
        on_connect_requested: Optional[Callable[[], None]] = None,
        default_clone_dir: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle("Open / Clone Repository")
        self.setMinimumSize(540, 420)
        self.setModal(True)

        self._job_runner = job_runner or jobs.get_job_runner()
        self._git_client = git_client or GitClient()
        self._client_factory = client_factory
        self._on_connect_requested = on_connect_requested
        self._repos: List[RepoInfo] = []
        self._visible_repos: List[RepoInfo] = []
        self._cloned_path: Optional[str] = None
        self._selected_repo: Optional[RepoInfo] = None
        self._is_loading = False
        self._default_clone_dir = default_clone_dir or settings.load_default_clone_dir()

        self._build_ui()
        QtCore.QTimer.singleShot(50, self._refresh_repos)

    # --- Public getters ---

    def cloned_path(self) -> Optional[str]:
        return self._cloned_path

    def selected_repo(self) -> Optional[RepoInfo]:
        return self._selected_repo

    # --- UI construction ---

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        self.setLayout(layout)

        self._connect_message = QtWidgets.QLabel(
            "Sign in to GitHub to list repositories."
        )
        self._connect_message.setStyleSheet(
            "color: gray; font-style: italic;"
        )
        self._connect_message.hide()
        layout.addWidget(self._connect_message)

        self._connect_btn = QtWidgets.QPushButton("Connect GitHub")
        self._connect_btn.clicked.connect(self._on_connect_clicked)
        self._connect_btn.hide()
        layout.addWidget(self._connect_btn)

        search_row = QtWidgets.QHBoxLayout()
        search_row.setSpacing(6)
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search repositories…")
        self.search_box.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search_box)

        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_repos)
        search_row.addWidget(self.refresh_btn)
        layout.addLayout(search_row)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Repository", "Visibility", "Updated"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.doubleClicked.connect(self._on_clone_clicked)
        layout.addWidget(self.table)

        self.status_label = QtWidgets.QLabel("Loading…")
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        self.clone_btn = QtWidgets.QPushButton("Clone")
        self.clone_btn.setEnabled(False)
        self.clone_btn.clicked.connect(self._on_clone_clicked)
        btn_row.addWidget(self.clone_btn)

        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)

    # --- Data loading ---

    def _ensure_client(self) -> Optional[GitHubApiClient]:
        try:
            if self._client_factory:
                return self._client_factory()
        except Exception as e:
            log.debug(f"Repo picker could not create client: {e}")
        return None

    def _refresh_repos(self):
        if self._is_loading:
            return

        client = self._ensure_client()
        if client is None:
            self._show_connect_prompt()
            return

        self._hide_connect_prompt()
        self._set_loading_state(True, "Loading…")

        self._job_runner.run_callable(
            "github_list_repos",
            lambda: list_repos(client, per_page=100, max_pages=10),
            on_success=self._on_repos_loaded,
            on_error=self._on_repos_error,
        )

    def _on_repos_loaded(self, repo_list: List[RepoInfo]):
        self._repos = repo_list or []
        self._apply_filter()
        count = len(self._repos)
        self.status_label.setText(f"Loaded {count} repositories")
        self.status_label.setStyleSheet("color: gray;")
        self._set_loading_state(False)

    def _on_repos_error(self, error: Exception):
        msg = "Failed to load repositories."
        if isinstance(error, GitHubApiNetworkError):
            msg = "Network error. Check connection and try again."
        elif isinstance(error, GitHubApiError):
            msg = str(error)
        log.warning(f"Repo picker load error: {msg}")
        self.status_label.setText(msg)
        self.status_label.setStyleSheet("color: red;")
        self._set_loading_state(False)

    def _apply_filter(self):
        term = self.search_box.text().strip().lower()
        if not term:
            filtered = self._repos
        else:
            filtered = [r for r in self._repos if term in (r.full_name or "").lower()]
        self._visible_repos = filtered
        self._populate_table(filtered)
        self.status_label.setText(f"Showing {len(filtered)} of {len(self._repos)}")
        self.status_label.setStyleSheet("color: gray;")

    def _populate_table(self, repos: List[RepoInfo]):
        self.table.setRowCount(len(repos))
        for idx, repo in enumerate(repos):
            repo_item = QtWidgets.QTableWidgetItem(repo.full_name)
            vis_text = "Private" if repo.private else "Public"
            vis_item = QtWidgets.QTableWidgetItem(vis_text)
            vis_item.setForeground(QtGui.QBrush(QtGui.QColor("#c62828" if repo.private else "#2e7d32")))
            updated_item = QtWidgets.QTableWidgetItem(repo.updated_at or "")

            repo_item.setFlags(repo_item.flags() ^ QtCore.Qt.ItemIsEditable)
            vis_item.setFlags(vis_item.flags() ^ QtCore.Qt.ItemIsEditable)
            updated_item.setFlags(updated_item.flags() ^ QtCore.Qt.ItemIsEditable)

            self.table.setItem(idx, 0, repo_item)
            self.table.setItem(idx, 1, vis_item)
            self.table.setItem(idx, 2, updated_item)

    # --- Selection / clone ---

    def _selected_repo_from_table(self) -> Optional[RepoInfo]:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        if row < 0 or row >= len(self._visible_repos):
            return None
        return self._visible_repos[row]

    def _on_selection_changed(self):
        self.clone_btn.setEnabled(bool(self._selected_repo_from_table()) and not self._is_loading)

    def _on_clone_clicked(self):
        if self._is_loading:
            return
        repo = self._selected_repo_from_table()
        if not repo:
            return

        dest_path = self._ask_destination(repo)
        if not dest_path:
            return

        self._start_clone(repo, dest_path)

    def _ask_destination(self, repo: RepoInfo) -> Optional[str]:
        base_dir = self._default_clone_dir or os.path.expanduser("~")
        chosen = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Choose clone destination",
            base_dir,
            QtWidgets.QFileDialog.ShowDirsOnly,
        )
        if not chosen:
            return None

        self._default_clone_dir = chosen
        settings.save_default_clone_dir(chosen)

        dest_path = os.path.join(chosen, repo.name)
        if os.path.isdir(dest_path):
            try:
                if os.listdir(dest_path):
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Destination Not Empty",
                        "Selected folder already exists and is not empty.\nChoose a different location.",
                    )
                    return None
            except OSError:
                pass
        return dest_path

    def _start_clone(self, repo: RepoInfo, dest_path: str):
        git_cmd = self._git_client._get_git_command()
        if not git_cmd:
            QtWidgets.QMessageBox.critical(
                self,
                "Git Not Found",
                "Git is not available. Install Git or GitHub Desktop and retry.",
            )
            return

        self._selected_repo = repo
        self._set_loading_state(True, "Cloning…")
        args = [git_cmd, "clone", repo.clone_url, dest_path]

        self._job_runner.run_job(
            "clone_repo",
            args,
            callback=lambda job: self._on_clone_finished(job, repo, dest_path),
        )

    def _on_clone_finished(self, job, repo: RepoInfo, dest_path: str):
        result = job.get("result", {}) if isinstance(job, dict) else {}
        success = result.get("success", False)
        stderr = result.get("stderr", "")

        if success:
            self._cloned_path = dest_path
            self.status_label.setText(f"Cloned {repo.full_name} → {dest_path}")
            self.status_label.setStyleSheet("color: green;")
            self._set_loading_state(False)
            self.accept()
            return

        message = "Clone failed."
        stderr_lower = stderr.lower()
        if "authentication" in stderr_lower:
            message = (
                "Authentication failed. Complete the Git Credential Manager prompt "
                "or sign in when Windows asks."
            )
        elif "not found" in stderr_lower or "repository" in stderr_lower:
            message = "Repository not found or access denied."
        QtWidgets.QMessageBox.warning(self, "Clone Failed", f"{message}\n\nDetails:\n{stderr}")
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: red;")
        self._set_loading_state(False)

    # --- Helpers ---

    def _show_connect_prompt(self):
        self._connect_message.show()
        self._connect_btn.show()
        self.table.setRowCount(0)
        self.clone_btn.setEnabled(False)
        self.status_label.setText("Connect to GitHub to list repos")
        self.status_label.setStyleSheet("color: gray;")
        self._is_loading = False
        self.search_box.setEnabled(False)
        self.refresh_btn.setEnabled(True)

    def _hide_connect_prompt(self):
        self._connect_message.hide()
        self._connect_btn.hide()
        self.search_box.setEnabled(True)

    def _on_connect_clicked(self):
        if self._on_connect_requested:
            self._on_connect_requested()
        else:
            QtWidgets.QMessageBox.information(
                self,
                "Connect GitHub",
                "Use the GitHub Account section to sign in, then click Refresh.",
            )

    def _set_loading_state(self, loading: bool, message: Optional[str] = None):
        self._is_loading = loading
        self.refresh_btn.setEnabled(not loading)
        self.clone_btn.setEnabled(not loading and bool(self._selected_repo_from_table()))
        self.search_box.setEnabled(not loading)
        if message:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: orange; font-style: italic;")