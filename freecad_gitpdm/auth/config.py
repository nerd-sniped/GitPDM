# -*- coding: utf-8 -*-
"""
GitPDM OAuth Configuration
Sprint OAUTH-0: GitHub OAuth Device Flow constants

This module defines OAuth endpoints and client configuration for
GitHub authentication. No actual network calls or token handling
happens in this sprint.
"""

# GitHub OAuth endpoints
GITHUB_HOST = "github.com"
GITHUB_API_BASE = "https://api.github.com"
DEVICE_CODE_URL = "https://github.com/login/device/code"
TOKEN_URL = "https://github.com/login/oauth/access_token"
VERIFICATION_URI_DEFAULT = "https://github.com/login/device"

# OAuth scopes requested
# - read:user: Get user profile (username, email)
# - repo: Access private repositories for git operations
DEFAULT_SCOPES = ["read:user", "repo"]

# Client ID for GitPDM GitHub OAuth App
# Fallback: "REPLACE_ME" indicates OAuth is not yet configured
_CLIENT_ID = "Ov23li9bhJnBzf4o55fw"


def get_client_id():
    """
    Get the GitHub OAuth client ID.
    
    Returns:
        str | None: Client ID if configured, None if placeholder
        
    Notes:
        Returns None when _CLIENT_ID is still "REPLACE_ME" so UI
        can show "Not configured" message to users.
    """
    if _CLIENT_ID == "REPLACE_ME":
        return None
    return _CLIENT_ID
