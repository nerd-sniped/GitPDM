# -*- coding: utf-8 -*-
"""
GitHub repositories listing utilities.
Sprint OAUTH-3: List repos with pagination (stdlib-only HTTP).
Sprint OAUTH-6: Error handling, retries, caching integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from freecad_gitpdm.core import log
from freecad_gitpdm.github.api_client import GitHubApiClient
from freecad_gitpdm.github.errors import GitHubApiError, GitHubApiNetworkError
from freecad_gitpdm.github.cache import get_github_api_cache


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
        if 'rel="next"' in rel_part:
            if url_part.startswith("<") and url_part.endswith(">"):
                return url_part[1:-1]
            return url_part
    return None


def _classify_error(status: int, headers: dict) -> GitHubApiError:
    """Classify HTTP error using structured error handling."""
    return GitHubApiError.from_http_error(status, headers or {})


def list_repos(
    client: GitHubApiClient,
    per_page: int = 100,
    max_pages: int = 10,
    use_cache: bool = True,
    cache_key_user: str = "default",
) -> List[RepoInfo]:
    """
    List repositories the viewer can access via GitHub REST API.

    - Uses GET /user/repos with affiliation + visibility filters.
    - Paginates using the Link header.
    - Checks cache first (120s TTL) if use_cache=True.
    - Raises GitHubApiError for HTTP failures with friendly messages.

    Args:
        client: GitHubApiClient instance
        per_page: Items per page (default 100, max 100)
        max_pages: Maximum pages to fetch
        use_cache: Whether to use/populate cache (default True)
        cache_key_user: Username/ID for cache key isolation

    Returns:
        List[RepoInfo]: List of repositories

    Raises:
        GitHubApiError: With code (UNAUTHORIZED, RATE_LIMITED, NETWORK, etc.)
    """
    # Check cache first
    if use_cache:
        cache = get_github_api_cache()
        cached_repos, cache_hit = cache.get(
            "api.github.com", cache_key_user, "repos_list"
        )
        if cache_hit and cached_repos is not None:
            log.debug(f"Using cached repo list ({len(cached_repos)} repos)")
            return cached_repos

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
        except GitHubApiError:
            raise
        except Exception as e:
            # Unexpected error; wrap it
            raise GitHubApiError.from_network_error(str(e)) from e

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
                    owner = (
                        full_name.split("/", 1)[0] if "/" in full_name else full_name
                    )

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

    # Store in cache before returning
    if use_cache:
        cache = get_github_api_cache()
        cache.set(
            "api.github.com",
            cache_key_user,
            "repos_list",
            results,
        )
        log.debug(f"Cached repo list ({len(results)} repos)")

    return results
