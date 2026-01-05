"""
GitPDM Diagnostics Module
Sprint OAUTH-0: System diagnostic information

Provides diagnostic information for troubleshooting and
support requests. Includes OAuth configuration status but
never includes sensitive data like tokens.
"""

import sys
import platform
from freecad.gitpdm.core import settings, log


def get_diagnostics():
    """
    Collect diagnostic information about GitPDM configuration.

    Returns:
        dict: Diagnostic information

    Notes:
        Never includes sensitive data (tokens, passwords, etc.)
    """
    diagnostics = {}

    # Python and platform information
    diagnostics["python_version"] = sys.version
    diagnostics["platform"] = platform.platform()
    diagnostics["platform_system"] = platform.system()
    diagnostics["platform_release"] = platform.release()

    # FreeCAD version
    try:
        import FreeCAD

        diagnostics["freecad_version"] = (
            f"{FreeCAD.Version()[0]}.{FreeCAD.Version()[1]}.{FreeCAD.Version()[2]}"
        )
        diagnostics["freecad_build"] = FreeCAD.Version()[3]
    except Exception as e:
        diagnostics["freecad_version"] = f"Error: {e}"
        diagnostics["freecad_build"] = "Unknown"

    # Qt binding
    try:
        from PySide6 import QtCore

        diagnostics["qt_binding"] = "PySide6"
        diagnostics["qt_version"] = QtCore.qVersion()
    except ImportError:
        try:
            from PySide6 import QtCore

            diagnostics["qt_binding"] = "PySide6"
            diagnostics["qt_version"] = QtCore.qVersion()
        except ImportError:
            diagnostics["qt_binding"] = "None"
            diagnostics["qt_version"] = "None"

    # Git availability
    try:
        from freecad.gitpdm.git import client

        git_client = client.GitClient()
        git_version = git_client.get_git_version()
        diagnostics["git_available"] = git_version is not None
        diagnostics["git_version"] = git_version if git_version else "Not found"
    except Exception as e:
        diagnostics["git_available"] = False
        diagnostics["git_version"] = f"Error: {e}"

    # Repository configuration
    try:
        repo_path = settings.load_repo_path()
        diagnostics["repo_path_configured"] = bool(repo_path)
        # Don't include actual path for privacy
    except Exception as e:
        diagnostics["repo_path_configured"] = False
        log.warning(f"Failed to load repo path: {e}")

    # GitHub OAuth configuration (Sprint OAUTH-0)
    try:
        from freecad.gitpdm.auth import config as auth_config

        client_id = auth_config.get_client_id()
        diagnostics["oauth_client_id_configured"] = client_id is not None
        # Never include actual client_id value
    except Exception as e:
        diagnostics["oauth_client_id_configured"] = False
        log.warning(f"Failed to load OAuth config: {e}")

    # GitHub connection status (Sprint OAUTH-0, Sprint OAUTH-6)
    try:
        diagnostics["github_connected"] = settings.load_github_connected()
        github_login = settings.load_github_login()
        diagnostics["github_login"] = github_login if github_login else None
        diagnostics["github_host"] = settings.load_github_host()
        diagnostics["github_user_id"] = settings.load_github_user_id()
        diagnostics["last_verified_at"] = settings.load_last_verified_at()
        # Token presence (yes/no) without exposing token
        try:
            from freecad.gitpdm.auth.token_store_factory import create_token_store

            store = create_token_store()
            token_present = (
                store.load(settings.load_github_host(), settings.load_github_login())
                is not None
            )
            diagnostics["token_present"] = token_present
        except Exception:
            diagnostics["token_present"] = False

        # Last API error (Sprint OAUTH-6)
        code, msg = settings.load_last_api_error()
        diagnostics["last_api_error_code"] = code or None
        diagnostics["last_api_error_message"] = msg or None

        # Cache statistics (Sprint OAUTH-6)
        try:
            from freecad.gitpdm.github.cache import get_github_api_cache

            cache = get_github_api_cache()
            stats = cache.get_stats()
            diagnostics["cache_hits"] = stats.get("hits", 0)
            diagnostics["cache_misses"] = stats.get("misses", 0)
        except Exception:
            diagnostics["cache_hits"] = 0
            diagnostics["cache_misses"] = 0

    except Exception as e:
        diagnostics["github_connected"] = False
        diagnostics["github_login"] = None
        diagnostics["github_host"] = "github.com"
        diagnostics["github_user_id"] = None
        diagnostics["last_verified_at"] = ""
        diagnostics["token_present"] = False
        diagnostics["last_api_error_code"] = None
        diagnostics["last_api_error_message"] = None
        diagnostics["cache_hits"] = 0
        diagnostics["cache_misses"] = 0
        log.warning(f"Failed to load GitHub settings: {e}")

    return diagnostics


def format_diagnostics(diagnostics=None):
    """
    Format diagnostics as human-readable text.

    Args:
        diagnostics: dict from get_diagnostics() (or None to fetch)

    Returns:
        str: Formatted diagnostic report
    """
    if diagnostics is None:
        diagnostics = get_diagnostics()

    lines = []
    lines.append("=== GitPDM Diagnostics ===")
    lines.append("")

    lines.append("Platform:")
    lines.append(f"  System: {diagnostics.get('platform_system')}")
    lines.append(f"  Release: {diagnostics.get('platform_release')}")
    lines.append(f"  Platform: {diagnostics.get('platform')}")
    lines.append("")

    lines.append("Python:")
    py_ver = diagnostics.get("python_version", "Unknown")
    # Show just version line, not full details
    first_line = py_ver.split("\n")[0] if py_ver else "Unknown"
    lines.append(f"  Version: {first_line}")
    lines.append("")

    lines.append("FreeCAD:")
    lines.append(f"  Version: {diagnostics.get('freecad_version')}")
    lines.append(f"  Build: {diagnostics.get('freecad_build')}")
    lines.append("")

    lines.append("Qt:")
    lines.append(f"  Binding: {diagnostics.get('qt_binding')}")
    lines.append(f"  Version: {diagnostics.get('qt_version')}")
    lines.append("")

    lines.append("Git:")
    lines.append(f"  Available: {diagnostics.get('git_available')}")
    lines.append(f"  Version: {diagnostics.get('git_version')}")
    lines.append("")

    lines.append("Repository:")
    lines.append(f"  Configured: {diagnostics.get('repo_path_configured')}")
    lines.append("")

    lines.append("GitHub OAuth:")
    lines.append(
        f"  Client ID configured: {diagnostics.get('oauth_client_id_configured')}"
    )
    lines.append(f"  Connected: {diagnostics.get('github_connected')}")
    github_login = diagnostics.get("github_login")
    lines.append(f"  Login: {github_login if github_login else 'None'}")
    lines.append(f"  Host: {diagnostics.get('github_host')}")
    lines.append(f"  Token present: {diagnostics.get('token_present')}")
    uid = diagnostics.get("github_user_id")
    lines.append(f"  User ID: {uid if uid is not None else 'None'}")
    lv = diagnostics.get("last_verified_at")
    lines.append(f"  Last verified: {lv if lv else 'Never'}")
    lec = diagnostics.get("last_api_error_code")
    lem = diagnostics.get("last_api_error_message")
    if lec or lem:
        lines.append("  Last API error:")
        lines.append(f"    Code: {lec if lec else 'Unknown'}")
        lines.append(f"    Message: {lem if lem else ''}")

    # Cache statistics (Sprint OAUTH-6)
    lines.append("Cache:")
    lines.append(f"  Hits: {diagnostics.get('cache_hits', 0)}")
    lines.append(f"  Misses: {diagnostics.get('cache_misses', 0)}")

    lines.append("")

    lines.append("=== End Diagnostics ===")

    return "\n".join(lines)


def print_diagnostics():
    """
    Print diagnostics to FreeCAD console.
    Useful for troubleshooting and support.
    """
    diagnostics = get_diagnostics()
    report = format_diagnostics(diagnostics)
    log.info(report)
    return report
