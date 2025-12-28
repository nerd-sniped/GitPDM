# -*- coding: utf-8 -*-
"""
Tests for identity fetcher (pure python).
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from freecad_gitpdm.github.identity import fetch_viewer_identity


class _StubClient:
    def __init__(self, status, js, headers=None):
        self._status = status
        self._js = js
        self._headers = headers or {}

    def request_json(self, method, url, headers, body, timeout_s):
        return self._status, self._js, self._headers


def test_identity_success_parsing():
    client = _StubClient(200, {"login": "octocat", "id": 1, "avatar_url": "http://example"})
    res = fetch_viewer_identity(client)
    assert res.ok is True
    assert res.login == "octocat"
    assert res.user_id == 1
    assert res.avatar_url == "http://example"


def test_identity_unauthorized_classification():
    client = _StubClient(401, None)
    res = fetch_viewer_identity(client)
    assert res.ok is False
    assert res.error_code == "UNAUTHORIZED"


def test_identity_rate_limited_classification():
    client = _StubClient(403, None, {"X-RateLimit-Remaining": "0"})
    res = fetch_viewer_identity(client)
    assert res.ok is False
    assert res.error_code == "RATE_LIMITED"


def test_identity_forbidden_classification():
    client = _StubClient(403, None, {"X-RateLimit-Remaining": "10"})
    res = fetch_viewer_identity(client)
    assert res.ok is False
    assert res.error_code == "FORBIDDEN"
