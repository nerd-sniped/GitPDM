# -*- coding: utf-8 -*-
"""
Bitbucket Cloud repository listing via GET /2.0/repositories/{workspace}.

Also workspace-scoped, like creation. Pagination is body-embedded: the
response has a `next` field holding the full next-page URL directly
(verified live against a real public workspace), unlike GitHub/Gitea's
Link header or GitLab's X-Next-Page header. Clone URL is nested in
`links.clone[]` (a list of `{name, href}`, pick the "https" entry) rather
than a flat field.
"""

from __future__ import annotations

from typing import List, Optional

from freecad_gitpdm.core import log
from freecad_gitpdm.providers.base import RepoInfo
from freecad_gitpdm.providers.bitbucket.api_client import BitbucketApiClient
from freecad_gitpdm.providers.bitbucket.errors import BitbucketApiError
from freecad_gitpdm.providers.bitbucket.create_repo import _extract_https_clone_url
from freecad_gitpdm.providers.shared.cache import get_api_cache
from freecad_gitpdm.providers.shared.errors import ProviderApiNetworkError


def list_repos(
    client: BitbucketApiClient,
    workspace: str,
    per_page: int = 100,
    max_pages: int = 10,
    use_cache: bool = True,
    cache_key_user: str = "default",
) -> List[RepoInfo]:
    if not workspace or not workspace.strip():
        raise BitbucketApiError(
            code="BAD_RESPONSE", message="A Bitbucket workspace is required"
        )
    workspace = workspace.strip()

    if use_cache:
        cache = get_api_cache()
        cached_repos, cache_hit = cache.get(
            "bitbucket.org", cache_key_user, "repos_list", query_params=workspace
        )
        if cache_hit and cached_repos is not None:
            log.debug(f"Using cached Bitbucket repo list ({len(cached_repos)} repos)")
            return cached_repos

    results: List[RepoInfo] = []

    if per_page <= 0 or per_page > 100:
        per_page = 100
    if max_pages <= 0:
        max_pages = 1

    url = f"/repositories/{workspace}?pagelen={per_page}"

    page = 0
    while url and page < max_pages:
        page += 1
        try:
            status, js, headers = client.request_json(
                "GET", url, headers=None, body=None, timeout_s=15
            )
        except ProviderApiNetworkError:
            raise
        except BitbucketApiError:
            raise
        except Exception as e:
            raise BitbucketApiError.from_network_error(str(e)) from e

        if status < 200 or status >= 300:
            raise BitbucketApiError.from_http_error(status, headers or {})

        if not isinstance(js, dict):
            log.warning("Unexpected Bitbucket response payload; expected object")
            js = {}

        for item in js.get("values") or []:
            try:
                full_name = item.get("full_name") or ""
                owner = full_name.split("/", 1)[0] if "/" in full_name else workspace
                name = item.get("slug") or item.get("name") or full_name.split("/")[-1]
                links = item.get("links") or {}
                mainbranch = item.get("mainbranch") or {}

                repo = RepoInfo(
                    owner=owner,
                    name=name,
                    full_name=full_name,
                    private=bool(item.get("is_private", False)),
                    default_branch=mainbranch.get("name"),
                    clone_url=_extract_https_clone_url(links.get("clone")),
                    updated_at=item.get("updated_on"),
                )
                results.append(repo)
            except (AttributeError, TypeError) as parse_err:
                log.debug(
                    f"Skipping Bitbucket repo entry due to parse error: {parse_err}"
                )
                continue

        next_url = js.get("next")
        # `next` is a full absolute URL; BaseApiClient._resolve_url passes
        # absolute URLs through unchanged, so this is safe to hand back in
        # directly on the next loop iteration.
        url = next_url if isinstance(next_url, str) and next_url else None

    if use_cache:
        cache = get_api_cache()
        cache.set(
            "bitbucket.org",
            cache_key_user,
            "repos_list",
            results,
            query_params=workspace,
        )
        log.debug(f"Cached Bitbucket repo list ({len(results)} repos)")

    return results
