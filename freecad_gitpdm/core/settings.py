# -*- coding: utf-8 -*-
"""
GitPDM Settings Module
Sprint 2: Persist settings using FreeCAD parameter store
"""

from __future__ import annotations

from freecad_gitpdm.core import log

# Parameter group path in FreeCAD's parameter tree
PARAM_GROUP_PATH = "User parameter:BaseApp/Preferences/Mod/GitPDM"

# FreeCAD's own document-save preferences (not GitPDM-specific).
# CompressionLevel controls the zlib deflate level used when zipping .FCStd
# files (0 = store/no compression, 9 = max). It's a global FreeCAD
# preference, not per-repo or per-document.
DOCUMENT_PARAM_GROUP_PATH = "User parameter:BaseApp/Preferences/Document"
GIT_FRIENDLY_COMPRESSION_LEVEL = 0


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


def get_fcstd_compression_level():
    """
    Read FreeCAD's current .FCStd save compression level (0-9).

    Returns:
        int | None: current level, or None if it couldn't be read
    """
    try:
        import FreeCAD

        param_group = FreeCAD.ParamGet(DOCUMENT_PARAM_GROUP_PATH)
        return param_group.GetInt("CompressionLevel", 3)
    except Exception as e:
        log.error(f"Failed to read FCStd compression level: {e}")
        return None


# --- G3: repo-scoped compression, not a silent global flip (R1.2) ---
#
# CompressionLevel is a global FreeCAD preference with no per-document
# override in the public API, so the only window we can shrink without
# touching FreeCAD internals is the save call itself: FreeCAD notifies
# document observers via slotStartSaveDocument/slotFinishSaveDocument
# around each save, and CompressionLevel is read at serialization time
# inside that window. Scoping to the save call (rather than "while a
# GitPDM repo is open") is *tighter* than the requirement asks for and
# fully satisfies it: saves of any other document, even ones open at the
# same time, are never affected. See ui/panel.py's _DocumentObserver for
# the call sites.
_PRIOR_COMPRESSION_KEY = "PriorCompressionLevelBeforeGitPDM"
_COMPRESSION_SCOPE_ACTIVE_KEY = "CompressionScopeActive"


def enter_git_friendly_compression_scope():
    """
    Record the current global compression level (once per scope) and set
    it to 0 (store, no deflate) so an imminent .FCStd save is git-friendly.

    .FCStd files are ZIP archives. Deflate compression makes even a small
    model edit rewrite most of the archive's bytes, so Git can't diff or
    delta-compress saves meaningfully. Storing entries uncompressed keeps
    unchanged internal files byte-identical across saves, so Git's own pack
    compression can actually do its job.

    Must be paired with exit_git_friendly_compression_scope() once the
    save completes, to restore the user's prior global preference.
    """
    try:
        import FreeCAD

        if not load_bool_setting(_COMPRESSION_SCOPE_ACTIVE_KEY, False):
            current = get_fcstd_compression_level()
            if current is None:
                return
            save_setting(_PRIOR_COMPRESSION_KEY, str(current))
            save_bool_setting(_COMPRESSION_SCOPE_ACTIVE_KEY, True)

        param_group = FreeCAD.ParamGet(DOCUMENT_PARAM_GROUP_PATH)
        if param_group.GetInt("CompressionLevel", 3) != GIT_FRIENDLY_COMPRESSION_LEVEL:
            param_group.SetInt("CompressionLevel", GIT_FRIENDLY_COMPRESSION_LEVEL)
            log.info(
                "Set FreeCAD document compression level to 0 (store) for this "
                "git-friendly .FCStd save; will restore afterward"
            )
    except Exception as e:
        log.error(f"Failed to enter git-friendly compression scope: {e}")


def exit_git_friendly_compression_scope():
    """
    Restore the global compression level recorded by
    enter_git_friendly_compression_scope(). No-op if no scope is active,
    so it is always safe to call unconditionally after a save completes.
    """
    if not load_bool_setting(_COMPRESSION_SCOPE_ACTIVE_KEY, False):
        return
    try:
        import FreeCAD

        prior_raw = load_setting(_PRIOR_COMPRESSION_KEY, "")
        prior = int(prior_raw) if prior_raw != "" else 3
        param_group = FreeCAD.ParamGet(DOCUMENT_PARAM_GROUP_PATH)
        param_group.SetInt("CompressionLevel", prior)
        log.info(f"Restored FreeCAD document compression level to {prior}")
    except Exception as e:
        log.error(f"Failed to restore compression level: {e}")
    finally:
        save_bool_setting(_COMPRESSION_SCOPE_ACTIVE_KEY, False)
        save_setting(_PRIOR_COMPRESSION_KEY, "")


def recover_stuck_compression_scope():
    """
    If a previous session crashed mid-save (leaving the compression scope
    flagged active with no matching exit call), restore the recorded prior
    value now instead of leaving the user's global preference pinned at 0
    indefinitely. Meant to be called once during startup/deferred init.
    """
    if load_bool_setting(_COMPRESSION_SCOPE_ACTIVE_KEY, False):
        log.warning(
            "Found a GitPDM compression scope left active from a previous "
            "session (likely interrupted mid-save); restoring prior "
            "compression level"
        )
        exit_git_friendly_compression_scope()


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


# --- Multi-provider connection settings ---
#
# Every provider gets its own namespaced set of connection-state keys, so
# e.g. a GitLab connection doesn't collide with or overwrite a GitHub one -
# a user (or a repo) can have both connected at once. GitHub's original
# Sprint OAUTH-0/OAUTH-2 functions below are kept as thin wrappers around
# these, calling with provider_id="github" - the underlying parameter-store
# keys ("GitHubConnected", "GitHubLogin", etc.) are unchanged, so existing
# stored settings load exactly as before with zero migration.

_PROVIDER_KEY_PREFIXES = {
    "github": "GitHub",
    "gitlab": "GitLab",
    "gitea": "Gitea",
    "bitbucket": "Bitbucket",
    "sourcehut": "SourceHut",
}


def _provider_key_prefix(provider_id: str) -> str:
    """Parameter-store key prefix for a provider's connection-state
    settings. Providers not in the explicit map above (there shouldn't be
    any, but this keeps a new provider from crashing settings lookups
    before someone remembers to add it here) fall back to a capitalized
    provider_id."""
    return _PROVIDER_KEY_PREFIXES.get(provider_id, (provider_id or "").capitalize())


def save_provider_connected(provider_id: str, connected: bool):
    """Save a provider's connection status (metadata only, no tokens)."""
    save_bool_setting(f"{_provider_key_prefix(provider_id)}Connected", bool(connected))


def load_provider_connected(provider_id: str) -> bool:
    """Load a provider's connection status."""
    return load_bool_setting(f"{_provider_key_prefix(provider_id)}Connected", False)


def save_provider_login(provider_id: str, login):
    """Save a provider's username (metadata only, no tokens)."""
    save_setting(f"{_provider_key_prefix(provider_id)}Login", login or "")


def load_provider_login(provider_id: str):
    """Load a provider's username. Returns None if unset."""
    login = load_setting(f"{_provider_key_prefix(provider_id)}Login", "")
    return login if login else None


def save_provider_host(provider_id: str, host, default_host: str = ""):
    """Save a provider's host (e.g. for GitHub Enterprise, or a
    self-hosted Gitea/Forgejo instance's server URL)."""
    save_setting(f"{_provider_key_prefix(provider_id)}Host", host or default_host)


def load_provider_host(provider_id: str, default_host: str = "") -> str:
    """Load a provider's host."""
    return load_setting(f"{_provider_key_prefix(provider_id)}Host", default_host)


def save_provider_user_id(provider_id: str, user_id: int | None):
    """Save a provider's user id (metadata only)."""
    try:
        value = "" if user_id is None else str(int(user_id))
        save_setting(f"{_provider_key_prefix(provider_id)}UserId", value)
    except (TypeError, ValueError):
        save_setting(f"{_provider_key_prefix(provider_id)}UserId", "")


def load_provider_user_id(provider_id: str) -> int | None:
    """Load a provider's user id (int or None)."""
    raw = load_setting(f"{_provider_key_prefix(provider_id)}UserId", "")
    try:
        return int(raw) if raw else None
    except ValueError:
        return None


def save_provider_last_verified_at(provider_id: str, ts_iso: str | None):
    """Save a provider's last successful identity verification timestamp (ISO)."""
    save_setting(f"{_provider_key_prefix(provider_id)}LastVerifiedAt", ts_iso or "")


def load_provider_last_verified_at(provider_id: str) -> str:
    """Load a provider's last successful identity verification timestamp."""
    return load_setting(f"{_provider_key_prefix(provider_id)}LastVerifiedAt", "")


def save_provider_last_api_error(
    provider_id: str, code: str | None, message: str | None
):
    """Persist a provider's last API error classification (no secrets)."""
    prefix = _provider_key_prefix(provider_id)
    save_setting(f"{prefix}LastApiErrorCode", code or "")
    save_setting(f"{prefix}LastApiErrorMessage", message or "")


def load_provider_last_api_error(provider_id: str):
    """Return tuple (code, message) for a provider's last API error."""
    prefix = _provider_key_prefix(provider_id)
    code = load_setting(f"{prefix}LastApiErrorCode", "")
    msg = load_setting(f"{prefix}LastApiErrorMessage", "")
    return (code or "", msg or "")


# --- Sprint OAUTH-0: GitHub OAuth settings (metadata only) ---
# Thin wrappers over the provider-namespaced functions above, kept for
# backward compatibility with existing callers (ui/github_auth.py etc.) -
# same storage keys as before, zero behavior change for existing users.


def save_github_connected(connected):
    """Save GitHub connection status (metadata only, no tokens)."""
    save_provider_connected("github", connected)


def load_github_connected():
    """Load GitHub connection status."""
    return load_provider_connected("github")


def save_github_login(login):
    """Save GitHub username (metadata only, no tokens)."""
    save_provider_login("github", login)


def load_github_login():
    """Load GitHub username."""
    return load_provider_login("github")


def save_github_host(host):
    """Save GitHub host (supports GitHub Enterprise)."""
    save_provider_host("github", host, default_host="github.com")


def load_github_host():
    """Load GitHub host."""
    return load_provider_host("github", default_host="github.com")


# --- Sprint OAUTH-2: Session verification metadata ---


def save_github_user_id(user_id: int | None):
    """Save GitHub user id (metadata only)."""
    save_provider_user_id("github", user_id)


def load_github_user_id() -> int | None:
    """Load GitHub user id (int or None)."""
    return load_provider_user_id("github")


def save_last_verified_at(ts_iso: str | None):
    """Save last successful identity verification timestamp (ISO)."""
    save_provider_last_verified_at("github", ts_iso)


def load_last_verified_at() -> str:
    """Load last successful identity verification timestamp (ISO string or empty)."""
    return load_provider_last_verified_at("github")


def save_last_api_error(code: str | None, message: str | None):
    """Persist last API error classification (no secrets)."""
    save_provider_last_api_error("github", code, message)


def load_last_api_error():
    """Return tuple (code, message) for last API error."""
    return load_provider_last_api_error("github")
