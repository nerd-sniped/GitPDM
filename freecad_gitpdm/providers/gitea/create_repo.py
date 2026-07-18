# -*- coding: utf-8 -*-
"""
Gitea/Forgejo repository creation via POST /user/repos.

Gitea's API was deliberately designed to be GitHub-API-compatible, so this
request/response shape (and field names: `full_name`, `html_url`,
`clone_url`, `default_branch`) is nearly identical to GitHub's — this is
the provider where that similarity actually pays off.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from freecad_gitpdm.core import log
from freecad_gitpdm.providers.gitea.api_client import GiteaApiClient
from freecad_gitpdm.providers.gitea.errors import GiteaApiError
from freecad_gitpdm.providers.shared.errors import ProviderApiNetworkError

_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


@dataclass
class CreateRepoRequest:
    name: str
    private: bool
    description: Optional[str] = None


@dataclass
class CreatedRepoInfo:
    full_name: str
    html_url: str
    clone_url: str
    default_branch: Optional[str]


def create_user_repo(
    client: GiteaApiClient,
    req: CreateRepoRequest,
) -> CreatedRepoInfo:
    if not req.name or not req.name.strip():
        raise GiteaApiError(code="BAD_RESPONSE", message="Repository name is required")

    if not _NAME_RE.match(req.name):
        raise GiteaApiError(
            code="BAD_RESPONSE",
            message=f"Invalid repository name '{req.name}'. "
            "Use letters, numbers, dash, dot, or underscore.",
        )

    body = {
        "name": req.name,
        "private": bool(req.private),
        "auto_init": False,
    }
    if req.description and req.description.strip():
        body["description"] = req.description.strip()

    try:
        status, response_json, headers = client.request_json(
            method="POST",
            url="/user/repos",
            headers=None,
            body=body,
            timeout_s=30,
        )
    except ProviderApiNetworkError as e:
        log.error(f"Network error creating Gitea repo: {e}")
        raise

    if status < 200 or status >= 300:
        if status == 409:
            raise GiteaApiError(
                code="BAD_RESPONSE",
                status=status,
                message=f"Repository '{req.name}' already exists. Try a different name.",
            )
        raise GiteaApiError.from_http_error(
            status, headers, str(response_json) if response_json else ""
        )

    if not response_json or not isinstance(response_json, dict):
        raise GiteaApiError(
            code="BAD_RESPONSE", message="Invalid response from the server"
        )

    try:
        repo_info = CreatedRepoInfo(
            full_name=response_json.get("full_name") or "",
            html_url=response_json.get("html_url") or "",
            clone_url=response_json.get("clone_url") or "",
            default_branch=response_json.get("default_branch"),
        )
        if not repo_info.full_name or not repo_info.clone_url:
            raise GiteaApiError(
                code="BAD_RESPONSE", message="Incomplete response from the server"
            )
        log.info(f"Gitea repository created: {repo_info.full_name}")
        return repo_info
    except (KeyError, AttributeError, TypeError) as e:
        log.error(f"Failed to parse Gitea repo creation response: {e}")
        raise GiteaApiError(
            code="BAD_RESPONSE", message="Invalid response format from the server"
        )
