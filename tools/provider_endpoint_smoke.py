# -*- coding: utf-8 -*-
"""
Live, unauthenticated smoke check for the multi-provider hosts (GitLab,
Bitbucket, Gitea/Forgejo, SourceHut). Confirms each host's API is still
reachable and returns the expected 401-shaped error for an unauthenticated
identity check — no token needed, cheap to run, and catches "the host
changed their API" drift early rather than during someone's real connect
attempt.

This does NOT prove the providers are fully correct (a real-token pass
that actually creates/lists a repo is still needed — see
Dev_Docs/GITPDM_DEV_PLAN.md's multi-provider entry, especially for SourceHut, whose
GraphQL schema could not be live-verified during development). It only
proves each endpoint is up and each client's request/error-handling
plumbing still produces a sane, non-crashing result.

Usage: python tools/provider_endpoint_smoke.py
Exit code 0 if every host responds as expected, 1 otherwise.
"""

from __future__ import annotations

import sys

from freecad_gitpdm.providers.gitlab.provider import GitLabProvider
from freecad_gitpdm.providers.gitea.provider import GiteaProvider
from freecad_gitpdm.providers.bitbucket.provider import BitbucketProvider
from freecad_gitpdm.providers.sourcehut.provider import SourceHutProvider

# Codeberg is a public Forgejo instance, used as a stand-in host for Gitea/
# Forgejo's API shape since that provider is inherently self-hosted with no
# single fixed host of its own to check.
_CHECKS = [
    (GitLabProvider(), {}),
    (GiteaProvider(), {"host": "https://codeberg.org"}),
    (BitbucketProvider(), {}),
    (SourceHutProvider(), {}),
]


def main() -> int:
    all_ok = True
    for provider, client_kwargs in _CHECKS:
        client = provider.build_api_client(token="", **client_kwargs)
        if client is None:
            print(f"{provider.provider_id:12s} FAIL  could not build a client")
            all_ok = False
            continue

        identity = provider.fetch_identity(client)
        # Unauthenticated: expect a clean UNAUTHORIZED, not ok=True and not
        # a crash/unexpected error code.
        if identity.ok:
            print(
                f"{provider.provider_id:12s} FAIL  unauthenticated request "
                "unexpectedly succeeded"
            )
            all_ok = False
        elif identity.error_code != "UNAUTHORIZED":
            print(
                f"{provider.provider_id:12s} FAIL  expected UNAUTHORIZED, "
                f"got {identity.error_code}: {identity.message}"
            )
            all_ok = False
        else:
            print(
                f"{provider.provider_id:12s} OK    endpoint reachable, error shape as expected"
            )

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
