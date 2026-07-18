# -*- coding: utf-8 -*-
"""
SourceHut repository listing via the git.sr.ht GraphQL `me { repositories }`
query, cursor-paginated (GraphQL's own convention, distinct from every
other provider's HTTP-header or body-URL pagination).

**Unverified against the live schema** - see providers/sourcehut/__init__.py.
"""

from __future__ import annotations

from typing import List, Optional

from freecad_gitpdm.core import log
from freecad_gitpdm.providers.base import RepoInfo
from freecad_gitpdm.providers.sourcehut.api_client import SourceHutApiClient
from freecad_gitpdm.providers.sourcehut.errors import SourceHutApiError
from freecad_gitpdm.providers.shared.cache import get_api_cache
from freecad_gitpdm.providers.shared.errors import ProviderApiNetworkError

_REPOSITORIES_QUERY = """
query Repositories($cursor: Cursor) {
  me {
    repositories(cursor: $cursor) {
      cursor
      results {
        id
        name
        description
        visibility
        updated
        owner {
          canonicalName
        }
      }
    }
  }
}
"""


def list_repos(
    client: SourceHutApiClient,
    max_pages: int = 10,
    use_cache: bool = True,
    cache_key_user: str = "default",
) -> List[RepoInfo]:
    if use_cache:
        cache = get_api_cache()
        cached_repos, cache_hit = cache.get("git.sr.ht", cache_key_user, "repos_list")
        if cache_hit and cached_repos is not None:
            log.debug(f"Using cached SourceHut repo list ({len(cached_repos)} repos)")
            return cached_repos

    results: List[RepoInfo] = []

    if max_pages <= 0:
        max_pages = 1

    cursor: Optional[str] = None
    page = 0

    while page < max_pages:
        page += 1
        try:
            data = client.graphql(_REPOSITORIES_QUERY, {"cursor": cursor}, timeout_s=15)
        except ProviderApiNetworkError:
            raise
        except SourceHutApiError:
            raise
        except Exception as e:
            raise SourceHutApiError.from_network_error(str(e)) from e

        me = data.get("me") if isinstance(data, dict) else None
        repos_page = (me or {}).get("repositories") or {}
        js_items = repos_page.get("results")
        if not isinstance(js_items, list):
            log.warning("Unexpected SourceHut response payload; expected a list")
            js_items = []

        for item in js_items:
            try:
                name = item.get("name") or ""
                owner = item.get("owner") or {}
                canonical_name = owner.get("canonicalName") or ""
                full_name = f"{canonical_name}/{name}".strip("/")
                url = (
                    f"https://git.sr.ht/{canonical_name}/{name}"
                    if canonical_name and name
                    else ""
                )

                repo = RepoInfo(
                    owner=canonical_name,
                    name=name,
                    full_name=full_name,
                    private=(item.get("visibility") == "PRIVATE"),
                    default_branch=None,  # not exposed by this query's response shape
                    clone_url=url,
                    updated_at=item.get("updated"),
                )
                results.append(repo)
            except (AttributeError, TypeError) as parse_err:
                log.debug(
                    f"Skipping SourceHut repo entry due to parse error: {parse_err}"
                )
                continue

        cursor = repos_page.get("cursor")
        if not cursor:
            break

    if use_cache:
        cache = get_api_cache()
        cache.set("git.sr.ht", cache_key_user, "repos_list", results)
        log.debug(f"Cached SourceHut repo list ({len(results)} repos)")

    return results
