# -*- coding: utf-8 -*-
"""
SourceHut repository creation via the git.sr.ht GraphQL `createRepository`
mutation.

**Unverified against the live schema** (see providers/sourcehut/__init__.py)
- built from SourceHut's public GraphQL API documentation. Field/mutation
names (`createRepository`, `Visibility` enum values PUBLIC/UNLISTED/PRIVATE,
`owner.canonicalName`) should be confirmed against a real account before
this is trusted; parsing is deliberately defensive (.get()-based, mirrors
every other provider's pattern) so a schema mismatch degrades to a clear
BAD_RESPONSE error rather than a crash.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from freecad_gitpdm.core import log
from freecad_gitpdm.providers.sourcehut.api_client import SourceHutApiClient
from freecad_gitpdm.providers.sourcehut.errors import SourceHutApiError
from freecad_gitpdm.providers.shared.errors import ProviderApiNetworkError

# SourceHut repo names: lowercase-friendly but case-sensitive in practice;
# documented as alphanumeric plus . _ -, no spaces.
_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")

_CREATE_REPOSITORY_MUTATION = """
mutation CreateRepository($name: String!, $visibility: Visibility!, $description: String) {
  createRepository(name: $name, visibility: $visibility, description: $description) {
    id
    name
    description
    visibility
    owner {
      canonicalName
    }
  }
}
"""


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
    client: SourceHutApiClient,
    req: CreateRepoRequest,
) -> CreatedRepoInfo:
    if not req.name or not req.name.strip():
        raise SourceHutApiError(
            code="BAD_RESPONSE", message="Repository name is required"
        )
    if not _NAME_RE.match(req.name):
        raise SourceHutApiError(
            code="BAD_RESPONSE",
            message=f"Invalid repository name '{req.name}'. "
            "Use letters, numbers, dash, dot, or underscore.",
        )

    variables = {
        "name": req.name,
        "visibility": "PRIVATE" if req.private else "PUBLIC",
        "description": req.description.strip()
        if req.description and req.description.strip()
        else None,
    }

    try:
        data = client.graphql(_CREATE_REPOSITORY_MUTATION, variables, timeout_s=30)
    except ProviderApiNetworkError as e:
        log.error(f"Network error creating SourceHut repository: {e}")
        raise

    repo = data.get("createRepository") if isinstance(data, dict) else None
    if not isinstance(repo, dict):
        raise SourceHutApiError(
            code="BAD_RESPONSE", message="Invalid response from SourceHut API"
        )

    try:
        name = repo.get("name") or ""
        owner = repo.get("owner") or {}
        canonical_name = owner.get("canonicalName") or ""

        if not name or not canonical_name:
            raise SourceHutApiError(
                code="BAD_RESPONSE", message="Incomplete response from SourceHut API"
            )

        full_name = f"{canonical_name}/{name}"
        # sr.ht's clone URL convention has no `.git` suffix and embeds the
        # owner's canonical (~-prefixed) name directly.
        url = f"https://git.sr.ht/{canonical_name}/{name}"

        log.info(f"SourceHut repository created: {full_name}")
        return CreatedRepoInfo(
            full_name=full_name,
            html_url=url,
            clone_url=url,
            default_branch=None,  # not exposed by this mutation's response shape
        )
    except (KeyError, AttributeError, TypeError) as e:
        log.error(f"Failed to parse SourceHut repo creation response: {e}")
        raise SourceHutApiError(
            code="BAD_RESPONSE", message="Invalid response format from SourceHut API"
        )
