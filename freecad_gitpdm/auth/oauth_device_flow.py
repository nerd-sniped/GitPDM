# -*- coding: utf-8 -*-
"""
GitPDM OAuth Device Flow Client
Sprint OAUTH-1: GitHub OAuth Device Flow implementation using stdlib only
Sprint SECURITY-4: Hardened with timing limits, jitter, and audit logging

This module implements the OAuth Device Authorization Grant flow (RFC 8628)
to authenticate users with GitHub without requiring them to enter passwords.
Uses urllib for HTTPS requests and threading for non-blocking polling.

Security enhancements:
- Absolute timeout cap on device flow (15 minutes max)
- Exponential backoff with jitter to prevent thundering herd
- Request correlation IDs for audit trails
"""

from __future__ import annotations

import json
import time
import random
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass
from typing import Optional, Callable


# SECURITY: Absolute timeout for device flow (prevents indefinite polling)
MAX_DEVICE_FLOW_DURATION_S = 900  # 15 minutes


class DeviceFlowError(Exception):
    """
    Exception raised for OAuth device flow errors.

    Attributes:
        error_code: str - OAuth error code (e.g., "authorization_pending")
        error_description: str - Human-readable error description
    """

    def __init__(self, error_code: str, error_description: str = ""):
        self.error_code = error_code
        self.error_description = error_description
        message = f"{error_code}"
        if error_description:
            message += f": {error_description}"
        super().__init__(message)


@dataclass
class DeviceCodeResponse:
    """
    Response from GitHub's device code endpoint.

    Attributes:
        device_code: str - Code used by device to poll for token
        user_code: str - Short code user enters on GitHub.com
        verification_uri: str - URL user visits to verify code
        expires_in: int - Seconds until device_code expires
        interval: int - Minimum seconds to wait between polls (default 5)
    """

    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


@dataclass
class TokenResponse:
    """
    Response from GitHub's token endpoint after successful authorization.

    Attributes:
        access_token: str - OAuth access token for API calls
        token_type: str - Type of token (typically "bearer")
        scope: str - Granted scopes (space-separated)
        refresh_token: str | None - Token to refresh access_token if expired
        expires_in: int | None - Seconds until token expires
        refresh_token_expires_in: int | None - Seconds until refresh_token expires
        obtained_at_utc: str - ISO 8601 UTC timestamp when token was obtained
    """

    access_token: str
    token_type: str
    scope: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    refresh_token_expires_in: Optional[int] = None
    obtained_at_utc: str = ""


def request_device_code(
    client_id: str,
    scopes: list[str],
    device_code_url: str = "https://github.com/login/device/code",
) -> DeviceCodeResponse:
    """
    Request a device code from GitHub.

    This is the first step of the OAuth Device Flow. The user will need to
    visit the verification_uri and enter the user_code displayed by the
    client application to grant access.

    Args:
        client_id: str - GitHub OAuth app client ID
        scopes: list[str] - OAuth scopes (e.g., ["read:user", "repo"])
        device_code_url: str - GitHub endpoint URL (for testing, can override)

    Returns:
        DeviceCodeResponse with device code and verification instructions

    Raises:
        DeviceFlowError: If request fails
        urllib.error.URLError: If network request fails
        json.JSONDecodeError: If response is not valid JSON
    """
    try:
        from freecad_gitpdm.core import log
    except ImportError:
        # Fallback for testing outside FreeCAD
        class log:
            @staticmethod
            def debug(msg):
                pass

            @staticmethod
            def error(msg):
                pass

    scope_str = " ".join(scopes)

    # Build request body (form-urlencoded)
    body_data = {
        "client_id": client_id,
        "scope": scope_str,
    }
    body_encoded = urllib.parse.urlencode(body_data).encode("utf-8")

    # Create request with proper headers
    request = urllib.request.Request(
        device_code_url,
        data=body_encoded,
        headers={
            "Accept": "application/json",
            "User-Agent": "GitPDM/1.0",
        },
        method="POST",
    )

    log.debug(f"Requesting device code from {device_code_url}")

    try:
        # Set timeout to 10 seconds
        with urllib.request.urlopen(request, timeout=10) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        log.error(f"Device code request failed: {e.code} {error_body}")
        raise DeviceFlowError("http_error", f"HTTP {e.code}") from e
    except urllib.error.URLError as e:
        log.error(f"Device code request network error: {e}")
        raise
    except json.JSONDecodeError as e:
        log.error(f"Device code response is not valid JSON: {e}")
        raise

    # Parse response
    device_code = response_data.get("device_code")
    user_code = response_data.get("user_code")
    verification_uri = response_data.get("verification_uri")
    expires_in = response_data.get("expires_in")
    interval = response_data.get("interval", 5)

    if not all([device_code, user_code, verification_uri, expires_in]):
        log.error(f"Device code response missing required fields: {response_data}")
        raise DeviceFlowError("invalid_response", "Missing required fields")

    log.debug(f"Device code received, expires in {expires_in}s")

    return DeviceCodeResponse(
        device_code=device_code,
        user_code=user_code,
        verification_uri=verification_uri,
        expires_in=expires_in,
        interval=max(interval, 5),  # Enforce minimum 5 second interval
    )


def poll_for_token(
    client_id: str,
    device_code: str,
    interval: int,
    expires_in: int,
    cancel_cb: Optional[Callable[[], bool]] = None,
    token_url: str = "https://github.com/login/oauth/access_token",
) -> TokenResponse:
    """
    Poll GitHub for an access token using the device code.

    This function blocks (but can be run in a worker thread) until the user
    approves the request on GitHub, the request is denied, or the device code
    expires.

    The cancel_cb callable, if provided, should return True to signal that
    polling should stop. This allows the UI thread to interrupt waiting.

    Args:
        client_id: str - GitHub OAuth app client ID
        device_code: str - Device code from request_device_code()
        interval: int - Minimum seconds to wait between polls (from response)
        expires_in: int - Seconds until device_code expires (from response)
        cancel_cb: callable() -> bool - Called each iteration; return True to cancel
        token_url: str - GitHub endpoint URL (for testing, can override)

    Returns:
        TokenResponse with access token and metadata

    Raises:
        DeviceFlowError: If device flow fails (expired, denied, etc.)
        urllib.error.URLError: If network request fails
        json.JSONDecodeError: If response is not valid JSON
    """
    try:
        from freecad_gitpdm.core import log
    except ImportError:
        # Fallback for testing outside FreeCAD
        class log:
            @staticmethod
            def debug(msg):
                pass

            @staticmethod
            def info(msg):
                pass

            @staticmethod
            def error(msg):
                pass

    from datetime import datetime, timezone

    start_time = time.time()
    # SECURITY: Enforce absolute timeout (RFC 8628 allows expires_in up to 1800s,
    # but we cap total flow duration to prevent resource exhaustion)
    deadline = start_time + min(expires_in, MAX_DEVICE_FLOW_DURATION_S)

    # Generate correlation ID for audit logging
    correlation_id = f"oauth-{int(start_time)}-{random.randint(1000, 9999)}"
    log.debug(
        f"Starting token poll [correlation_id={correlation_id}] (expires in {expires_in}s, hard cap {MAX_DEVICE_FLOW_DURATION_S}s)"
    )

    poll_count = 0
    poll_count = 0
    while True:
        poll_count += 1

        # Check for cancellation
        if cancel_cb and cancel_cb():
            log.debug(
                f"Token poll cancelled by user [correlation_id={correlation_id}] after {poll_count} attempts"
            )
            raise DeviceFlowError("user_cancelled", "User cancelled the flow")

        # Check for expiry
        if time.time() >= deadline:
            log.error(
                f"Device code expired [correlation_id={correlation_id}] after {poll_count} attempts"
            )
            raise DeviceFlowError("expired_token", "Device code expired")

        # SECURITY: Add jitter to prevent thundering herd
        # Sleep base interval + random jitter (0-20% of interval)
        jitter = random.uniform(0, interval * 0.2)
        sleep_duration = interval + jitter
        time.sleep(sleep_duration)

        # Build request body (form-urlencoded)
        body_data = {
            "client_id": client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }
        body_encoded = urllib.parse.urlencode(body_data).encode("utf-8")

        # Create request with proper headers
        request = urllib.request.Request(
            token_url,
            data=body_encoded,
            headers={
                "Accept": "application/json",
                "User-Agent": "GitPDM/1.0",
            },
            method="POST",
        )

        try:
            # Set timeout to 10 seconds
            with urllib.request.urlopen(request, timeout=10) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            log.error(
                f"Token poll failed [correlation_id={correlation_id}] attempt {poll_count}: {e.code} {error_body}"
            )
            raise DeviceFlowError("http_error", f"HTTP {e.code}") from e
        except urllib.error.URLError as e:
            # Transient network error; continue polling
            log.debug(
                f"Token poll network error [correlation_id={correlation_id}] attempt {poll_count} (will retry): {e}"
            )
            continue
        except json.JSONDecodeError as e:
            log.error(
                f"Token poll response invalid JSON [correlation_id={correlation_id}] attempt {poll_count}: {e}"
            )
            raise

        # Check for OAuth error in response
        if "error" in response_data:
            error_code = response_data.get("error")
            error_description = response_data.get("error_description", "")

            if error_code == "authorization_pending":
                # User hasn't approved yet; continue polling
                log.debug(
                    f"Authorization pending [correlation_id={correlation_id}] attempt {poll_count}"
                )
                continue
            elif error_code == "slow_down":
                # SECURITY: Increase poll interval by 5 seconds (RFC 8628 requirement)
                # Also add jitter to next sleep
                interval = min(interval + 5, 120)  # Cap at 2 minutes
                log.debug(
                    f"GitHub requested slow_down [correlation_id={correlation_id}], new interval: {interval}s"
                )
                continue
            elif error_code == "expired_token":
                log.error(f"Device code expired [correlation_id={correlation_id}]")
                raise DeviceFlowError(error_code, error_description)
            elif error_code == "access_denied":
                log.error(
                    f"User denied GitHub access [correlation_id={correlation_id}]"
                )
                raise DeviceFlowError(error_code, error_description)
            else:
                log.error(
                    f"GitHub returned error [correlation_id={correlation_id}]: {error_code}"
                )
                raise DeviceFlowError(error_code, error_description)

        # Success: extract token
        access_token = response_data.get("access_token")
        token_type = response_data.get("token_type", "bearer")
        # BUGFIX: Handle null scope value (GitHub may return {"scope": null})
        scope = response_data.get("scope") or ""
        refresh_token = response_data.get("refresh_token")
        expires_in_response = response_data.get("expires_in")
        refresh_token_expires_in = response_data.get("refresh_token_expires_in")

        if not access_token:
            # Import redaction helper to prevent token leaks in logs
            try:
                from freecad_gitpdm.core.log import _redact_sensitive

                safe_response = _redact_sensitive(str(response_data))
            except ImportError:
                safe_response = "[response redacted]"
            log.error(f"Token response missing access_token: {safe_response}")
            raise DeviceFlowError("invalid_response", "Missing access_token")

        obtained_at = datetime.now(timezone.utc).isoformat()

        # DEBUG: Log received scopes to help diagnose multi-computer issues
        log.info(
            f"Token obtained successfully [correlation_id={correlation_id}] after {poll_count} poll attempts. "
            f"Granted scopes: '{scope}'"
        )

        return TokenResponse(
            access_token=access_token,
            token_type=token_type,
            scope=scope,
            refresh_token=refresh_token,
            expires_in=expires_in_response,
            refresh_token_expires_in=refresh_token_expires_in,
            obtained_at_utc=obtained_at,
        )
