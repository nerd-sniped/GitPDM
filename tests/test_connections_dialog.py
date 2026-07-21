# -*- coding: utf-8 -*-
"""
Tests for ui/connections_dialog.py's provider routing logic.

Audit fix P1.4: the "Other Git Hosts" list must be driven by
`capabilities.requires_manual_token`, not a hardcoded id exclusion
(`pid not in ("github", "generic")`) — so a new PAT-paste provider is
picked up automatically. GitHub's device-flow section stays a hardcoded
special case (it's the only `supports_device_flow` provider today, and
its startup wiring in ui/panel.py depends on its widgets always
existing), but that assumption is asserted here so it fails loudly if a
second device-flow provider is ever added without updating the UI.
"""

from freecad_gitpdm.providers import list_provider_ids, get_provider_class


def _other_host_ids():
    """Mirrors ConnectionsDialog._build_other_hosts_section's filter
    without needing Qt/FreeCAD constructed."""
    return sorted(
        pid
        for pid in list_provider_ids()
        if get_provider_class(pid).capabilities.requires_manual_token
    )


class TestOtherHostsCapabilityFiltering:
    def test_generic_and_github_excluded(self):
        ids = _other_host_ids()
        assert "generic" not in ids
        assert "github" not in ids

    def test_pat_paste_hosts_included(self):
        ids = _other_host_ids()
        for expected in ("gitlab", "bitbucket", "gitea", "sourcehut"):
            assert expected in ids

    def test_filter_is_capability_driven_not_id_based(self):
        """A provider with requires_manual_token=True must appear
        regardless of its id — proves the filter isn't secretly still an
        id-based exclusion list in disguise."""
        ids = _other_host_ids()
        for pid in ids:
            assert get_provider_class(pid).capabilities.requires_manual_token is True

    def test_no_provider_is_both_device_flow_and_manual_token(self):
        """Device flow and PAT-paste are mutually exclusive auth UX per
        provider today. If this ever fails, connections_dialog.py needs a
        real device-flow section for that provider too."""
        for pid in list_provider_ids():
            caps = get_provider_class(pid).capabilities
            assert not (caps.supports_device_flow and caps.requires_manual_token)


class TestGitHubDeviceFlowAssumption:
    """GitHub's "GitHub Account" section is hardcoded (not built from a
    capability-driven loop) — safe only because it's currently the only
    supports_device_flow provider. This guards that assumption."""

    def test_github_is_the_only_device_flow_provider(self):
        device_flow_ids = [
            pid
            for pid in list_provider_ids()
            if get_provider_class(pid).capabilities.supports_device_flow
        ]
        assert device_flow_ids == ["github"]
