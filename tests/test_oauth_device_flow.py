"""
Tests for auth.oauth_device_flow module - OAuth Device Flow implementation
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from freecad.gitpdm.auth.oauth_device_flow import (
    DeviceFlowError,
    DeviceCodeResponse,
    TokenResponse,
    request_device_code,
    poll_for_token,
)


class TestDeviceFlowError:
    """Test DeviceFlowError exception"""

    def test_create_error(self):
        """Test creating device flow error"""
        error = DeviceFlowError("authorization_pending", "User hasn't authorized yet")
        assert error.error_code == "authorization_pending"
        assert error.error_description == "User hasn't authorized yet"
        assert "authorization_pending" in str(error)

    def test_error_without_description(self):
        """Test error without description"""
        error = DeviceFlowError("expired_token")
        assert error.error_code == "expired_token"
        assert error.error_description == ""


class TestDeviceCodeResponse:
    """Test DeviceCodeResponse dataclass"""

    def test_create_response(self):
        """Test creating device code response"""
        response = DeviceCodeResponse(
            device_code="device123",
            user_code="USER-CODE",
            verification_uri="https://github.com/login/device",
            expires_in=900,
            interval=5,
        )
        assert response.device_code == "device123"
        assert response.user_code == "USER-CODE"
        assert response.verification_uri == "https://github.com/login/device"
        assert response.expires_in == 900
        assert response.interval == 5


class TestTokenResponse:
    """Test TokenResponse dataclass"""

    def test_create_token_response(self):
        """Test creating token response"""
        response = TokenResponse(
            access_token="ghp_test123",
            token_type="bearer",
            scope="repo read:user",
            refresh_token="refresh123",
            expires_in=28800,
            obtained_at_utc="2025-12-31T12:00:00Z",
        )
        assert response.access_token == "ghp_test123"
        assert response.token_type == "bearer"
        assert response.scope == "repo read:user"
        assert response.refresh_token == "refresh123"
        assert response.expires_in == 28800


class TestRequestDeviceCode:
    """Test request_device_code function"""

    @patch("urllib.request.urlopen")
    def test_successful_request(self, mock_urlopen):
        """Test successful device code request"""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "device_code": "3584d83530557fdd1f46af8289938c8ef79f9dc5",
                "user_code": "WDJB-MJHT",
                "verification_uri": "https://github.com/login/device",
                "expires_in": 900,
                "interval": 5,
            }
        ).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = request_device_code(
            client_id="test_client_id", scopes=["repo", "read:user"]
        )

        assert result.device_code == "3584d83530557fdd1f46af8289938c8ef79f9dc5"
        assert result.user_code == "WDJB-MJHT"
        assert result.verification_uri == "https://github.com/login/device"
        assert result.expires_in == 900
        assert result.interval == 5

    @patch("urllib.request.urlopen")
    def test_http_error(self, mock_urlopen):
        """Test handling HTTP error"""
        from urllib.error import HTTPError

        mock_error = HTTPError(
            url="https://github.com/login/device/code",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=MagicMock(read=lambda: b'{"error": "bad_request"}'),
        )
        mock_urlopen.side_effect = mock_error

        with pytest.raises(DeviceFlowError) as exc_info:
            request_device_code(client_id="test_client_id", scopes=["repo"])
        assert exc_info.value.error_code == "http_error"

    @patch("urllib.request.urlopen")
    def test_network_error(self, mock_urlopen):
        """Test handling network error"""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")

        with pytest.raises(URLError):
            request_device_code(client_id="test_client_id", scopes=["repo"])

    @patch("urllib.request.urlopen")
    def test_invalid_json_response(self, mock_urlopen):
        """Test handling invalid JSON response"""
        mock_response = MagicMock()
        mock_response.read.return_value = b"not valid json"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        with pytest.raises(json.JSONDecodeError):
            request_device_code(client_id="test_client_id", scopes=["repo"])


class TestPollForToken:
    """Test poll_for_token function"""

    @patch("urllib.request.urlopen")
    @patch("time.time")
    def test_successful_authorization(self, mock_time, mock_urlopen):
        """Test successful token polling"""
        mock_time.return_value = 1000000  # Fixed time for testing

        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "access_token": "ghp_test_access_token",
                "token_type": "bearer",
                "scope": "repo,read:user",
            }
        ).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = poll_for_token(
            client_id="test_client_id",
            device_code="test_device_code",
            interval=5,
            expires_in=900,
        )

        assert result.access_token == "ghp_test_access_token"
        assert result.token_type == "bearer"
        assert result.scope == "repo,read:user"

    @patch("urllib.request.urlopen")
    @patch("time.time")
    def test_authorization_pending(self, mock_time, mock_urlopen):
        """Test authorization pending continues polling then stops"""
        from urllib.error import HTTPError

        mock_time.return_value = 1000000

        # First call returns authorization_pending
        mock_response1 = MagicMock()
        mock_response1.read.return_value = json.dumps(
            {
                "error": "authorization_pending",
                "error_description": "User has not yet authorized",
            }
        ).encode("utf-8")
        mock_response1.__enter__ = Mock(return_value=mock_response1)
        mock_response1.__exit__ = Mock(return_value=False)

        # Second call also returns authorization_pending
        mock_response2 = MagicMock()
        mock_response2.read.return_value = json.dumps(
            {
                "error": "authorization_pending",
                "error_description": "User has not yet authorized",
            }
        ).encode("utf-8")
        mock_response2.__enter__ = Mock(return_value=mock_response2)
        mock_response2.__exit__ = Mock(return_value=False)

        # Third call returns expired to exit the loop
        mock_response3 = MagicMock()
        mock_response3.read.return_value = json.dumps(
            {"error": "expired_token", "error_description": "Device code expired"}
        ).encode("utf-8")
        mock_response3.__enter__ = Mock(return_value=mock_response3)
        mock_response3.__exit__ = Mock(return_value=False)

        mock_urlopen.side_effect = [mock_response1, mock_response2, mock_response3]

        with pytest.raises(DeviceFlowError) as exc_info:
            poll_for_token(
                client_id="test_client_id",
                device_code="test_device_code",
                interval=1,  # Short interval for testing
                expires_in=900,
            )
        # Final error should be expired_token
        assert exc_info.value.error_code == "expired_token"

    @patch("urllib.request.urlopen")
    @patch("time.time")
    def test_expired_token(self, mock_time, mock_urlopen):
        """Test expired token error"""
        mock_time.return_value = 1000000

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"error": "expired_token", "error_description": "Device code expired"}
        ).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        with pytest.raises(DeviceFlowError) as exc_info:
            poll_for_token(
                client_id="test_client_id",
                device_code="test_device_code",
                interval=5,
                expires_in=900,
            )
        assert exc_info.value.error_code == "expired_token"
