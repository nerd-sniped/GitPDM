# -*- coding: utf-8 -*-
"""
GitPDM Settings Module
Sprint 2: Persist settings using FreeCAD parameter store
"""

from freecad_gitpdm.core import log

# Parameter group path in FreeCAD's parameter tree
PARAM_GROUP_PATH = "User parameter:BaseApp/Preferences/Mod/GitPDM"


def get_param_group():
    """
    Get the FreeCAD parameter group for GitPDM settings

    Returns:
        ParameterGrp object for GitPDM settings
    """
    import FreeCAD

    return FreeCAD.ParamGet(PARAM_GROUP_PATH)


def save_repo_path(path):
    """
    Save the repository path to persistent storage

    Args:
        path: Repository path string
    """
    try:
        param_group = get_param_group()
        param_group.SetString("RepoPath", path)
        log.info(f"Saved repo path: {path}")
    except Exception as e:
        log.error(f"Failed to save repo path: {e}")


def load_repo_path():
    """
    Load the repository path from persistent storage

    Returns:
        Repository path string (empty if not set)
    """
    try:
        param_group = get_param_group()
        path = param_group.GetString("RepoPath", "")
        if path:
            log.info(f"Loaded repo path: {path}")
        return path
    except Exception as e:
        log.error(f"Failed to load repo path: {e}")
        return ""


def save_setting(key, value):
    """
    Save a generic string setting

    Args:
        key: Setting key name
        value: Setting value (string)
    """
    try:
        param_group = get_param_group()
        param_group.SetString(key, str(value))
        log.debug(f"Saved setting {key}={value}")
    except Exception as e:
        log.error(f"Failed to save setting {key}: {e}")


def load_setting(key, default=""):
    """
    Load a generic string setting

    Args:
        key: Setting key name
        default: Default value if not found

    Returns:
        Setting value string
    """
    try:
        param_group = get_param_group()
        return param_group.GetString(key, default)
    except Exception as e:
        log.error(f"Failed to load setting {key}: {e}")
        return default


def save_bool_setting(key, value):
    """
    Save a boolean setting

    Args:
        key: Setting key name
        value: Boolean value
    """
    try:
        param_group = get_param_group()
        param_group.SetBool(key, bool(value))
        log.debug(f"Saved bool setting {key}={value}")
    except Exception as e:
        log.error(f"Failed to save bool setting {key}: {e}")


def load_bool_setting(key, default=False):
    """
    Load a boolean setting

    Args:
        key: Setting key name
        default: Default value if not found

    Returns:
        Boolean value
    """
    try:
        param_group = get_param_group()
        return param_group.GetBool(key, default)
    except Exception as e:
        log.error(f"Failed to load bool setting {key}: {e}")
        return default


def save_remote_name(remote):
    """
    Save the remote name to persistent storage

    Args:
        remote: Remote name string (e.g., "origin")
    """
    save_setting("RemoteName", remote)


def load_remote_name():
    """
    Load the remote name from persistent storage

    Returns:
        Remote name string (default "origin")
    """
    return load_setting("RemoteName", "origin")


def save_last_fetch_at(timestamp):
    """
    Save the last fetch timestamp to persistent storage.
    MVP: Single timestamp for current repo.
    Future: Per-repo timestamps using repo root as key.

    Args:
        timestamp: ISO 8601 timestamp string
    """
    save_setting("LastFetchAt", timestamp)


def load_last_fetch_at():
    """
    Load the last fetch timestamp from persistent storage

    Returns:
        ISO 8601 timestamp string (empty if not set)
    """
    return load_setting("LastFetchAt", "")


def save_last_pull_at(timestamp):
    """
    Save the last pull timestamp to persistent storage.
    MVP: Single timestamp for current repo.
    Future: Per-repo timestamps using repo root as key.

    Args:
        timestamp: ISO 8601 timestamp string
    """
    save_setting("LastPullAt", timestamp)


def load_last_pull_at():
    """
    Load the last pull timestamp from persistent storage

    Returns:
        ISO 8601 timestamp string (empty if not set)
    """
    return load_setting("LastPullAt", "")


# --- Sprint 6: Preview export settings ---


def save_last_preview_at(timestamp):
    """
    Save the last preview generation timestamp (ISO 8601 UTC).
    MVP: Single timestamp; future may use per-repo keys.
    """
    save_setting("LastPreviewAt", timestamp)


def load_last_preview_at():
    """
    Load last preview generation timestamp.
    """
    return load_setting("LastPreviewAt", "")


def save_last_preview_dir(rel_dir):
    """Save last preview output repo-relative directory."""
    save_setting("LastPreviewDir", rel_dir or "")


def load_last_preview_dir():
    """Load last preview output repo-relative directory."""
    return load_setting("LastPreviewDir", "")


def load_stage_previews_default_on():
    """
    Load whether to stage preview files after export.
    Default ON.
    """
    return load_bool_setting("StagePreviews", True)


def save_stage_previews(value):
    """Persist staging preference."""
    save_bool_setting("StagePreviews", bool(value))


# --- Sprint 5: CAD extensions configuration ---

_DEFAULT_CAD_EXT_STR = ".FCStd;.STEP;.STP;.IGES;.IGS;.STL;.DXF;.SVG"


def _normalize_ext(ext):
    """
    Normalize a single extension string.
    Ensures leading dot and lower-case for matching.
    """
    if not ext:
        return ""
    e = ext.strip()
    if not e:
        return ""
    if not e.startswith("."):
        e = "." + e
    return e.lower()


def load_cad_extensions():
    """
    Load configured CAD file extensions.

    Returns:
        list[str]: normalized extensions (lower-case, with leading dot)
    """
    raw = load_setting("cad_extensions", _DEFAULT_CAD_EXT_STR)
    parts = [p for p in raw.split(";") if p]
    normalized = []
    for p in parts:
        n = _normalize_ext(p)
        if n and n not in normalized:
            normalized.append(n)
    if not normalized:
        # Fallback to default if parsing produced empty list
        for p in _DEFAULT_CAD_EXT_STR.split(";"):
            n = _normalize_ext(p)
            if n and n not in normalized:
                normalized.append(n)
    return normalized


def save_cad_extensions(ext_list):
    """
    Save CAD file extensions.

    Args:
        ext_list: list[str] of extensions; case preserved in storage

    Notes:
        - Stored as semicolon-separated string in parameter group.
        - Matching uses normalized (lower-case) values at load-time.
    """
    try:
        # Store as given, but ensure leading dots and trim spaces
        cleaned = []
        for e in ext_list or []:
            s = e.strip()
            if not s:
                continue
            if not s.startswith("."):
                s = "." + s
            cleaned.append(s)
        value = ";".join(cleaned) if cleaned else _DEFAULT_CAD_EXT_STR
        save_setting("cad_extensions", value)
        log.info(f"Saved CAD extensions: {value}")
    except Exception as e:
        log.error(f"Failed to save CAD extensions: {e}")


# --- Sprint OAUTH-3: Clone defaults ---


def save_default_clone_dir(path: str):
    """Persist default clone destination directory (user-friendly)."""
    save_setting("DefaultCloneDir", path or "")


def load_default_clone_dir() -> str:
    """Load default clone destination directory (empty string if unset)."""
    return load_setting("DefaultCloneDir", "")


# --- Sprint OAUTH-0: GitHub OAuth settings (metadata only) ---


def save_github_connected(connected):
    """
    Save GitHub connection status (metadata only, no tokens).

    Args:
        connected: bool indicating if user is connected to GitHub
    """
    save_bool_setting("GitHubConnected", bool(connected))


def load_github_connected():
    """
    Load GitHub connection status.

    Returns:
        bool: True if GitHub is connected, False otherwise
    """
    return load_bool_setting("GitHubConnected", False)


def save_github_login(login):
    """
    Save GitHub username (metadata only, no tokens).

    Args:
        login: str GitHub username or None to clear
    """
    save_setting("GitHubLogin", login or "")


def load_github_login():
    """
    Load GitHub username.

    Returns:
        str | None: GitHub username if set, None otherwise
    """
    login = load_setting("GitHubLogin", "")
    return login if login else None


def save_github_host(host):
    """
    Save GitHub host (supports GitHub Enterprise).

    Args:
        host: str GitHub host (e.g., "github.com")
    """
    save_setting("GitHubHost", host or "github.com")


def load_github_host():
    """
    Load GitHub host.

    Returns:
        str: GitHub host (default "github.com")
    """
    return load_setting("GitHubHost", "github.com")


# --- Sprint OAUTH-2: Session verification metadata ---


def save_github_user_id(user_id: int | None):
    """Save GitHub user id (metadata only)."""
    try:
        # Store as string; empty if None
        value = "" if user_id is None else str(int(user_id))
        save_setting("GitHubUserId", value)
    except Exception:
        save_setting("GitHubUserId", "")


def load_github_user_id() -> int | None:
    """Load GitHub user id (int or None)."""
    raw = load_setting("GitHubUserId", "")
    try:
        return int(raw) if raw else None
    except Exception:
        return None


def save_last_verified_at(ts_iso: str | None):
    """Save last successful identity verification timestamp (ISO)."""
    save_setting("GitHubLastVerifiedAt", ts_iso or "")


def load_last_verified_at() -> str:
    """Load last successful identity verification timestamp (ISO string or empty)."""
    return load_setting("GitHubLastVerifiedAt", "")


def save_last_api_error(code: str | None, message: str | None):
    """Persist last API error classification (no secrets)."""
    save_setting("GitHubLastApiErrorCode", (code or ""))
    # Message may be user-facing; store redacted/non-sensitive
    save_setting("GitHubLastApiErrorMessage", (message or ""))


def load_last_api_error():
    """Return tuple (code, message) for last API error."""
    code = load_setting("GitHubLastApiErrorCode", "")
    msg = load_setting("GitHubLastApiErrorMessage", "")
    return (code or "", msg or "")
