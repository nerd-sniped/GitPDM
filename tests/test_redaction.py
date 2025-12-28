# -*- coding: utf-8 -*-
"""
Tests for log redaction (no secrets).
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from freecad_gitpdm.core.log import _redact_sensitive


def test_redact_access_token_json():
    s = '{"access_token": "ghp_ABCDEF123456"}'
    r = _redact_sensitive(s)
    assert "ghp_ABCDEF" not in r
    assert "[REDACTED_ACCESS_TOKEN]" in r


def test_redact_authorization_header():
    s = "Authorization: Bearer verysecrettoken123=="
    r = _redact_sensitive(s)
    assert "verysecrettoken" not in r
    assert "Authorization: Bearer [REDACTED]" in r
