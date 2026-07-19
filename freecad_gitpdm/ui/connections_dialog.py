# -*- coding: utf-8 -*-
"""
GitPDM Connections Dialog

Houses the GitHub Account and Other Git Hosts (GitLab/Bitbucket/Gitea-
Forgejo/SourceHut PAT-paste) sections that used to be built inline in the
main dock panel's sidebar. Relocated here as part of the bottom-dock UI
simplification: credentials are "dense information ... you don't touch
nearly as often", reachable from the GitPDM menu instead of always-on-screen.

Opened non-modally and constructed eagerly (hidden) alongside the main
panel, so GitHubAuthHandler/PatAuthHandler's startup checks
(refresh_connection_status, maybe_auto_verify_identity) keep updating real
widgets regardless of whether this dialog is currently visible -- identical
to how those checks behaved when the sections lived inline in the panel.
"""

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtWidgets
    except ImportError as e:
        raise ImportError(
            "Neither PySide6 nor PySide2 found. FreeCAD installation may be incomplete."
        ) from e

from freecad_gitpdm.core import log, settings
from freecad_gitpdm.ui import label_style
from freecad_gitpdm.ui.github_auth import GitHubAuthHandler
from freecad_gitpdm.ui.pat_auth import PatAuthHandler


class ConnectionsDialog(QtWidgets.QDialog):
    """Standalone dialog for GitHub + other-host connection management."""

    def __init__(self, panel, services):
        super().__init__(panel)
        self._panel = panel
        self._services = services
        self._git_client = services.git_client()
        self._job_runner = services.job_runner()

        self.setWindowTitle("GitPDM Connections")
        self.setMinimumWidth(420)

        self._github_auth = GitHubAuthHandler(self, services)
        self._pat_auth = PatAuthHandler(self, services)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.setLayout(layout)

        self._build_github_account_section(layout)
        self._build_other_hosts_section(layout)
        self._build_checkpointing_section(layout)

        close_row = QtWidgets.QHBoxLayout()
        close_row.addStretch()
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    def _set_strong_label(self, label, color="black"):
        label_style.set_strong_label(label, color)

    def _set_meta_label(self, label, color="gray"):
        label_style.set_meta_label(label, color)

    # ========== GitHub Account section ==========

    def _build_github_account_section(self, layout):
        """
        Build the GitHub Account section (Sprint OAUTH-1)
        Shows connection status and connect/disconnect buttons.
        Implements OAuth Device Flow workflow.
        """
        group = QtWidgets.QGroupBox("GitHub Account")
        group_layout = QtWidgets.QVBoxLayout()
        group_layout.setContentsMargins(6, 4, 6, 4)
        group_layout.setSpacing(4)
        group.setLayout(group_layout)

        self.github_status_label = QtWidgets.QLabel("GitHub: Not connected")
        self._set_strong_label(self.github_status_label, "gray")
        group_layout.addWidget(self.github_status_label)

        try:
            from freecad_gitpdm.auth import config as auth_config

            client_id = auth_config.get_client_id()
            oauth_configured = client_id is not None
        except Exception:
            oauth_configured = False

        if not oauth_configured:
            hint_label = QtWidgets.QLabel("GitHub OAuth not configured. See docs.")
            hint_label.setWordWrap(True)
            hint_label.setStyleSheet(
                "color: orange; font-style: italic; font-size: 9px;"
            )
            group_layout.addWidget(hint_label)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setSpacing(4)

        self.github_connect_btn = QtWidgets.QPushButton("Connect GitHub")
        self.github_connect_btn.setEnabled(oauth_configured)
        self.github_connect_btn.setToolTip(
            "Connect to GitHub using OAuth Device Flow"
            if oauth_configured
            else "OAuth not configured"
        )
        self.github_connect_btn.clicked.connect(self._on_github_connect_clicked)
        buttons_layout.addWidget(self.github_connect_btn)

        self.github_disconnect_btn = QtWidgets.QPushButton("Disconnect")
        self.github_disconnect_btn.setEnabled(False)
        self.github_disconnect_btn.setToolTip("Disconnect GitHub account")
        self.github_disconnect_btn.clicked.connect(self._on_github_disconnect_clicked)
        buttons_layout.addWidget(self.github_disconnect_btn)

        self.github_refresh_btn = QtWidgets.QPushButton("Verify / Refresh Account")
        self.github_refresh_btn.setEnabled(oauth_configured)
        self.github_refresh_btn.setToolTip("Verify GitHub account and refresh session")
        self.github_refresh_btn.clicked.connect(self._on_github_verify_clicked)
        buttons_layout.addWidget(self.github_refresh_btn)

        group_layout.addLayout(buttons_layout)

        layout.addWidget(group)
        self._group_github_account = group

    def _on_github_connect_clicked(self):
        self._github_auth.connect_clicked()

    def _on_github_disconnect_clicked(self):
        self._github_auth.disconnect_clicked()

    def _on_github_verify_clicked(self):
        self._github_auth.verify_clicked()

    # ========== Other Git Hosts section ==========

    def _build_other_hosts_section(self, layout):
        """
        Build the "Other Git Hosts" section: one consolidated PAT-connect
        UI for GitLab/Bitbucket/Gitea-Forgejo/SourceHut, rather than four
        more GitHub-style sections (device-flow specific, would balloon
        this file). GitHub keeps its own dedicated section above - it
        authenticates differently (OAuth device flow) and predates this.
        """
        group = QtWidgets.QGroupBox("Other Git Hosts")
        group_layout = QtWidgets.QVBoxLayout()
        group_layout.setContentsMargins(6, 4, 6, 4)
        group_layout.setSpacing(4)
        group.setLayout(group_layout)

        from freecad_gitpdm.providers import list_provider_ids, get_provider_class

        self._other_host_ids = sorted(
            pid for pid in list_provider_ids() if pid not in ("github", "generic")
        )

        picker_row = QtWidgets.QHBoxLayout()
        picker_row.setSpacing(4)
        picker_row.addWidget(QtWidgets.QLabel("Host:"))
        self.other_hosts_combo = QtWidgets.QComboBox()
        for provider_id in self._other_host_ids:
            provider_cls = get_provider_class(provider_id)
            self.other_hosts_combo.addItem(
                provider_cls.display_name or provider_id, provider_id
            )
        self.other_hosts_combo.currentIndexChanged.connect(
            self._on_other_hosts_provider_changed
        )
        picker_row.addWidget(self.other_hosts_combo, 1)
        group_layout.addLayout(picker_row)

        self.other_hosts_status_label = QtWidgets.QLabel("")
        self._set_strong_label(self.other_hosts_status_label, "gray")
        group_layout.addWidget(self.other_hosts_status_label)

        self._other_hosts_host_url_row = QtWidgets.QWidget()
        host_url_row_layout = QtWidgets.QHBoxLayout()
        host_url_row_layout.setContentsMargins(0, 0, 0, 0)
        self._other_hosts_host_url_row.setLayout(host_url_row_layout)
        host_url_row_layout.addWidget(QtWidgets.QLabel("Server URL:"))
        self.other_hosts_host_url_edit = QtWidgets.QLineEdit()
        self.other_hosts_host_url_edit.setPlaceholderText(
            "e.g., https://gitea.example.com"
        )
        host_url_row_layout.addWidget(self.other_hosts_host_url_edit)
        group_layout.addWidget(self._other_hosts_host_url_row)

        pat_row = QtWidgets.QHBoxLayout()
        pat_row.setSpacing(4)
        self.other_hosts_pat_edit = QtWidgets.QLineEdit()
        self.other_hosts_pat_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.other_hosts_pat_edit.setPlaceholderText("Paste a Personal Access Token")
        pat_row.addWidget(self.other_hosts_pat_edit, 1)
        group_layout.addLayout(pat_row)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setSpacing(4)

        self.other_hosts_connect_btn = QtWidgets.QPushButton("Connect")
        self.other_hosts_connect_btn.clicked.connect(
            self._on_other_hosts_connect_clicked
        )
        buttons_layout.addWidget(self.other_hosts_connect_btn)

        self.other_hosts_disconnect_btn = QtWidgets.QPushButton("Disconnect")
        self.other_hosts_disconnect_btn.clicked.connect(
            self._on_other_hosts_disconnect_clicked
        )
        buttons_layout.addWidget(self.other_hosts_disconnect_btn)

        self.other_hosts_browse_btn = QtWidgets.QPushButton("Browse Repos…")
        self.other_hosts_browse_btn.setToolTip(
            "List and clone repositories from the selected, connected host"
        )
        self.other_hosts_browse_btn.clicked.connect(self._on_other_hosts_browse_clicked)
        buttons_layout.addWidget(self.other_hosts_browse_btn)

        group_layout.addLayout(buttons_layout)

        layout.addWidget(group)
        self._group_other_hosts = group

        if self._other_host_ids:
            self._on_other_hosts_provider_changed(0)

    # ========== Checkpointing section (Phase G6 / R2.5) ==========

    def _build_checkpointing_section(self, layout):
        """
        Recovery-branch push policy: auto-push defaults to ON everywhere
        (desktop and headless alike), so a checkpoint is a real off-machine
        record right away rather than sitting local-only until the next real
        commit. Explicit "Always"/"Never" here just make that default (or
        its opposite) permanent regardless of environment.
        """
        group = QtWidgets.QGroupBox("Checkpointing")
        group_layout = QtWidgets.QHBoxLayout()
        group_layout.setContentsMargins(6, 4, 6, 4)
        group_layout.setSpacing(4)
        group.setLayout(group_layout)

        group_layout.addWidget(QtWidgets.QLabel("Push recovery checkpoints:"))
        self.checkpoint_push_combo = QtWidgets.QComboBox()
        self.checkpoint_push_combo.addItem(
            "Automatic (recommended — pushes by default)", None
        )
        self.checkpoint_push_combo.addItem("Always", True)
        self.checkpoint_push_combo.addItem("Never (local only)", False)
        current = settings.load_checkpoint_auto_push_override()
        self.checkpoint_push_combo.setCurrentIndex(
            {None: 0, True: 1, False: 2}.get(current, 0)
        )
        self.checkpoint_push_combo.currentIndexChanged.connect(
            self._on_checkpoint_push_policy_changed
        )
        group_layout.addWidget(self.checkpoint_push_combo, 1)

        layout.addWidget(group)
        self._group_checkpointing = group

    def _on_checkpoint_push_policy_changed(self, index):
        value = self.checkpoint_push_combo.itemData(index)
        settings.save_checkpoint_auto_push_override(value)
        log.debug(f"Checkpoint auto-push override set to {value!r}")

    def _current_other_host_id(self) -> str:
        idx = self.other_hosts_combo.currentIndex()
        if 0 <= idx < len(self._other_host_ids):
            return self._other_host_ids[idx]
        return self._other_host_ids[0] if self._other_host_ids else "generic"

    def _on_other_hosts_provider_changed(self, _index):
        provider_id = self._current_other_host_id()
        from freecad_gitpdm.providers import get_provider

        provider = get_provider(provider_id)
        self._other_hosts_host_url_row.setVisible(
            provider.capabilities.requires_host_url
        )
        self.other_hosts_pat_edit.clear()
        self._pat_auth.update_status_for(provider_id)
        self._update_other_hosts_buttons()

    def _update_other_hosts_buttons(self):
        provider_id = self._current_other_host_id()
        is_connected = settings.load_provider_connected(provider_id)
        self.other_hosts_connect_btn.setEnabled(not is_connected)
        self.other_hosts_disconnect_btn.setEnabled(is_connected)

    def _on_other_hosts_connect_clicked(self):
        provider_id = self._current_other_host_id()
        self._pat_auth.connect_clicked(
            provider_id,
            self.other_hosts_pat_edit.text(),
            host_url=self.other_hosts_host_url_edit.text(),
        )

    def _on_other_hosts_disconnect_clicked(self):
        self._pat_auth.disconnect_clicked(self._current_other_host_id())

    def _on_other_hosts_browse_clicked(self):
        """Browse/clone repos from whichever host is selected above - the
        payoff of connecting there."""
        provider_id = self._current_other_host_id()
        if not settings.load_provider_connected(provider_id):
            QtWidgets.QMessageBox.information(
                self,
                "Not Connected",
                "Connect to this host first (paste a token and click Connect), "
                "then Browse Repos.",
            )
            return

        try:
            from freecad_gitpdm.ui.repo_picker import RepoPickerDialog
            from freecad_gitpdm.providers import get_provider

            provider = get_provider(provider_id)

            def _client_factory():
                try:
                    return self._services.api_client_for(provider)
                except Exception as e:
                    log.debug(f"Failed to create {provider_id} client: {e}")
                    return None

            dlg = RepoPickerDialog(
                parent=self,
                job_runner=self._job_runner,
                git_client=self._git_client,
                client_factory=_client_factory,
                on_connect_requested=self._on_other_hosts_connect_clicked,
                default_clone_dir=settings.load_default_clone_dir(),
                provider=provider,
            )

            if dlg.exec():
                self._panel._handle_repo_picker_result(dlg)
        except Exception as e:
            log.error(f"Browse {provider_id} repos flow failed: {e}")
            QtWidgets.QMessageBox.warning(
                self,
                "Browse Repos",
                "Failed to open repo picker. See logs for details.",
            )
