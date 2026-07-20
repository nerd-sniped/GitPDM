# -*- coding: utf-8 -*-
"""
SourceHut provider (git.sr.ht GraphQL API, PAT/Bearer-token auth).

**Unverified schema warning:** unlike GitLab/Bitbucket/Gitea (all
live-verified against real endpoints during development), SourceHut's
GraphQL endpoint requires `Authorization: Bearer <token>` even for schema
introspection — confirmed live, no way around it without a real account.
The mutation/query field names in this subpackage are built from
SourceHut's public GraphQL API documentation, not confirmed against the
live schema. Treat this provider as needing a real-token acceptance pass
(create a repo, list repos, verify identity against a real git.sr.ht
account) before trusting it in production — see Dev_Docs/GITPDM_DEV_PLAN.md's
multi-provider entry, which tracks this explicitly, mirroring how G1's
docker acceptance run was tracked as outstanding and closed out later.
"""

from __future__ import annotations

from freecad_gitpdm.providers.sourcehut.provider import SourceHutProvider

__all__ = ["SourceHutProvider"]
