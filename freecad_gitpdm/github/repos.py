# -*- coding: utf-8 -*-
"""
GitHub repositories listing utilities.
Sprint OAUTH-3: List repos with pagination (stdlib-only HTTP).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from freecad_gitpdm.core import log
from freecad_gitpdm.github.api_client import (
    GitHubApiClient,
    GitHubApiError,
    GitHubApiNetworkError,
)


@dataclass
class RepoInfo:
    owner: str
    name: str
    full_name: str
    private: bool
    default_branch: Optional[str]
    clone_url: str
    updated_at: Optional[str]


def _extract_next_link(headers: dict) -> Optional[str]:
    """Parse the HTTP Link header and return the rel="next" URL if present."""
    if not headers:
        return None

    link_header = None
    for k, v in headers.items():
        if k.lower() == "link":
            link_header = v
            break
    if not link_header:
        return None

    parts = link_header.split(",")
    for part in parts:
        section = part.split(";")
        if len(section) < 2:
            continue
        url_part = section[0].strip()
        rel_part = ";".join(section[1:]).strip().lower()
        if "rel=\"next\"" in rel_part:
            if url_part.startswith("<") and url_part.endswith(">"):
                return url_part[1:-1]
            return url_part
    return None


def _classify_error(status: int, headers: dict) -> GitHubApiError:
    """Return a user-friendly GitHubApiError for the status code."""
    if status == 401:
        return GitHubApiError("Not authorized. Reconnect GitHub and try again.")
    if status == 403:
        try:
            remaining = headers.get("X-RateLimit-Remaining") or headers.get("x-ratelimit-remaining")
            if remaining is not None and str(remaining) == "0":
                return GitHubApiError("GitHub rate limit reached. Try again later.")
        except Exception:
            pass
        return GitHubApiError("Access forbidden. Check token scopes and permissions.")
    if status >= 500:
        return GitHubApiError("GitHub is unavailable right now. Please retry.")
    return GitHubApiError(f"GitHub API returned status {status}")


def list_repos(
    client: GitHubApiClient,
    per_page: int = 100,
    max_pages: int = 10,
) -> List[RepoInfo]:
    """
    List repositories the viewer can access via GitHub REST API.

    - Uses GET /user/repos with affiliation + visibility filters.
    - Paginates using the Link header.
    - Raises GitHubApiError for HTTP failures with friendly messages.
    """
    results: List[RepoInfo] = []

    if per_page <= 0 or per_page > 100:
        per_page = 100
    if max_pages <= 0:
        max_pages = 1

    url = (
        f"/user/repos?per_page={per_page}"
        "&sort=updated&direction=desc"
        "&affiliation=owner,collaborator,organization_member"
        "&visibility=all"
    )

    page = 0
    while url and page < max_pages:
        page += 1
        try:
            status, js, headers = client.request_json(
                "GET", url, headers=None, body=None, timeout_s=15
            )
        except GitHubApiNetworkError:
            raise
        except Exception as e:
            raise GitHubApiError(f"Request failed: {e}") from e

        if status < 200 or status >= 300:
            raise _classify_error(status, headers or {})

        if not isinstance(js, list):
            log.warning("Unexpected GitHub response payload; expected list")
            js_items = []
        else:
            js_items = js

        for item in js_items:
            try:
                owner = ""
                full_name = item.get("full_name") or ""
                if not full_name:
                    owner_obj = item.get("owner") or {}
                    owner = owner_obj.get("login") or ""
                    name = item.get("name") or ""
                    full_name = f"{owner}/{name}".strip("/")
                else:
                    owner = full_name.split("/", 1)[0] if "/" in full_name else full_name

                repo = RepoInfo(
                    owner=owner,
                    name=item.get("name") or full_name.split("/")[-1],
                    full_name=full_name,
                    private=bool(item.get("private", False)),
                    default_branch=item.get("default_branch"),
                    clone_url=item.get("clone_url") or "",
                    updated_at=item.get("updated_at"),
                )
                results.append(repo)
            except Exception as parse_err:
                log.debug(f"Skipping repo entry due to parse error: {parse_err}")
                continue

        url = _extract_next_link(headers or {})

    return results
