# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
PAT (Personal Access Token) Authentication Handler

Connect flow for GitLab/Bitbucket/Gitea-Forgejo/SourceHut - the multi-
provider hosts that authenticate via a pasted token rather than GitHub's
OAuth device flow (see providers/base.py's `requires_manual_token`).
Meaningfully simpler than ui/github_auth.py's GitHubAuthHandler: no device
code, no polling, no browser handoff - paste a token, verify it works,
store it.
"""

# FreeCAD's own Qt compatibility shim -- re-exports whichever binding
# (PySide2/PySide6/...) the running FreeCAD was built against, so this
# code doesn't need updating on the next Qt major-version bump.
from PySide import QtWidgets

from freecad_gitpdm.core import log, settings
from freecad_gitpdm.core.log import _redact_sensitive
from freecad_gitpdm.providers import get_provider


class PatAuthHandler:
    """Manages PAT-based connect/disconnect/verify for the panel's "Other
    Git Hosts" section. Unlike GitHubAuthHandler, every method here takes
    an explicit `provider_id` - the panel supports connecting to more than
    one of these hosts, so there's no single implicit "the" provider."""

    def __init__(self, parent_panel, services):
        self.panel = parent_panel
        self.services = services
        self._connect_in_progress = False

    # ========== Public API ==========

    def connect_clicked(self, provider_id: str, pat: str, host_url: str = ""):
        """Verify a pasted PAT against the host and, on success, store it."""
        if self._connect_in_progress:
            log.warning("PAT connect already in progress")
            return

        provider = get_provider(provider_id)
        pat = (pat or "").strip()
        if not pat:
            QtWidgets.QMessageBox.warning(
                self.panel, "Connect", "Paste a Personal Access Token first."
            )
            return

        if provider.capabilities.requires_host_url and not (host_url or "").strip():
            QtWidgets.QMessageBox.warning(
                self.panel,
                "Connect",
                f"Enter the {provider.display_name} server URL first.",
            )
            return

        client = provider.build_api_client(pat, "GitPDM/1.0", host=host_url or None)
        if client is None:
            QtWidgets.QMessageBox.critical(
                self.panel,
                "Connect",
                f"Could not build a client for {provider.display_name}.",
            )
            return

        self._connect_in_progress = True
        self._set_status(provider, "Verifying…", "orange")

        self.panel._job_runner.run_callable(
            f"pat_connect_{provider_id}",
            lambda: provider.fetch_identity(client),
            on_success=lambda identity: self._on_verified(
                provider, pat, host_url, identity
            ),
            on_error=lambda err: self._on_connect_error(provider, err),
        )

    def _on_verified(self, provider, pat: str, host_url: str, identity):
        self._connect_in_progress = False
        if not identity.ok:
            self._set_status(provider, "Not connected", "gray")
            QtWidgets.QMessageBox.warning(
                self.panel,
                "Connect Failed",
                identity.message or "Could not verify this token.",
            )
            return

        host = (
            (host_url or "").strip()
            if provider.capabilities.requires_host_url
            else provider.default_host
        )

        try:
            from freecad_gitpdm.auth.oauth_device_flow import TokenResponse
            from datetime import datetime, timezone

            token = TokenResponse(
                access_token=pat,
                token_type="bearer",
                scope="",
                obtained_at_utc=datetime.now(timezone.utc).isoformat(),
                provider=provider.provider_id,
            )
            store = self.services.token_store()
            store.save(host, identity.login, token)
        except OSError as e:
            log.error_safe("Failed to store PAT", e)
            QtWidgets.QMessageBox.critical(
                self.panel,
                "Connect Failed",
                f"Verified but could not save the token: {_redact_sensitive(str(e))}",
            )
            return

        settings.save_provider_connected(provider.provider_id, True)
        settings.save_provider_login(provider.provider_id, identity.login)
        settings.save_provider_host(
            provider.provider_id, host, default_host=provider.default_host
        )

        log.info(f"Connected {provider.provider_id} as {identity.login}")
        self._set_status(
            provider,
            f"Connected as {identity.login}" if identity.login else "Connected",
            "green",
        )
        self.panel._update_other_hosts_buttons()

    def _on_connect_error(self, provider, error):
        self._connect_in_progress = False
        log.warning(f"PAT connect failed for {provider.provider_id}: {error}")
        self._set_status(provider, "Not connected", "gray")
        QtWidgets.QMessageBox.warning(
            self.panel,
            "Connect Failed",
            _redact_sensitive(str(error)),
        )

    def disconnect_clicked(self, provider_id: str):
        provider = get_provider(provider_id)
        reply = QtWidgets.QMessageBox.question(
            self.panel,
            f"Disconnect from {provider.display_name}?",
            f"This removes the stored {provider.display_name} token from this "
            "computer. You can reconnect any time by pasting a token again.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        try:
            store = self.services.token_store()
            host = settings.load_provider_host(
                provider_id, default_host=provider.default_host
            )
            account = settings.load_provider_login(provider_id)
            store.delete(host, account)
        except OSError as e:
            log.error_safe(f"Error disconnecting {provider_id}", e)

        settings.save_provider_connected(provider_id, False)
        settings.save_provider_login(provider_id, None)
        settings.save_provider_user_id(provider_id, None)
        settings.save_provider_last_verified_at(provider_id, None)

        log.info(f"Disconnected {provider_id}")
        self._set_status(provider, "Not connected", "gray")
        self.panel._update_other_hosts_buttons()

    def update_status_for(self, provider_id: str):
        """Refresh the status label for whichever provider is currently
        selected in the panel's dropdown (called on dropdown change)."""
        provider = get_provider(provider_id)
        is_connected = settings.load_provider_connected(provider_id)
        login = settings.load_provider_login(provider_id)
        if is_connected and login:
            self._set_status(provider, f"Connected as {login}", "green")
        elif is_connected:
            self._set_status(provider, "Connected", "green")
        else:
            self._set_status(provider, "Not connected", "gray")

    # ========== Helpers ==========

    def _set_status(self, provider, text: str, color: str):
        self.panel.other_hosts_status_label.setText(f"{provider.display_name}: {text}")
        self.panel._set_strong_label(self.panel.other_hosts_status_label, color)
