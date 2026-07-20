# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
GitLab project (repository) creation via POST /projects.

GitLab's request/response shape differs from GitHub's: `visibility` is a
three-way enum (private/internal/public) rather than a boolean, there's no
`auto_init` flag (GitLab's equivalent is `initialize_with_readme`, also
left False so GitPDM inits locally), and the response's full-name/clone-URL
fields are named `path_with_namespace`/`http_url_to_repo` rather than
`full_name`/`clone_url`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from freecad_gitpdm.core import log
from freecad_gitpdm.providers.gitlab.api_client import GitLabApiClient
from freecad_gitpdm.providers.gitlab.errors import GitLabApiError
from freecad_gitpdm.providers.shared.errors import ProviderApiNetworkError

# GitLab project-path rules: must start with a letter, digit, or
# underscore; may contain letters, digits, underscores, dots, dashes;
# can't end with .git or .atom (reserved suffixes).
_NAME_RE = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_.\-]*$")


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
    client: GitLabApiClient,
    req: CreateRepoRequest,
) -> CreatedRepoInfo:
    if not req.name or not req.name.strip():
        raise GitLabApiError(code="BAD_RESPONSE", message="Repository name is required")

    if not _NAME_RE.match(req.name) or req.name.endswith((".git", ".atom")):
        raise GitLabApiError(
            code="BAD_RESPONSE",
            message=(
                f"Invalid repository name '{req.name}'. Use letters, numbers, "
                "dash, dot, or underscore; don't end with .git or .atom."
            ),
        )

    body = {
        "name": req.name,
        "visibility": "private" if req.private else "public",
        "initialize_with_readme": False,
    }
    if req.description and req.description.strip():
        body["description"] = req.description.strip()

    try:
        status, response_json, headers = client.request_json(
            method="POST",
            url="/projects",
            headers=None,
            body=body,
            timeout_s=30,
        )
    except ProviderApiNetworkError as e:
        log.error(f"Network error creating GitLab project: {e}")
        raise

    if status < 200 or status >= 300:
        if status == 400 and response_json:
            # GitLab reports validation errors keyed by field, e.g.
            # {"message": {"name": ["has already been taken"]}}
            message_field = response_json.get("message")
            if isinstance(message_field, dict) and "name" in message_field:
                raise GitLabApiError(
                    code="BAD_RESPONSE",
                    status=status,
                    message=f"Repository '{req.name}' already exists or is invalid. "
                    "Try a different name.",
                )
        raise GitLabApiError.from_http_error(
            status, headers, str(response_json) if response_json else ""
        )

    if not response_json or not isinstance(response_json, dict):
        raise GitLabApiError(
            code="BAD_RESPONSE", message="Invalid response from GitLab API"
        )

    try:
        repo_info = CreatedRepoInfo(
            full_name=response_json.get("path_with_namespace") or "",
            html_url=response_json.get("web_url") or "",
            clone_url=response_json.get("http_url_to_repo") or "",
            default_branch=response_json.get("default_branch"),
        )
        if not repo_info.full_name or not repo_info.clone_url:
            raise GitLabApiError(
                code="BAD_RESPONSE", message="Incomplete response from GitLab API"
            )
        log.info(f"GitLab project created: {repo_info.full_name}")
        return repo_info
    except (KeyError, AttributeError, TypeError) as e:
        log.error(f"Failed to parse GitLab project creation response: {e}")
        raise GitLabApiError(
            code="BAD_RESPONSE", message="Invalid response format from GitLab API"
        )
