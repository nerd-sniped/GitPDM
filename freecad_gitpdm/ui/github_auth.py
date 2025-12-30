# -*- coding: utf-8 -*-
"""
GitHub OAuth Authentication Handlers
Sprint 4: Extracted from panel.py to reduce size and improve maintainability

Handles:
- OAuth Device Flow (connect, device code, token polling)
- Token storage/retrieval (via service container)
- Identity verification
- Disconnect flow
- UI state management for GitHub connection status
"""

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets

from freecad_gitpdm.core import log, settings


class GitHubAuthHandler:
    """Manages GitHub OAuth authentication UI and workflows."""

    def __init__(self, parent_panel, services):
        """
        Initialize GitHub auth handler.

        Args:
            parent_panel: The parent GitPDMDockWidget instance
            services: ServiceContainer for token store and API client access
        """
        self.panel = parent_panel
        self.services = services

        # OAuth state
        self._oauth_dialog = None
        self._oauth_cancel_token = None
        self._oauth_in_progress = False
        self._oauth_status_label = None
        self._is_checking_connection = False  # Sprint PERF-4: Track async status check

    # ========== Public API ==========

    def refresh_connection_status(self):
        """Check if GitHub token exists and update UI. Called on startup (Sprint PERF-4: async)."""
        # Sprint PERF-4: Prevent multiple simultaneous checks
        if self._is_checking_connection:
            log.debug("Connection status check already in progress")
            return
        
        self._is_checking_connection = True
        
        # Show checking state
        self.panel.github_status_label.setText("GitHub: Checking…")
        self.panel._set_strong_label(self.panel.github_status_label, "orange")
        
        # Sprint PERF-4: Check credentials in background
        def _check_credentials():
            """Background job to check GitHub credentials."""
            try:
                store = self.services.token_store()
                host = settings.load_github_host()
                account = settings.load_github_login()
                token = store.load(host, account)
                is_connected = token is not None
                return {"connected": is_connected, "login": account}
            except Exception as e:
                log.debug(f"Failed to check GitHub credentials: {e}")
                return {"connected": False, "login": None}
        
        # Use job_runner if available (panel initialization), fallback to sync for tests
        if hasattr(self.panel, '_job_runner') and self.panel._job_runner:
            self.panel._job_runner.run_callable(
                "check_github_credentials",
                _check_credentials,
                on_success=self._on_connection_status_checked,
                on_error=self._on_connection_status_error
            )
        else:
            # Fallback for tests without job_runner
            result = _check_credentials()
            self._on_connection_status_checked(result)

    def _on_connection_status_checked(self, result):
        """Callback when connection status check completes (Sprint PERF-4)."""
        self._is_checking_connection = False
        
        is_connected = result.get("connected", False)
        login = result.get("login", None)
        
        settings.save_github_connected(is_connected)
        self.update_ui_state()
        
        if is_connected:
            log.info("GitHub token found in credential store")
        else:
            log.debug("No GitHub token in credential store")
    
    def _on_connection_status_error(self, error_msg):
        """Callback when connection status check fails (Sprint PERF-4)."""
        self._is_checking_connection = False
        
        log.debug(f"Failed to check GitHub connection: {error_msg}")
        settings.save_github_connected(False)
        self.update_ui_state()

    def update_ui_state(self):
        """Update GitHub UI buttons and status label based on connection state."""
        is_connected = settings.load_github_connected()
        login = settings.load_github_login()

        if is_connected and login:
            self.panel.github_status_label.setText(f"GitHub: Signed in as {login}")
            self.panel._set_strong_label(self.panel.github_status_label, "green")
        elif is_connected:
            self.panel.github_status_label.setText("GitHub: Connected")
            self.panel._set_strong_label(self.panel.github_status_label, "green")
        else:
            self.panel.github_status_label.setText("GitHub: Not connected")
            self.panel._set_strong_label(self.panel.github_status_label, "gray")

        # Enable/disable buttons
        self.panel.github_connect_btn.setEnabled(
            not self._oauth_in_progress and not is_connected
        )
        self.panel.github_disconnect_btn.setEnabled(
            not self._oauth_in_progress and is_connected
        )
        self.panel.github_refresh_btn.setEnabled(not self._oauth_in_progress)

    def connect_clicked(self):
        """Handle Connect GitHub button click."""
        if self._oauth_in_progress:
            log.warning("OAuth flow already in progress")
            return

        try:
            from freecad_gitpdm.auth import config as auth_config

            # Check if OAuth is configured
            client_id = auth_config.get_client_id()
            if not client_id:
                QtWidgets.QMessageBox.warning(
                    self.panel,
                    "GitHub OAuth Not Configured",
                    "Client ID not found. Please check docs/OAUTH_DEVICE_FLOW.md",
                )
                return

            log.info("Starting GitHub OAuth Device Flow")
            self._oauth_in_progress = True
            self.update_ui_state()

            # Start request_device_code in background
            self.panel._job_runner.run_callable(
                "request_device_code",
                lambda: self._request_device_code_sync(client_id, auth_config),
                on_success=self._on_device_code_received,
                on_error=self._on_oauth_error,
            )
        except Exception as e:
            log.error(f"Connect button error: {e}")
            self._oauth_in_progress = False
            self.update_ui_state()
            QtWidgets.QMessageBox.critical(
                self.panel,
                "GitHub Connection Error",
                f"Failed to start OAuth flow: {str(e)}",
            )

    def disconnect_clicked(self):
        """Handle Disconnect GitHub button click."""
        reply = QtWidgets.QMessageBox.question(
            self.panel,
            "Disconnect GitHub",
            "Remove GitHub credentials from this computer?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        try:
            log.info("Disconnecting GitHub")

            # Delete token from credential manager
            store = self.services.token_store()
            host = settings.load_github_host()
            account = settings.load_github_login()

            store.delete(host, account)
            log.info("Token deleted from credential manager")

            # Update settings
            settings.save_github_connected(False)
            settings.save_github_login(None)
            settings.save_github_user_id(None)
            settings.save_last_verified_at(None)
            settings.save_last_api_error(None, None)

            # Update UI
            self.update_ui_state()

            # Show success message
            QtWidgets.QMessageBox.information(
                self.panel,
                "GitHub Disconnected",
                "GitHub credentials have been removed.",
            )

            log.info("GitHub disconnected")
        except Exception as e:
            log.error(f"Error disconnecting GitHub: {e}")
            QtWidgets.QMessageBox.critical(
                self.panel,
                "Disconnect Failed",
                f"Failed to disconnect: {str(e)}",
            )

    def verify_clicked(self):
        """Handle Verify / Refresh Account button click."""
        self.verify_identity_async(force=True)

    def maybe_auto_verify_identity(self):
        """Auto-verify identity on panel open with 10-minute cooldown (Sprint PERF-4: fully async)."""
        # Sprint PERF-4: Move all checks to background including cooldown
        def _check_should_verify():
            """Background job to check if verification is needed."""
            try:
                store = self.services.token_store()
                host = settings.load_github_host()
                account = settings.load_github_login()
                token = store.load(host, account)
                
                if not token:
                    return {"should_verify": False, "reason": "no_token"}
                
                last_verified = settings.load_last_verified_at() or ""
                if not last_verified:
                    return {"should_verify": True, "reason": "never_verified"}
                
                from datetime import datetime, timezone
                try:
                    dt = datetime.fromisoformat(last_verified)
                    now = datetime.now(timezone.utc)
                    age_s = (now - dt).total_seconds()
                    
                    if age_s > 10 * 60:  # 10 minute cooldown
                        return {"should_verify": True, "reason": "cooldown_expired"}
                    else:
                        return {"should_verify": False, "reason": "cooldown_active"}
                except Exception:
                    return {"should_verify": True, "reason": "parse_error"}
            except Exception as e:
                log.debug(f"Auto verify check failed: {e}")
                return {"should_verify": False, "reason": "error"}
        
        # Use job_runner if available
        if hasattr(self.panel, '_job_runner') and self.panel._job_runner:
            self.panel._job_runner.run_callable(
                "check_auto_verify_needed",
                _check_should_verify,
                on_success=self._on_auto_verify_check_complete,
                on_error=lambda error: log.debug(f"Auto verify check error: {error}")
            )
        else:
            # Fallback for tests
            result = _check_should_verify()
            self._on_auto_verify_check_complete(result)
    
    def _on_auto_verify_check_complete(self, result):
        """Callback when auto-verify check completes (Sprint PERF-4)."""
        should_verify = result.get("should_verify", False)
        reason = result.get("reason", "unknown")
        
        if should_verify:
            log.debug(f"Auto-verifying identity: {reason}")
            self.verify_identity_async(force=False)
        else:
            log.debug(f"Skipping auto-verify: {reason}")

    def verify_identity_async(self, force: bool = False):
        """Run identity verification in a worker thread and update UI."""
        try:
            from freecad_gitpdm.github.identity import fetch_viewer_identity

            client = self.services.github_api_client()
            if not client:
                self.panel.github_status_label.setText("GitHub: Not connected")
                self.panel._set_strong_label(
                    self.panel.github_status_label, "gray"
                )
                self.update_ui_state()
                return

            # Show verifying state
            self.panel.github_status_label.setText("GitHub: Verifying…")
            self.panel._set_strong_label(
                self.panel.github_status_label, "orange"
            )
            self.panel.github_refresh_btn.setEnabled(False)

            # Run in background
            self.panel._job_runner.run_callable(
                "github_verify",
                lambda: fetch_viewer_identity(client),
                on_success=self._on_identity_result,
                on_error=self._on_identity_error,
            )
        except Exception as e:
            log.error(f"Verify failed to start: {e}")
            self.panel.github_refresh_btn.setEnabled(True)
            self.update_ui_state()

    # ========== Private OAuth Flow ==========

    def _request_device_code_sync(self, client_id, auth_config):
        """Sync wrapper for request_device_code (runs in worker thread)."""
        from freecad_gitpdm.auth.oauth_device_flow import request_device_code

        return request_device_code(
            client_id, auth_config.DEFAULT_SCOPES, auth_config.DEVICE_CODE_URL
        )

    def _on_device_code_received(self, device_code_response):
        """Called when device code is received. Shows dialog and starts polling."""
        try:
            log.info(f"Device code received: {device_code_response.user_code}")

            # Create and show dialog
            self._show_oauth_dialog(device_code_response)

            # Start polling for token
            self._start_token_polling(device_code_response)
        except Exception as e:
            log.error(f"Error processing device code: {e}")
            self._on_oauth_error(e)

    def _show_oauth_dialog(self, device_code_response):
        """Create and show the OAuth authorization dialog."""
        self._oauth_dialog = QtWidgets.QDialog(self.panel)
        self._oauth_dialog.setWindowTitle("Connect GitHub")
        self._oauth_dialog.setMinimumWidth(400)
        self._oauth_dialog.setModal(True)

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Instructions
        instructions = QtWidgets.QLabel()
        instructions.setWordWrap(True)
        instructions.setText(
            "We opened a GitHub page in your browser.\n"
            "Enter this code on the GitHub page:"
        )
        layout.addWidget(instructions)

        # Code display (large, monospace)
        code_label = QtWidgets.QLabel(device_code_response.user_code)
        code_font = QtGui.QFont("Courier")
        code_font.setPointSize(16)
        code_font.setBold(True)
        code_label.setFont(code_font)
        code_label.setAlignment(QtCore.Qt.AlignCenter)
        code_label.setStyleSheet(
            "color: darkblue; border: 1px solid gray; padding: 8px;"
        )
        code_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(code_label)

        # Status label
        self._oauth_status_label = QtWidgets.QLabel("Waiting for authorization…")
        self._oauth_status_label.setStyleSheet(
            "color: orange; font-style: italic;"
        )
        self._oauth_status_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self._oauth_status_label)

        # Buttons
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setSpacing(6)

        copy_btn = QtWidgets.QPushButton("Copy Code")
        copy_btn.clicked.connect(
            lambda: self._copy_to_clipboard(device_code_response.user_code)
        )
        buttons_layout.addWidget(copy_btn)

        open_btn = QtWidgets.QPushButton("Open GitHub Page")
        open_btn.clicked.connect(
            lambda: self._open_verification_uri(
                device_code_response.verification_uri
            )
        )
        buttons_layout.addWidget(open_btn)

        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self._on_oauth_dialog_cancel)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)
        layout.addStretch()

        self._oauth_dialog.setLayout(layout)

        # Auto-copy code and open browser
        self._copy_to_clipboard(device_code_response.user_code)
        self._open_verification_uri(device_code_response.verification_uri)

        self._oauth_dialog.show()

    def _copy_to_clipboard(self, text):
        """Copy text to clipboard."""
        try:
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(text)
            log.debug("Copied to clipboard")
        except Exception as e:
            log.warning(f"Failed to copy to clipboard: {e}")

    def _open_verification_uri(self, uri):
        """Open verification URI in default browser."""
        try:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(uri))
            log.debug(f"Opened browser to {uri}")
        except Exception as e:
            log.warning(f"Failed to open browser: {e}")

    def _on_oauth_dialog_cancel(self):
        """Handle Cancel button in OAuth dialog."""
        if self._oauth_cancel_token:
            self._oauth_cancel_token.cancel()
        if self._oauth_dialog:
            self._oauth_dialog.close()
        self._oauth_in_progress = False
        self.update_ui_state()
        log.info("OAuth flow cancelled by user")

    def _start_token_polling(self, device_code_response):
        """Start polling for token in background thread."""
        try:
            from freecad_gitpdm.auth import config as auth_config

            client_id = auth_config.get_client_id()

            # Create cancel token
            self._oauth_cancel_token = _CancelToken()

            # Start polling
            self.panel._job_runner.run_callable(
                "poll_for_token",
                lambda: self._poll_for_token_sync(
                    client_id, device_code_response, auth_config
                ),
                on_success=self._on_token_received,
                on_error=self._on_token_poll_error,
            )
        except Exception as e:
            log.error(f"Failed to start token polling: {e}")
            self._on_oauth_error(e)

    def _poll_for_token_sync(self, client_id, device_code_response, auth_config):
        """Sync wrapper for poll_for_token (runs in worker thread)."""
        from freecad_gitpdm.auth.oauth_device_flow import poll_for_token

        return poll_for_token(
            client_id,
            device_code_response.device_code,
            device_code_response.interval,
            device_code_response.expires_in,
            cancel_cb=(
                lambda: (
                    self._oauth_cancel_token.is_cancelled
                    if self._oauth_cancel_token
                    else False
                )
            ),
            token_url=auth_config.TOKEN_URL,
        )

    def _on_token_received(self, token_response):
        """Called when token is successfully received. Stores it and updates UI."""
        try:
            log.info("Token received successfully")

            # Store token
            store = self.services.token_store()
            host = settings.load_github_host()
            account = settings.load_github_login()

            store.save(host, account, token_response)
            log.info("Token stored in credential manager")

            # Update settings
            settings.save_github_connected(True)

            # Update UI
            self.update_ui_state()

            # Close dialog
            if self._oauth_dialog:
                self._oauth_dialog.close()

            # Show success message
            QtWidgets.QMessageBox.information(
                self.panel, "GitHub Connected", "Successfully connected to GitHub!"
            )

            log.info("GitHub OAuth flow completed successfully")
        except Exception as e:
            log.error(f"Error storing token: {e}")
            self._on_oauth_error(e)
        finally:
            self._oauth_in_progress = False
            self._oauth_cancel_token = None
            self.update_ui_state()
            # Trigger identity verification immediately after connect
            try:
                QtCore.QTimer.singleShot(50, self.verify_identity_async)
            except Exception:
                pass

    def _on_token_poll_error(self, error):
        """Called if token polling fails."""
        from freecad_gitpdm.auth.oauth_device_flow import DeviceFlowError

        try:
            self._oauth_in_progress = False

            # Close dialog if open
            if self._oauth_dialog:
                self._oauth_dialog.close()

            # Show appropriate error message
            if isinstance(error, DeviceFlowError):
                if error.error_code == "user_cancelled":
                    log.info("OAuth flow cancelled")
                    return
                elif error.error_code == "expired_token":
                    msg = "Device code expired. Please try again."
                elif error.error_code == "access_denied":
                    msg = "GitHub access was denied. Please try again."
                else:
                    msg = f"GitHub error: {error.error_code}"
            else:
                msg = f"Connection error: {str(error)}"

            log.error(f"OAuth error: {msg}")
            QtWidgets.QMessageBox.warning(
                self.panel, "GitHub Connection Failed", msg
            )
        except Exception as e:
            log.error(f"Error handling token poll error: {e}")
        finally:
            self.update_ui_state()
            self._oauth_cancel_token = None

    def _on_oauth_error(self, error):
        """General error handler for OAuth flow."""
        try:
            self._oauth_in_progress = False

            # Close dialog if open
            if self._oauth_dialog:
                self._oauth_dialog.close()

            log.error(f"OAuth flow error: {error}")
            QtWidgets.QMessageBox.critical(
                self.panel,
                "GitHub Connection Error",
                f"An error occurred: {str(error)}",
            )
        except Exception as e:
            log.error(f"Error handling OAuth error: {e}")
        finally:
            self.update_ui_state()
            self._oauth_cancel_token = None

    # ========== Identity Verification ==========

    def _on_identity_result(self, result):
        """Handle identity verification result on UI thread."""
        from datetime import datetime, timezone

        try:
            if not result or not getattr(result, "ok", False):
                settings.save_last_api_error(
                    result.error_code if result else "UNKNOWN",
                    result.message if result else "",
                )
                if result and result.error_code == "UNAUTHORIZED":
                    settings.save_github_connected(False)
                    self.panel.github_status_label.setText(
                        "GitHub: Session expired; please reconnect"
                    )
                    self.panel._set_strong_label(
                        self.panel.github_status_label, "red"
                    )
                elif result and result.error_code == "RATE_LIMITED":
                    self.panel.github_status_label.setText(
                        "GitHub: Rate limit reached; try later"
                    )
                    self.panel._set_strong_label(
                        self.panel.github_status_label, "orange"
                    )
                elif result and result.error_code == "NETWORK_ERROR":
                    self.panel.github_status_label.setText(
                        "GitHub: Network error; retry"
                    )
                    self.panel._set_strong_label(
                        self.panel.github_status_label, "orange"
                    )
                else:
                    self.panel.github_status_label.setText(
                        "GitHub: Verification failed"
                    )
                    self.panel._set_strong_label(
                        self.panel.github_status_label, "red"
                    )
                self.panel.github_refresh_btn.setEnabled(True)
                self.update_ui_state()
                return

            # Success: persist non-secret metadata
            login = result.login or ""
            uid = result.user_id
            settings.save_github_login(login or None)
            settings.save_github_user_id(uid)
            settings.save_github_connected(True)
            settings.save_last_api_error(None, None)
            settings.save_last_verified_at(
                datetime.now(timezone.utc).isoformat()
            )

            # Update UI
            if login:
                self.panel.github_status_label.setText(
                    f"GitHub: Signed in as {login}"
                )
            else:
                self.panel.github_status_label.setText("GitHub: Connected")
            self.panel._set_strong_label(self.panel.github_status_label, "green")
            self.panel.github_refresh_btn.setEnabled(True)
            self.update_ui_state()
        except Exception as e:
            log.error(f"Identity result handling failed: {e}")
            self.panel.github_refresh_btn.setEnabled(True)

    def _on_identity_error(self, error):
        """Handle unexpected verification error."""
        settings.save_last_api_error("UNKNOWN", str(error))
        self.panel.github_status_label.setText("GitHub: Verification error")
        self.panel._set_strong_label(self.panel.github_status_label, "red")
        self.panel.github_refresh_btn.setEnabled(True)
        self.update_ui_state()


class _CancelToken:
    """Simple cancel token for OAuth polling."""

    def __init__(self):
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True
