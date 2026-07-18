# -*- coding: utf-8 -*-
"""
GitPDM provider registry (Phase G4).

`get_provider_class()` is the only supported way to go from a provider id
(stored per-repo in `.freecad-pdm/config.json`, or `GITPDM_PROVIDER` in the
G1 credential chain) to a concrete provider class. Never import
`GitHubProvider`/`GenericProvider`/`GitLabProvider` directly outside this
package and `providers/github/` — that's the choke point that keeps
provider conditionals out of `core/`, `export/`, and `ui/`.
"""

from __future__ import annotations

from typing import Dict, List, Type

from freecad_gitpdm.providers.base import BaseProvider, GenericProvider

DEFAULT_PROVIDER_ID = "github"

_REGISTRY: Dict[str, Type[BaseProvider]] = {}


def _populate_registry() -> Dict[str, Type[BaseProvider]]:
    from freecad_gitpdm.providers.github.provider import GitHubProvider
    from freecad_gitpdm.providers.gitlab import GitLabProvider
    from freecad_gitpdm.providers.gitea import GiteaProvider
    from freecad_gitpdm.providers.bitbucket import BitbucketProvider

    return {
        "generic": GenericProvider,
        "github": GitHubProvider,
        "gitlab": GitLabProvider,
        "gitea": GiteaProvider,
        "bitbucket": BitbucketProvider,
    }


def get_provider_class(provider_id: str) -> Type[BaseProvider]:
    """Look up a provider class by id. Unknown ids fall back to GenericProvider."""
    global _REGISTRY
    if not _REGISTRY:
        _REGISTRY = _populate_registry()
    return _REGISTRY.get((provider_id or "").strip().lower(), GenericProvider)


def get_provider(provider_id: str) -> BaseProvider:
    """Look up and instantiate a provider by id."""
    return get_provider_class(provider_id)()


def list_provider_ids() -> List[str]:
    global _REGISTRY
    if not _REGISTRY:
        _REGISTRY = _populate_registry()
    return sorted(_REGISTRY.keys())
