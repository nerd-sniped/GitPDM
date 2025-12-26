# -*- coding: utf-8 -*-
"""
GitPDM Logging Module
Sprint 1: Lightweight logging to FreeCAD console
"""


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
        FreeCAD.Console.PrintWarning(
            f"[GitPDM] WARNING: {safe_msg}\n"
        )
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
