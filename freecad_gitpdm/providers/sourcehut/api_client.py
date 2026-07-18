# -*- coding: utf-8 -*-
"""
SourceHut GraphQL API client (stdlib-only, built on BaseApiClient).

Structurally different from every other provider here: GraphQL means one
endpoint (`https://git.sr.ht/query`, confirmed live) always POST'd to with
a `{"query": ..., "variables": {...}}` body, not path-based REST calls.
`_resolve_url` is overridden to always target that one endpoint regardless
of what's passed in, and `graphql()` wraps `request_json` to also surface
query/mutation-execution-time errors (a `errors` array in an otherwise-200
response — standard GraphQL behavior, not verified live for this API
specifically, but handled defensively either way).

Auth: `Authorization: Bearer <token>` — confirmed live (SourceHut requires
this even for schema introspection, which is precisely why the query/
mutation field names elsewhere in this subpackage could NOT be verified
against the live schema — see providers/sourcehut/__init__.py).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from freecad_gitpdm.providers.sourcehut.errors import SourceHutApiError
from freecad_gitpdm.providers.shared.http_client import BaseApiClient

SOURCEHUT_GRAPHQL_ENDPOINT = "https://git.sr.ht/query"


class SourceHutApiClient(BaseApiClient):
    provider_id = "sourcehut"
    error_cls = SourceHutApiError

    def __init__(self, token: str, user_agent: str = "GitPDM/1.0"):
        super().__init__(SOURCEHUT_GRAPHQL_ENDPOINT, token, user_agent)

    def _auth_headers(self):
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    def _resolve_url(self, url: str) -> str:
        # Single GraphQL endpoint - there's no per-resource path to build.
        return self._base_url

    def graphql(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        timeout_s: int = 20,
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query/mutation. Returns the `data` object on
        success. Raises SourceHutApiError for both transport-level HTTP
        errors and query-execution-time errors (a GraphQL `errors` array
        in the response body, regardless of HTTP status).
        """
        status, js, _headers = self.request_json(
            "POST",
            "",
            headers=None,
            body={"query": query, "variables": variables or {}},
            timeout_s=timeout_s,
        )

        if not isinstance(js, dict):
            raise SourceHutApiError(
                code="BAD_RESPONSE", message="Invalid response from SourceHut API"
            )

        errors = js.get("errors")
        if errors:
            raise SourceHutApiError.from_graphql_errors(errors)

        return js.get("data") or {}
