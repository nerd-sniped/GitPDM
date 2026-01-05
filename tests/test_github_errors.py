"""
Tests for github.errors module - GitHub API error classification
"""

import pytest
from freecad.gitpdm.github.errors import GitHubApiError, GitHubApiNetworkError


class TestGitHubApiError:
    """Test GitHubApiError classification"""

    def test_from_http_401_unauthorized(self):
        """Test 401 Unauthorized error classification"""
        error = GitHubApiError.from_http_error(401)
        assert error.code == "UNAUTHORIZED"
        assert error.status == 401
        assert "session" in error.message.lower() or "expired" in error.message.lower()
        assert error.retry_after_s is None

    def test_from_http_403_forbidden(self):
        """Test 403 Forbidden error classification"""
        error = GitHubApiError.from_http_error(403)
        assert error.code == "FORBIDDEN"
        assert error.status == 403
        assert error.retry_after_s is None

    def test_from_http_404_not_found(self):
        """Test 404 Not Found error classification"""
        error = GitHubApiError.from_http_error(404)
        assert error.code == "UNKNOWN"  # 404 returns UNKNOWN in implementation
        assert error.status == 404

    def test_from_http_429_rate_limit(self):
        """Test 429/403 Rate Limit error classification"""
        # Rate limiting returns 403 with x-ratelimit-remaining=0
        headers = {
            "x-ratelimit-remaining": "0",  # Must be 0 for RATE_LIMITED
            "x-ratelimit-reset": "1735660800",
            "retry-after": "60",
        }
        error = GitHubApiError.from_http_error(403, headers=headers)  # 403 not 429
        assert error.code == "RATE_LIMITED"
        assert error.status == 403
        assert error.retry_after_s == 60
        assert error.rate_limit_reset_utc is not None

    def test_from_http_422_validation(self):
        """Test 422 Unprocessable Entity error"""
        error = GitHubApiError.from_http_error(422)
        assert error.code == "BAD_RESPONSE"  # Implementation uses BAD_RESPONSE
        assert error.status == 422

    def test_from_http_500_server_error(self):
        """Test 500 Server Error classification"""
        error = GitHubApiError.from_http_error(500)
        assert error.code == "NETWORK"
        assert error.status == 500
        assert error.retry_after_s is not None  # Should have retry

    def test_from_http_503_service_unavailable(self):
        """Test 503 Service Unavailable"""
        error = GitHubApiError.from_http_error(503)
        assert error.code == "NETWORK"
        assert error.status == 503
        assert error.retry_after_s is not None

    def test_from_network_error_timeout(self):
        """Test network timeout error"""
        error = GitHubApiError.from_network_error("Request timeout after 10s")
        assert error.code == "TIMEOUT"
        assert error.status is None
        assert error.retry_after_s is not None
        assert (
            "timed out" in error.message.lower() or "timeout" in error.message.lower()
        )

    def test_from_network_error_connection(self):
        """Test connection error"""
        error = GitHubApiError.from_network_error("Connection refused")
        assert error.code == "NETWORK"
        assert error.status is None
        assert (
            "network" in error.message.lower() or "connection" in error.message.lower()
        )

    def test_from_network_error_ssl(self):
        """Test SSL error"""
        error = GitHubApiError.from_network_error("SSL certificate verification failed")
        assert error.code == "NETWORK"
        assert error.status is None

    def test_from_json_error(self):
        """Test JSON parsing error"""
        error = GitHubApiError.from_json_error("Unexpected character at position 10")
        assert error.code == "BAD_RESPONSE"
        assert error.status is None
        assert "json" in error.details.lower()

    def test_error_str_representation(self):
        """Test string representation of error"""
        error = GitHubApiError(
            code="TEST_ERROR",
            message="This is a test error",
            details="Additional details",
        )
        assert str(error) == "This is a test error"

    def test_rate_limit_with_reset_time(self):
        """Test rate limit error includes reset time"""
        headers = {
            "x-ratelimit-remaining": "0",  # Required for RATE_LIMITED
            "x-ratelimit-reset": "1735660800",
        }
        error = GitHubApiError.from_http_error(403, headers=headers)  # Use 403
        assert error.rate_limit_reset_utc is not None
        # 1735660800 = 2024-12-31T16:00:00Z
        assert "2024" in error.rate_limit_reset_utc


class TestGitHubApiNetworkError:
    """Test GitHubApiNetworkError"""

    def test_create_network_error(self):
        """Test creating network error"""
        error = GitHubApiNetworkError("Connection failed")
        # GitHubApiNetworkError wraps from_network_error which adds message
        assert (
            "network" in error.message.lower() or "connection" in error.message.lower()
        )
        assert isinstance(error, GitHubApiError)

    def test_network_error_inheritance(self):
        """Test that network error is an Exception"""
        error = GitHubApiNetworkError("Test")
        assert isinstance(error, Exception)
