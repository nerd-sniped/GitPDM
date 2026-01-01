# -*- coding: utf-8 -*-
"""
OAuth Token Refresh and Expiry Management
Sprint SECURITY-3: Automatic token expiry detection and refresh

Implements:
- Token expiry detection based on obtained_at + expires_in
- Automatic refresh before expiry using refresh_token
- Graceful fallback to re-authentication if refresh fails

Security: Prevents usage of expired tokens and ensures fresh
credentials without requiring manual re-authentication.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from freecad_gitpdm.auth.oauth_device_flow import TokenResponse


# Refresh token this many seconds before actual expiry
REFRESH_BUFFER_SECONDS = 300  # 5 minutes


def is_token_expired(token: TokenResponse, buffer_s: int = REFRESH_BUFFER_SECONDS) -> bool:
    """
    Check if token is expired or will expire soon.
    
    Args:
        token: TokenResponse to check
        buffer_s: Seconds before expiry to consider "expired" (default 300)
        
    Returns:
        True if token is expired or expiring soon, False if still valid
    """
    if not token.expires_in or not token.obtained_at_utc:
        # No expiry info; assume token is long-lived (GitHub PATs)
        return False
    
    try:
        obtained_at = datetime.fromisoformat(token.obtained_at_utc.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        # Can't parse timestamp; assume expired to be safe
        return True
    
    expiry_time = obtained_at + timedelta(seconds=token.expires_in)
    now = datetime.now(timezone.utc)
    
    # Check if we're within buffer_s of expiry
    time_until_expiry = (expiry_time - now).total_seconds()
    return time_until_expiry <= buffer_s


def refresh_token(
    client_id: str,
    refresh_token: str,
    token_url: str = "https://github.com/login/oauth/access_token",
) -> Tuple[bool, Optional[TokenResponse], str]:
    """
    Refresh an access token using a refresh token.
    
    Args:
        client_id: GitHub OAuth app client ID
        refresh_token: Refresh token from previous TokenResponse
        token_url: GitHub token endpoint (for testing)
        
    Returns:
        (success, new_token, error_message) tuple
        - success: True if refresh succeeded
        - new_token: New TokenResponse if success, None otherwise
        - error_message: Empty if success, error description if failed
    """
    if not refresh_token:
        return False, None, "No refresh token available"
    
    try:
        from freecad_gitpdm.core import log
    except ImportError:
        # Fallback for testing
        class log:
            @staticmethod
            def debug(msg):
                pass
            @staticmethod
            def error(msg):
                pass
    
    # Build request body
    body_data = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    body_encoded = urllib.parse.urlencode(body_data).encode("utf-8")
    
    # Create request
    request = urllib.request.Request(
        token_url,
        data=body_encoded,
        headers={
            "Accept": "application/json",
            "User-Agent": "GitPDM/1.0",
        },
        method="POST",
    )
    
    log.debug("Attempting token refresh")
    
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        log.error(f"Token refresh failed: {e.code} {error_body}")
        return False, None, f"Token refresh failed (HTTP {e.code})"
    except urllib.error.URLError as e:
        log.error(f"Token refresh network error: {e}")
        return False, None, f"Network error during token refresh: {e}"
    except json.JSONDecodeError as e:
        log.error(f"Token refresh response invalid JSON: {e}")
        return False, None, "Invalid response from GitHub"
    
    # Check for errors in response
    if "error" in response_data:
        error_code = response_data.get("error")
        error_description = response_data.get("error_description", "")
        log.error(f"Token refresh error: {error_code} - {error_description}")
        return False, None, f"Refresh failed: {error_description or error_code}"
    
    # Extract new token
    access_token = response_data.get("access_token")
    if not access_token:
        log.error("Token refresh response missing access_token")
        return False, None, "Invalid response: missing access_token"
    
    token_type = response_data.get("token_type", "bearer")
    scope = response_data.get("scope", "")
    new_refresh_token = response_data.get("refresh_token")
    expires_in = response_data.get("expires_in")
    refresh_token_expires_in = response_data.get("refresh_token_expires_in")
    
    obtained_at = datetime.now(timezone.utc).isoformat()
    
    new_token = TokenResponse(
        access_token=access_token,
        token_type=token_type,
        scope=scope,
        refresh_token=new_refresh_token,
        expires_in=expires_in,
        refresh_token_expires_in=refresh_token_expires_in,
        obtained_at_utc=obtained_at,
    )
    
    log.debug("Token refreshed successfully")
    return True, new_token, ""


def ensure_fresh_token(
    token: TokenResponse,
    client_id: str,
    token_url: str = "https://github.com/login/oauth/access_token",
) -> Tuple[bool, Optional[TokenResponse], str]:
    """
    Ensure token is fresh (not expired), refreshing if needed.
    
    Args:
        token: Current TokenResponse
        client_id: GitHub OAuth app client ID
        token_url: GitHub token endpoint
        
    Returns:
        (is_fresh, token_to_use, message) tuple
        - is_fresh: True if token is usable (either was fresh or refreshed)
        - token_to_use: Token to use (original or refreshed)
        - message: Empty if OK, error/info message otherwise
    """
    if not is_token_expired(token):
        return True, token, ""
    
    # Token is expired or expiring soon
    if not token.refresh_token:
        return False, token, "Token expired and no refresh token available. Please sign in again."
    
    # Attempt refresh
    success, new_token, error = refresh_token(client_id, token.refresh_token, token_url)
    
    if success and new_token:
        return True, new_token, "Token refreshed"
    else:
        return False, token, f"Token refresh failed: {error}. Please sign in again."


def get_token_ttl_seconds(token: TokenResponse) -> Optional[int]:
    """
    Get remaining time-to-live for token in seconds.
    
    Args:
        token: TokenResponse to check
        
    Returns:
        Seconds until expiry, or None if no expiry info available
    """
    if not token.expires_in or not token.obtained_at_utc:
        return None
    
    try:
        obtained_at = datetime.fromisoformat(token.obtained_at_utc.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    
    expiry_time = obtained_at + timedelta(seconds=token.expires_in)
    now = datetime.now(timezone.utc)
    
    ttl = (expiry_time - now).total_seconds()
    return max(0, int(ttl))
