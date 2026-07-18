# -*- coding: utf-8 -*-
"""
GitPDM per-repo provider selection (Phase G4, R5.1/R5.3).

Stores which git host a repo talks to in `.freecad-pdm/config.json`
(the same config-file mechanism `core/storage_mode.py` uses for storage
mode, and `export/preset.py` uses for export presets) so two repos with
different providers open in one FreeCAD session don't fight over global
state.

    {
      "provider": "github" | "generic" | "gitlab",
      "remoteHost": "github.example.com"   # optional, for GitHub Enterprise etc.
    }

Missing or malformed config defaults to "github" — every repo GitPDM has
ever created predates this field, so treating an absent value as anything
else would silently change behavior for existing users.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from freecad_gitpdm.core import log

CONFIG_DIR = ".freecad-pdm"
CONFIG_FILE = "config.json"

DEFAULT_PROVIDER_ID = "github"

_KNOWN_PROVIDER_IDS = {"github", "generic", "gitlab", "gitea", "bitbucket"}


def _config_path(repo_root: str) -> str:
    return os.path.join(repo_root, CONFIG_DIR, CONFIG_FILE)


def _read_config(repo_root: str) -> dict:
    path = _config_path(repo_root)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError) as e:
        log.warning(f"Could not read {CONFIG_DIR}/{CONFIG_FILE} ({e}); using defaults")
        return {}


def get_provider_id(repo_root: str) -> str:
    """Return the repo's configured provider id, defaulting to 'github'."""
    provider_id = (_read_config(repo_root).get("provider") or "").strip().lower()
    if provider_id not in _KNOWN_PROVIDER_IDS:
        return DEFAULT_PROVIDER_ID
    return provider_id


def get_remote_host(repo_root: str) -> Optional[str]:
    """Return the repo's configured remote host override, if any."""
    host = _read_config(repo_root).get("remoteHost")
    return host.strip() if isinstance(host, str) and host.strip() else None


def set_provider_config(
    repo_root: str,
    provider_id: str,
    remote_host: Optional[str] = None,
) -> None:
    """Write the repo's provider selection, preserving any other config keys."""
    provider_id = (provider_id or "").strip().lower()
    if provider_id not in _KNOWN_PROVIDER_IDS:
        raise ValueError(
            f"Unknown provider id '{provider_id}'; expected one of {sorted(_KNOWN_PROVIDER_IDS)}"
        )

    config_dir = os.path.join(repo_root, CONFIG_DIR)
    os.makedirs(config_dir, exist_ok=True)

    data = _read_config(repo_root)
    data["provider"] = provider_id
    if remote_host:
        data["remoteHost"] = remote_host.strip()
    else:
        data.pop("remoteHost", None)

    with open(_config_path(repo_root), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    log.info(f"Repo provider set to '{provider_id}'")
