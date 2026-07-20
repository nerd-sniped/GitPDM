# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
Tests for freecad_gitpdm.core.input_validator's validate_self_hosted_url
(2026-07-20, closing a gap found while auditing the PAT-paste connect flow
for the FreeCAD Addon Index submission: unlike GitHub's hardcoded HTTPS
path, the Gitea/Forgejo self-hosted host-URL field accepted plain HTTP
with no local warning).
"""

import pytest

from freecad_gitpdm.core.input_validator import validate_self_hosted_url


class TestValidateSelfHostedUrl:
    def test_https_url_is_valid(self):
        is_valid, error = validate_self_hosted_url("https://gitea.example.com")
        assert is_valid
        assert error == ""

    def test_plain_http_is_rejected(self):
        is_valid, error = validate_self_hosted_url("http://gitea.example.com")
        assert not is_valid
        assert "HTTPS" in error

    def test_missing_scheme_is_rejected(self):
        is_valid, error = validate_self_hosted_url("gitea.example.com")
        assert not is_valid
        assert "https://" in error

    def test_empty_url_is_rejected(self):
        is_valid, error = validate_self_hosted_url("")
        assert not is_valid
        assert error == "URL cannot be empty"

    def test_other_scheme_is_rejected(self):
        is_valid, error = validate_self_hosted_url("ftp://gitea.example.com")
        assert not is_valid

    def test_null_byte_is_rejected(self):
        is_valid, error = validate_self_hosted_url("https://gitea.example.com\0evil")
        assert not is_valid
        assert "invalid characters" in error

    def test_overly_long_url_is_rejected(self):
        is_valid, error = validate_self_hosted_url("https://" + "a" * 2000)
        assert not is_valid
        assert "too long" in error
