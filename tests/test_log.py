# -*- coding: utf-8 -*-
"""
Tests for core.log module - Logging with token redaction
"""

import pytest
from unittest.mock import patch, MagicMock
from freecad_gitpdm.core import log


class TestTokenRedaction:
    """Test sensitive data redaction in logs"""
    
    def test_redact_github_access_token(self):
        """Test redaction of GitHub OAuth access tokens"""
        message = "Using token ghp_1234567890abcdefghijklmnop for auth"
        redacted = log._redact_sensitive(message)
        assert "ghp_" not in redacted
        assert "[REDACTED_ACCESS_TOKEN]" in redacted
    
    def test_redact_github_pat(self):
        """Test redaction of GitHub Personal Access Tokens"""
        message = "Token: github_pat_11ABCDEF1234567890"
        redacted = log._redact_sensitive(message)
        assert "github_pat_" not in redacted
        assert "[REDACTED_PAT]" in redacted
    
    def test_redact_refresh_token_json(self):
        """Test redaction of refresh tokens in JSON"""
        message = '{"access_token": "abc", "refresh_token": "sensitive_refresh_token_here"}'
        redacted = log._redact_sensitive(message)
        assert "sensitive_refresh_token_here" not in redacted
        assert "[REDACTED_REFRESH_TOKEN]" in redacted
    
    def test_redact_access_token_json(self):
        """Test redaction of access tokens in JSON"""
        message = '{"access_token": "ghp_secret123"}'
        redacted = log._redact_sensitive(message)
        assert "ghp_secret123" not in redacted
        assert "[REDACTED_ACCESS_TOKEN]" in redacted
    
    def test_redact_multiple_tokens(self):
        """Test redaction of multiple tokens in same message"""
        message = "Token 1: ghp_token1 and Token 2: ghp_token2"
        redacted = log._redact_sensitive(message)
        assert "ghp_token1" not in redacted
        assert "ghp_token2" not in redacted
        assert redacted.count("[REDACTED_ACCESS_TOKEN]") == 2
    
    def test_no_redaction_for_safe_content(self):
        """Test that safe content is not modified"""
        message = "Normal log message without sensitive data"
        redacted = log._redact_sensitive(message)
        assert redacted == message
    
    def test_redact_none_message(self):
        """Test handling None message"""
        redacted = log._redact_sensitive(None)
        assert redacted is None
    
    def test_redact_empty_string(self):
        """Test handling empty string"""
        redacted = log._redact_sensitive("")
        assert redacted == ""


class TestLoggingFunctions:
    """Test logging functions"""
    
    @patch('freecad_gitpdm.core.log._redact_sensitive')
    def test_info_calls_redaction(self, mock_redact, mock_freecad):
        """Test that info() calls redaction"""
        mock_redact.return_value = "safe message"
        log.info("test message")
        mock_redact.assert_called_once()
    
    @patch('freecad_gitpdm.core.log._redact_sensitive')
    def test_error_calls_redaction(self, mock_redact, mock_freecad):
        """Test that error() calls redaction"""
        mock_redact.return_value = "safe error"
        log.error("error message")
        mock_redact.assert_called_once()
    
    @patch('freecad_gitpdm.core.log._redact_sensitive')
    def test_warning_calls_redaction(self, mock_redact, mock_freecad):
        """Test that warning() calls redaction"""
        mock_redact.return_value = "safe warning"
        log.warning("warning message")
        mock_redact.assert_called_once()
    
    @patch('freecad_gitpdm.core.log._redact_sensitive')
    def test_debug_calls_redaction(self, mock_redact, mock_freecad):
        """Test that debug() calls redaction"""
        mock_redact.return_value = "safe debug"
        log.debug("debug message")
        mock_redact.assert_called_once()
    
    def test_error_safe_with_exception(self, mock_freecad):
        """Test error_safe with exception object"""
        exc = Exception("Token: ghp_secret123")
        log.error_safe("Error occurred", exc)
        # Should not raise exception
    
    def test_warning_safe_with_exception(self, mock_freecad):
        """Test warning_safe with exception object"""
        exc = ValueError("Invalid token ghp_test")
        log.warning_safe("Warning", exc)
        # Should not raise exception
    
    def test_debug_safe_with_exception(self, mock_freecad):
        """Test debug_safe with exception object"""
        exc = RuntimeError("Debug info ghp_debug")
        log.debug_safe("Debug", exc)
        # Should not raise exception
    
    def test_logging_without_freecad(self):
        """Test logging falls back gracefully without FreeCAD"""
        # Temporarily remove FreeCAD from sys.modules
        import sys
        freecad_backup = sys.modules.get('FreeCAD')
        if 'FreeCAD' in sys.modules:
            del sys.modules['FreeCAD']
        
        try:
            # Should fall back to print() without raising exception
            log.info("Test message")
            log.error("Test error")
            log.warning("Test warning")
            log.debug("Test debug")
        finally:
            # Restore FreeCAD mock
            if freecad_backup:
                sys.modules['FreeCAD'] = freecad_backup
