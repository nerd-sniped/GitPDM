# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
GitLab project listing via GET /projects.

Pagination differs from GitHub: GitLab returns an `X-Next-Page` response
header holding the next page number (empty when there is no next page),
not a Link header with a full next URL — so the loop here advances by
incrementing a `page` query param rather than following an opaque URL.
"""

from __future__ import annotations

from typing import List, Optional

from freecad_gitpdm.core import log
from freecad_gitpdm.providers.base import RepoInfo
from freecad_gitpdm.providers.gitlab.api_client import GitLabApiClient
from freecad_gitpdm.providers.gitlab.errors import GitLabApiError
from freecad_gitpdm.providers.shared.cache import get_api_cache
from freecad_gitpdm.providers.shared.errors import ProviderApiNetworkError


def _extract_next_page(headers: dict) -> Optional[str]:
    if not headers:
        return None
    for k, v in headers.items():
        if k.lower() == "x-next-page":
            return v.strip() if v and v.strip() else None
    return None


def list_repos(
    client: GitLabApiClient,
    per_page: int = 100,
    max_pages: int = 10,
    use_cache: bool = True,
    cache_key_user: str = "default",
) -> List[RepoInfo]:
    if use_cache:
        cache = get_api_cache()
        cached_repos, cache_hit = cache.get(
            client._base_url, cache_key_user, "repos_list"
        )
        if cache_hit and cached_repos is not None:
            log.debug(f"Using cached GitLab project list ({len(cached_repos)} repos)")
            return cached_repos

    results: List[RepoInfo] = []

    if per_page <= 0 or per_page > 100:
        per_page = 100
    if max_pages <= 0:
        max_pages = 1

    page_num = "1"
    pages_fetched = 0

    while page_num and pages_fetched < max_pages:
        pages_fetched += 1
        url = (
            f"/projects?membership=true&per_page={per_page}"
            f"&order_by=updated_at&sort=desc&page={page_num}"
        )
        try:
            status, js, headers = client.request_json(
                "GET", url, headers=None, body=None, timeout_s=15
            )
        except ProviderApiNetworkError:
            raise
        except GitLabApiError:
            raise
        except Exception as e:
            raise GitLabApiError.from_network_error(str(e)) from e

        if status < 200 or status >= 300:
            raise GitLabApiError.from_http_error(status, headers or {})

        if not isinstance(js, list):
            log.warning("Unexpected GitLab response payload; expected list")
            js_items = []
        else:
            js_items = js

        for item in js_items:
            try:
                full_name = item.get("path_with_namespace") or item.get("name") or ""
                owner = full_name.rsplit("/", 1)[0] if "/" in full_name else full_name
                name = item.get("path") or item.get("name") or full_name.split("/")[-1]

                repo = RepoInfo(
                    owner=owner,
                    name=name,
                    full_name=full_name,
                    private=(item.get("visibility") != "public"),
                    default_branch=item.get("default_branch"),
                    clone_url=item.get("http_url_to_repo") or "",
                    updated_at=item.get("last_activity_at"),
                )
                results.append(repo)
            except (AttributeError, TypeError) as parse_err:
                log.debug(
                    f"Skipping GitLab project entry due to parse error: {parse_err}"
                )
                continue

        page_num = _extract_next_page(headers or {})

    if use_cache:
        cache = get_api_cache()
        cache.set(client._base_url, cache_key_user, "repos_list", results)
        log.debug(f"Cached GitLab project list ({len(results)} repos)")

    return results
