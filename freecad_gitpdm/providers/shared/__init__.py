# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
Shared, host-agnostic building blocks for provider API clients: the generic
retry/circuit-breaker HTTP client, the shared error shape, response caching,
and rate limiting. Extracted from `providers/github/*` (Phase G4's first and
only provider) so GitLab/Bitbucket/Gitea/SourceHut don't each reimplement
the same transport plumbing. See Dev_Docs/GITPDM_DEV_PLAN.md's multi-provider entry.
"""
