"""
GitPDM Logging Module
Sprint 1: Lightweight logging to FreeCAD console
Sprint OAUTH-1: Token redaction to prevent secrets in logs
"""

import re


def _redact_sensitive(message):
    """
    Redact potentially sensitive data from log messages.

    Patterns removed:
    - OAuth access tokens (ghp_* format used by GitHub)
    - OAuth refresh tokens
    - GitHub Personal Access Tokens (github_pat_* format)
    - JSON keys containing "access_token", "refresh_token"

    Args:
        message: Log message string

    Returns:
        Redacted message string with sensitive data replaced
    """
    if not message:
        return message

    msg = str(message)

    # Redact GitHub OAuth access tokens (ghp_XXXX)
    msg = re.sub(r"ghp_[a-zA-Z0-9_]+", "[REDACTED_ACCESS_TOKEN]", msg)

    # Redact GitHub Personal Access Tokens (github_pat_XXXX)
    msg = re.sub(r"github_pat_[a-zA-Z0-9_]+", "[REDACTED_PAT]", msg)

    # Redact refresh tokens (usually long base64 or similar)
    # Look for "refresh_token": "..." patterns in JSON
    msg = re.sub(
        r'("refresh_token"\s*:\s*)"([^"]*)"',
        r'\1"[REDACTED_REFRESH_TOKEN]"',
        msg,
        flags=re.IGNORECASE,
    )

    # Redact access tokens in JSON
    # Look for "access_token": "..." patterns in JSON
    msg = re.sub(
        r'("access_token"\s*:\s*)"([^"]*)"',
        r'\1"[REDACTED_ACCESS_TOKEN]"',
        msg,
        flags=re.IGNORECASE,
    )

    # Redact token_type if it's a bearer token (less critical but good practice)
    # Redact any "token" key that looks like it contains a real token
    msg = re.sub(
        r'"token"\s*:\s*"([a-zA-Z0-9_\-\.]+)"',
        r'"token": "[REDACTED_TOKEN]"',
        msg,
        flags=re.IGNORECASE,
    )

    # Redact Authorization: Bearer <token> header-like strings
    msg = re.sub(
        r"(Authorization\s*:\s*Bearer)\s+[A-Za-z0-9_\-\.~=+/]+",
        r"\1 [REDACTED]",
        msg,
        flags=re.IGNORECASE,
    )

    return msg


def info(message):
    """
    Log an informational message to FreeCAD console

    Args:
        message: Message to log
    """
    try:
        import FreeCAD

        safe_msg = _redact_sensitive(str(message))
        FreeCAD.Console.PrintLog(f"[GitPDM] INFO: {safe_msg}\n")
    except ImportError:
        # FreeCAD not available, fall back to print
        print(f"[GitPDM] INFO: {message}")


def warning(message):
    """
    Log a warning message to FreeCAD console

    Args:
        message: Warning message to log
    """
    try:
        import FreeCAD

        safe_msg = _redact_sensitive(str(message))
        FreeCAD.Console.PrintWarning(f"[GitPDM] WARNING: {safe_msg}\n")
    except ImportError:
        print(f"[GitPDM] WARNING: {message}")


def error(message):
    """
    Log an error message to FreeCAD console

    Args:
        message: Error message to log
    """
    try:
        import FreeCAD

        safe_msg = _redact_sensitive(str(message))
        FreeCAD.Console.PrintError(f"[GitPDM] ERROR: {safe_msg}\n")
    except ImportError:
        print(f"[GitPDM] ERROR: {message}")


def debug(message):
    """
    Log a debug message (currently same as info)

    Args:
        message: Debug message to log
    """
    try:
        import FreeCAD

        safe_msg = _redact_sensitive(str(message))
        FreeCAD.Console.PrintLog(f"[GitPDM] DEBUG: {safe_msg}\n")
    except ImportError:
        print(f"[GitPDM] DEBUG: {message}")


def error_safe(message, exception=None):
    """
    Log an error with automatic exception redaction.

    Args:
        message: Error message prefix
        exception: Optional exception object to include (will be redacted)
    """
    if exception:
        safe_exc = _redact_sensitive(str(exception))
        full_msg = f"{message}: {safe_exc}"
    else:
        full_msg = message
    error(full_msg)


def warning_safe(message, exception=None):
    """
    Log a warning with automatic exception redaction.

    Args:
        message: Warning message prefix
        exception: Optional exception object to include (will be redacted)
    """
    if exception:
        safe_exc = _redact_sensitive(str(exception))
        full_msg = f"{message}: {safe_exc}"
    else:
        full_msg = message
    warning(full_msg)


def debug_safe(message, exception=None):
    """
    Log a debug message with automatic exception redaction.

    Args:
        message: Debug message prefix
        exception: Optional exception object to include (will be redacted)
    """
    if exception:
        safe_exc = _redact_sensitive(str(exception))
        full_msg = f"{message}: {safe_exc}"
    else:
        full_msg = message
    debug(full_msg)
