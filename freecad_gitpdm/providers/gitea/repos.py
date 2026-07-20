# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
Gitea/Forgejo repository listing via GET /user/repos.

Pagination uses the RFC5988 `Link` header (same convention as GitHub) -
Gitea's GitHub-API-compatibility extends to this.
"""

from __future__ import annotations

from typing import List, Optional

from freecad_gitpdm.core import log
from freecad_gitpdm.providers.base import RepoInfo
from freecad_gitpdm.providers.gitea.api_client import GiteaApiClient
from freecad_gitpdm.providers.gitea.errors import GiteaApiError
from freecad_gitpdm.providers.shared.cache import get_api_cache
from freecad_gitpdm.providers.shared.errors import ProviderApiNetworkError


def _extract_next_link(headers: dict) -> Optional[str]:
    if not headers:
        return None
    link_header = None
    for k, v in headers.items():
        if k.lower() == "link":
            link_header = v
            break
    if not link_header:
        return None

    for part in link_header.split(","):
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


def list_repos(
    client: GiteaApiClient,
    per_page: int = 50,
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
            log.debug(f"Using cached Gitea repo list ({len(cached_repos)} repos)")
            return cached_repos

    results: List[RepoInfo] = []

    # Gitea's /user/repos caps limit at 50 per page.
    if per_page <= 0 or per_page > 50:
        per_page = 50
    if max_pages <= 0:
        max_pages = 1

    url = f"/user/repos?limit={per_page}"

    page = 0
    while url and page < max_pages:
        page += 1
        try:
            status, js, headers = client.request_json(
                "GET", url, headers=None, body=None, timeout_s=15
            )
        except ProviderApiNetworkError:
            raise
        except GiteaApiError:
            raise
        except Exception as e:
            raise GiteaApiError.from_network_error(str(e)) from e

        if status < 200 or status >= 300:
            raise GiteaApiError.from_http_error(status, headers or {})

        if not isinstance(js, list):
            log.warning("Unexpected Gitea response payload; expected list")
            js_items = []
        else:
            js_items = js

        for item in js_items:
            try:
                full_name = item.get("full_name") or ""
                if not full_name:
                    owner_obj = item.get("owner") or {}
                    owner = owner_obj.get("login") or owner_obj.get("username") or ""
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
            except (AttributeError, TypeError) as parse_err:
                log.debug(f"Skipping Gitea repo entry due to parse error: {parse_err}")
                continue

        url = _extract_next_link(headers or {})

    if use_cache:
        cache = get_api_cache()
        cache.set(client._base_url, cache_key_user, "repos_list", results)
        log.debug(f"Cached Gitea repo list ({len(results)} repos)")

    return results
