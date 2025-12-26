# -*- coding: utf-8 -*-
"""
GitPDM Logging Module
Sprint 0: Lightweight logging to FreeCAD console
"""

import FreeCAD


def _redact_sensitive(message):
    """
    Redact potentially sensitive data from log messages
    Sprint 0: Stub implementation
    
    Args:
        message: Log message string
        
    Returns:
        Redacted message string
    """
    # Future: implement password/token redaction
    # For now, just return as-is
    return message


def info(message):
    """
    Log an informational message to FreeCAD console
    
    Args:
        message: Message to log
    """
    safe_msg = _redact_sensitive(str(message))
    FreeCAD.Console.PrintLog(f"[GitPDM] INFO: {safe_msg}\n")


def warning(message):
    """
    Log a warning message to FreeCAD console
    
    Args:
        message: Warning message to log
    """
    safe_msg = _redact_sensitive(str(message))
    FreeCAD.Console.PrintWarning(f"[GitPDM] WARNING: {safe_msg}\n")


def error(message):
    """
    Log an error message to FreeCAD console
    
    Args:
        message: Error message to log
    """
    safe_msg = _redact_sensitive(str(message))
    FreeCAD.Console.PrintError(f"[GitPDM] ERROR: {safe_msg}\n")


def debug(message):
    """
    Log a debug message (currently same as info)
    
    Args:
        message: Debug message to log
    """
    # FreeCAD doesn't have a separate debug level
    # Use PrintLog for now
    safe_msg = _redact_sensitive(str(message))
    FreeCAD.Console.PrintLog(f"[GitPDM] DEBUG: {safe_msg}\n")
