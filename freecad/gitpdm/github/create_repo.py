"""
GitHub Repository Creation
Sprint OAUTH-4: Create user repositories on GitHub
Sprint OAUTH-6: Structured error handling

Implements POST /user/repos via GitHub REST API with error handling.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from freecad.gitpdm.core import log
from freecad.gitpdm.github.api_client import GitHubApiClient
from freecad.gitpdm.github.errors import GitHubApiError, GitHubApiNetworkError


@dataclass
class CreateRepoRequest:
    """Request to create a new repository."""

    name: str
    private: bool
    description: Optional[str] = None
    auto_init: bool = False  # Must be False; we init locally


@dataclass
class CreatedRepoInfo:
    """Response data from successful repo creation."""

    full_name: str
    html_url: str
    clone_url: str
    default_branch: Optional[str]


def create_user_repo(
    client: GitHubApiClient,
    req: CreateRepoRequest,
) -> CreatedRepoInfo:
    """
    Create a new repository on GitHub for the authenticated user.

    Calls POST https://api.github.com/user/repos with:
      {
        "name": <name>,
        "private": <private>,
        "description": <description> (optional),
        "auto_init": false
      }

    Args:
        client: GitHubApiClient instance
        req: CreateRepoRequest with name, private, etc.

    Returns:
        CreatedRepoInfo on success

    Raises:
        GitHubApiError: On HTTP error, auth failure, or repo already exists
        GitHubApiNetworkError: On network connectivity issues
    """
    if not req.name or not req.name.strip():
        raise GitHubApiError("Repository name is required")

    # Validate repo name (simple check: letters, numbers, ., -, _)
    import re

    if not re.match(r"^[a-zA-Z0-9._-]+$", req.name):
        raise GitHubApiError(
            f"Invalid repository name '{req.name}'. "
            "Use letters, numbers, dash, dot, or underscore."
        )

    # Build request body
    body = {
        "name": req.name,
        "private": bool(req.private),
        "auto_init": False,  # Must be False; we init locally
    }

    if req.description and req.description.strip():
        body["description"] = req.description.strip()

    # Make request
    try:
        status, response_json, headers = client.request_json(
            method="POST",
            url="/user/repos",
            headers=None,
            body=body,
            timeout_s=30,
        )
    except GitHubApiNetworkError as e:
        log.error(f"Network error creating repo: {e}")
        raise

    # Handle error responses
    if status < 200 or status >= 300:
        if status == 422:
            # Unprocessable Entity - typically name already exists
            try:
                errors = response_json.get("errors", []) if response_json else []
                for err in errors:
                    if err.get("field") == "name":
                        raise GitHubApiError(
                            f"Repository '{req.name}' already exists. "
                            "Try a different name."
                        )
            except (AttributeError, TypeError):
                pass
            raise GitHubApiError(
                "Repository creation failed (422). Check name is unique and valid."
            )
        elif status == 401:
            log.warning("Unauthorized: token may have expired")
            raise GitHubApiError(
                "Authentication failed. "
                "Your session may have expired. "
                "Reconnect GitHub and try again."
            )
        elif status == 403:
            # Check rate limit
            remaining = headers.get("X-RateLimit-Remaining") or headers.get(
                "x-ratelimit-remaining"
            )
            if remaining is not None and str(remaining) == "0":
                raise GitHubApiError(
                    "GitHub rate limit reached. Wait a moment and try again."
                )
            raise GitHubApiError(
                "Permission denied. Check that your token has repo creation scope."
            )
        else:
            raise GitHubApiError(
                f"Failed to create repository (HTTP {status}). "
                "Check your internet connection and try again."
            )

    # Parse success response
    if not response_json or not isinstance(response_json, dict):
        raise GitHubApiError("Invalid response from GitHub API")

    try:
        repo_info = CreatedRepoInfo(
            full_name=response_json.get("full_name") or "",
            html_url=response_json.get("html_url") or "",
            clone_url=response_json.get("clone_url") or "",
            default_branch=response_json.get("default_branch"),
        )

        if not repo_info.full_name or not repo_info.clone_url:
            raise GitHubApiError("Incomplete response from GitHub API")

        log.info(f"Repository created: {repo_info.full_name}")
        return repo_info

    except (KeyError, AttributeError, TypeError) as e:
        log.error(f"Failed to parse repo creation response: {e}")
        raise GitHubApiError("Invalid response format from GitHub API")
