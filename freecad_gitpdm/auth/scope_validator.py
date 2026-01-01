# -*- coding: utf-8 -*-
"""
OAuth Scope Validation
Sprint SECURITY-2: Validate granted scopes match requested scopes

Ensures tokens have the minimum required scopes and detects scope
downgrades (user grants fewer scopes than requested).

Security: Prevents privilege escalation and ensures the app only
operates with expected permissions.
"""

from __future__ import annotations

from typing import Set, Tuple
from freecad_gitpdm.auth.oauth_device_flow import TokenResponse


# Minimum required scopes for GitPDM to function
REQUIRED_SCOPES = {"repo", "read:user"}

# Optional scopes (nice to have but not required)
OPTIONAL_SCOPES = set()


def parse_scopes(scope_string: str) -> Set[str]:
    """
    Parse space-separated or comma-separated scope string into set.

    Args:
        scope_string: Space-separated or comma-separated OAuth scopes 
                     (e.g., "repo read:user" or "repo,read:user")

    Returns:
        Set of individual scope strings
    """
    if not scope_string:
        return set()
    # Handle both space-separated and comma-separated formats
    # GitHub typically uses space-separated, but some responses may use commas
    delimiter = ',' if ',' in scope_string and ' ' not in scope_string else ' '
    return set(s.strip() for s in scope_string.split(delimiter) if s.strip())


def validate_token_scopes(token: TokenResponse) -> Tuple[bool, str]:
    """
    Validate that token has required scopes.

    Args:
        token: TokenResponse from OAuth device flow

    Returns:
        (is_valid, message) tuple
        - is_valid: True if all required scopes present
        - message: Empty string if valid, error description if invalid
    """
    granted_scopes = parse_scopes(token.scope)

    # Check for required scopes
    missing_scopes = REQUIRED_SCOPES - granted_scopes

    if missing_scopes:
        missing_list = ", ".join(sorted(missing_scopes))
        return False, (
            f"Token missing required scopes: {missing_list}. "
            f"GitPDM needs these permissions to backup your FreeCAD files. "
            f"Please re-authenticate and grant all requested permissions."
        )

    return True, ""


def get_scope_description(scope: str) -> str:
    """
    Get human-readable description of what a scope allows.

    Args:
        scope: OAuth scope identifier

    Returns:
        User-friendly description
    """
    descriptions = {
        "repo": "Access your repositories (read and write)",
        "read:user": "Read your GitHub profile information",
        "public_repo": "Access public repositories only",
        "read:org": "Read organization membership",
    }
    return descriptions.get(scope, f"Unknown scope: {scope}")


def explain_requested_scopes() -> str:
    """
    Generate user-friendly explanation of why scopes are needed.

    Returns:
        Multi-line explanation for display in auth UI
    """
    lines = [
        "GitPDM requests the following permissions:",
        "",
    ]

    for scope in sorted(REQUIRED_SCOPES):
        desc = get_scope_description(scope)
        lines.append(f"• {scope}: {desc}")

    lines.extend(
        [
            "",
            "These permissions are necessary to:",
            "• Save your FreeCAD files to GitHub repositories",
            "• Read repository contents for synchronization",
            "• Identify you as the commit author",
        ]
    )

    return "\n".join(lines)


def audit_scope_changes(old_token: TokenResponse, new_token: TokenResponse) -> str:
    """
    Compare scopes between old and new token for audit logging.

    Args:
        old_token: Previous token
        new_token: New/refreshed token

    Returns:
        Human-readable description of scope changes (empty if no changes)
    """
    old_scopes = parse_scopes(old_token.scope)
    new_scopes = parse_scopes(new_token.scope)

    if old_scopes == new_scopes:
        return ""

    added = new_scopes - old_scopes
    removed = old_scopes - new_scopes

    messages = []
    if added:
        messages.append(f"Added scopes: {', '.join(sorted(added))}")
    if removed:
        messages.append(f"Removed scopes: {', '.join(sorted(removed))}")

    return "; ".join(messages)
