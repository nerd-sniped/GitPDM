# -*- coding: utf-8 -*-
"""
Bitbucket Cloud repository creation via POST /2.0/repositories/{workspace}/{slug}.

The one real structural difference from every other provider here:
Bitbucket repos live under a workspace the user must specify (there's no
"just my account" scope), so the repo identifier is a URL path segment
(`{workspace}/{slug}`), not just a name in the request body. `scm: "git"`
must be explicit since Bitbucket historically also supported Mercurial.
Response repo-info fields are nested (`links.html.href`, `links.clone[]`)
rather than flat, unlike GitHub/GitLab/Gitea.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from freecad_gitpdm.core import log
from freecad_gitpdm.providers.bitbucket.api_client import BitbucketApiClient
from freecad_gitpdm.providers.bitbucket.errors import BitbucketApiError
from freecad_gitpdm.providers.shared.errors import ProviderApiNetworkError

_SLUG_INVALID_CHARS = re.compile(r"[^a-z0-9._-]+")


def _slugify(name: str) -> str:
    """Bitbucket repo slugs are lowercase, no spaces. Derived from name,
    not user-entered separately, to keep the wizard's input surface the
    same shape as every other provider (just a name field)."""
    slug = name.strip().lower().replace(" ", "-")
    slug = _SLUG_INVALID_CHARS.sub("-", slug)
    return slug.strip("-") or "repo"


@dataclass
class CreateRepoRequest:
    name: str
    private: bool
    workspace: str
    description: Optional[str] = None


@dataclass
class CreatedRepoInfo:
    full_name: str
    html_url: str
    clone_url: str
    default_branch: Optional[str]


def _extract_https_clone_url(clone_links) -> str:
    if not isinstance(clone_links, list):
        return ""
    for entry in clone_links:
        if isinstance(entry, dict) and entry.get("name") == "https":
            return entry.get("href") or ""
    return ""


def create_user_repo(
    client: BitbucketApiClient,
    req: CreateRepoRequest,
) -> CreatedRepoInfo:
    if not req.name or not req.name.strip():
        raise BitbucketApiError(
            code="BAD_RESPONSE", message="Repository name is required"
        )
    if not req.workspace or not req.workspace.strip():
        raise BitbucketApiError(
            code="BAD_RESPONSE", message="A Bitbucket workspace is required"
        )

    slug = _slugify(req.name)
    body = {
        "scm": "git",
        "name": req.name,
        "is_private": bool(req.private),
    }
    if req.description and req.description.strip():
        body["description"] = req.description.strip()

    try:
        status, response_json, headers = client.request_json(
            method="POST",
            url=f"/repositories/{req.workspace.strip()}/{slug}",
            headers=None,
            body=body,
            timeout_s=30,
        )
    except ProviderApiNetworkError as e:
        log.error(f"Network error creating Bitbucket repo: {e}")
        raise

    if status < 200 or status >= 300:
        if status in (400, 409) and response_json:
            error_obj = response_json.get("error") or {}
            message = error_obj.get("message") or ""
            if "already exist" in message.lower() or "already have" in message.lower():
                raise BitbucketApiError(
                    code="BAD_RESPONSE",
                    status=status,
                    message=f"Repository '{slug}' already exists in workspace "
                    f"'{req.workspace}'. Try a different name.",
                )
        raise BitbucketApiError.from_http_error(
            status, headers, str(response_json) if response_json else ""
        )

    if not response_json or not isinstance(response_json, dict):
        raise BitbucketApiError(
            code="BAD_RESPONSE", message="Invalid response from Bitbucket API"
        )

    try:
        links = response_json.get("links") or {}
        html_link = (links.get("html") or {}).get("href") or ""
        clone_url = _extract_https_clone_url(links.get("clone"))
        mainbranch = response_json.get("mainbranch") or {}

        repo_info = CreatedRepoInfo(
            full_name=response_json.get("full_name") or "",
            html_url=html_link,
            clone_url=clone_url,
            default_branch=mainbranch.get("name"),
        )
        if not repo_info.full_name or not repo_info.clone_url:
            raise BitbucketApiError(
                code="BAD_RESPONSE", message="Incomplete response from Bitbucket API"
            )
        log.info(f"Bitbucket repository created: {repo_info.full_name}")
        return repo_info
    except (KeyError, AttributeError, TypeError) as e:
        log.error(f"Failed to parse Bitbucket repo creation response: {e}")
        raise BitbucketApiError(
            code="BAD_RESPONSE", message="Invalid response format from Bitbucket API"
        )
