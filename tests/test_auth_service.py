"""Unit tests for AuthService.

This module contains comprehensive unit tests for the AuthService class,
including LINE OAuth verification, JWT token management, and error handling.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import httpx
import pytest
from jose import jwt

from src.api_server.config import Settings
from src.api_server.services.auth_service import (
    AuthenticationError,
    AuthService,
    JWTError,
    JWTPayload,
    LineAuthError,
    LineTokenInfo,
    LineUserProfile,
)


class TestAuthService:
    """Test cases for AuthService."""

    @pytest.fixture
    def auth_service(self, test_settings: Settings) -> AuthService:
        """Create AuthService instance for testing."""
        return AuthService(test_settings)

    @pytest.fixture
    def sample_line_token_response(self) -> dict:
        """Sample LINE token verification response."""
        return {"scope": "profile", "client_id": "test_client_id", "expires_in": 3600}

    @pytest.fixture
    def sample_line_profile_response(self) -> dict:
        """Sample LINE profile response."""
        return {
            "userId": "test_line_user_123",
            "displayName": "Test User",
            "pictureUrl": "https://example.com/profile.jpg",
            "statusMessage": "Hello, World!",
        }

    @pytest.mark.asyncio
    async def test_verify_line_access_token_success(
        self, auth_service: AuthService, sample_line_token_response: dict
    ):
        """Test successful LINE access token verification."""
        with patch("httpx.AsyncClient") as mock_client:
            # Setup mock response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_line_token_response

            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            # Test token verification
            result = await auth_service.verify_line_access_token("valid_token")

            # Assertions
            assert isinstance(result, LineTokenInfo)
            assert result.scope == "profile"
            assert result.client_id == "test_client_id"
            assert result.expires_in == 3600

            # Verify API call was made correctly
            mock_client.return_value.__aenter__.return_value.get.assert_called_once_with(
                auth_service.LINE_TOKEN_VERIFY_URL,
                params={"access_token": "valid_token"},
                timeout=10.0,
            )

    @pytest.mark.asyncio
    async def test_verify_line_access_token_invalid_token(
        self, auth_service: AuthService
    ):
        """Test LINE access token verification with invalid token."""
        with patch("httpx.AsyncClient") as mock_client:
            # Setup mock response for invalid token
            mock_response = Mock()
            mock_response.status_code = 401

            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            # Test token verification with invalid token
            with pytest.raises(LineAuthError) as exc_info:
                await auth_service.verify_line_access_token("invalid_token")

            assert exc_info.value.status_code == 401
            assert "LINE token verification failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_line_access_token_wrong_client_id(
        self, auth_service: AuthService, sample_line_token_response: dict
    ):
        """Test LINE access token verification with wrong client ID."""
        with patch("httpx.AsyncClient") as mock_client:
            # Setup mock response with wrong client ID
            wrong_client_response = sample_line_token_response.copy()
            wrong_client_response["client_id"] = "wrong_client_id"

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = wrong_client_response

            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            # Test token verification with wrong client ID
            with pytest.raises(LineAuthError) as exc_info:
                await auth_service.verify_line_access_token("valid_token")

            assert exc_info.value.status_code == 401
            assert "Invalid client ID in token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_line_access_token_network_error(
        self, auth_service: AuthService
    ):
        """Test LINE access token verification with network error."""
        with patch("httpx.AsyncClient") as mock_client:
            # Setup mock to raise network error
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                httpx.RequestError("Network error")
            )

            # Test token verification with network error
            with pytest.raises(LineAuthError) as exc_info:
                await auth_service.verify_line_access_token("valid_token")

            assert exc_info.value.status_code == 503
            assert "Failed to connect to LINE API" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_line_user_profile_success(
        self, auth_service: AuthService, sample_line_profile_response: dict
    ):
        """Test successful LINE user profile retrieval."""
        with patch("httpx.AsyncClient") as mock_client:
            # Setup mock response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_line_profile_response

            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            # Test profile retrieval
            result = await auth_service.get_line_user_profile("valid_token")

            # Assertions
            assert isinstance(result, LineUserProfile)
            assert result.userId == "test_line_user_123"
            assert result.displayName == "Test User"
            assert result.pictureUrl == "https://example.com/profile.jpg"
            assert result.statusMessage == "Hello, World!"

            # Verify API call was made correctly
            mock_client.return_value.__aenter__.return_value.get.assert_called_once_with(
                auth_service.LINE_PROFILE_API_URL,
                headers={"Authorization": "Bearer valid_token"},
                timeout=10.0,
            )

    @pytest.mark.asyncio
    async def test_get_line_user_profile_invalid_token(self, auth_service: AuthService):
        """Test LINE user profile retrieval with invalid token."""
        with patch("httpx.AsyncClient") as mock_client:
            # Setup mock response for invalid token
            mock_response = Mock()
            mock_response.status_code = 401

            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            # Test profile retrieval with invalid token
            with pytest.raises(LineAuthError) as exc_info:
                await auth_service.get_line_user_profile("invalid_token")

            assert exc_info.value.status_code == 401
            assert "Failed to get LINE user profile" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authenticate_line_user_success(
        self,
        auth_service: AuthService,
        sample_line_token_response: dict,
        sample_line_profile_response: dict,
    ):
        """Test successful LINE user authentication."""
        with patch("httpx.AsyncClient") as mock_client:
            # Setup mock responses for both token verification and profile retrieval
            mock_responses = [
                Mock(
                    status_code=200, json=Mock(return_value=sample_line_token_response)
                ),
                Mock(
                    status_code=200,
                    json=Mock(return_value=sample_line_profile_response),
                ),
            ]

            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                mock_responses
            )

            # Test user authentication
            result = await auth_service.authenticate_line_user("valid_token")

            # Assertions
            assert isinstance(result, LineUserProfile)
            assert result.userId == "test_line_user_123"
            assert result.displayName == "Test User"

    def test_create_jwt_token_success(self, auth_service: AuthService):
        """Test successful JWT token creation."""
        user_id = 123
        line_user_id = "test_line_user_123"

        # Create JWT token
        token = auth_service.create_jwt_token(user_id, line_user_id)

        # Verify token is a string
        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify token payload (without expiration validation for testing)
        payload = jwt.decode(
            token,
            auth_service.jwt_secret,
            algorithms=[auth_service.jwt_algorithm],
            options={"verify_exp": False},  # Skip expiration validation for testing
        )

        assert payload["sub"] == str(user_id)
        assert payload["line_user_id"] == line_user_id
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_jwt_token_success(self, auth_service: AuthService):
        """Test successful JWT token verification."""
        user_id = 123
        line_user_id = "test_line_user_123"

        # Mock datetime to ensure token doesn't expire during test
        with patch("src.api_server.services.auth_service.datetime") as mock_datetime:
            fixed_time = datetime(2025, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = fixed_time

            # Create token
            token = auth_service.create_jwt_token(user_id, line_user_id)

            # Verify token (still using mocked time)
            payload = auth_service.verify_jwt_token(token)

            # Assertions
            assert isinstance(payload, JWTPayload)
            assert payload.sub == str(user_id)
            assert payload.line_user_id == line_user_id

    def test_verify_jwt_token_expired(self, auth_service: AuthService):
        """Test JWT token verification with expired token."""
        # Create expired token
        now = datetime.utcnow()
        expired_payload = {
            "sub": "123",
            "line_user_id": "test_line_user_123",
            "exp": int((now - timedelta(minutes=1)).timestamp()),
            "iat": int(now.timestamp()),
        }

        expired_token = jwt.encode(
            expired_payload,
            auth_service.jwt_secret,
            algorithm=auth_service.jwt_algorithm,
        )

        # Test token verification with expired token
        with pytest.raises(JWTError) as exc_info:
            auth_service.verify_jwt_token(expired_token)

        assert exc_info.value.status_code == 401
        assert "Token has expired" in str(exc_info.value)

    def test_verify_jwt_token_invalid(self, auth_service: AuthService):
        """Test JWT token verification with invalid token."""
        invalid_token = "invalid.jwt.token"

        # Test token verification with invalid token
        with pytest.raises(JWTError) as exc_info:
            auth_service.verify_jwt_token(invalid_token)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value)

    def test_extract_token_from_header_success(self, auth_service: AuthService):
        """Test successful token extraction from Authorization header."""
        authorization = "Bearer test_jwt_token"

        token = auth_service.extract_token_from_header(authorization)

        assert token == "test_jwt_token"

    def test_extract_token_from_header_missing(self, auth_service: AuthService):
        """Test token extraction with missing Authorization header."""
        with pytest.raises(JWTError) as exc_info:
            auth_service.extract_token_from_header(None)

        assert exc_info.value.status_code == 401
        assert "Authorization header is missing" in str(exc_info.value)

    def test_extract_token_from_header_invalid_scheme(self, auth_service: AuthService):
        """Test token extraction with invalid authorization scheme."""
        authorization = "Basic test_token"

        with pytest.raises(JWTError) as exc_info:
            auth_service.extract_token_from_header(authorization)

        assert exc_info.value.status_code == 401
        assert "Invalid authorization scheme" in str(exc_info.value)

    def test_extract_token_from_header_invalid_format(self, auth_service: AuthService):
        """Test token extraction with invalid header format."""
        authorization = "InvalidFormat"

        with pytest.raises(JWTError) as exc_info:
            auth_service.extract_token_from_header(authorization)

        assert exc_info.value.status_code == 401
        assert "Invalid authorization header format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_current_user_id_success(self, auth_service: AuthService):
        """Test successful current user ID extraction."""
        user_id = 123
        line_user_id = "test_line_user_123"

        # Mock datetime to ensure token doesn't expire during test
        with patch("src.api_server.services.auth_service.datetime") as mock_datetime:
            fixed_time = datetime(2025, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = fixed_time

            # Create valid token
            token = auth_service.create_jwt_token(user_id, line_user_id)
            authorization = f"Bearer {token}"

            # Get current user ID (still using mocked time)
            result = await auth_service.get_current_user_id(authorization)

            assert result == user_id

    @pytest.mark.asyncio
    async def test_get_current_user_id_invalid_user_id(self, auth_service: AuthService):
        """Test current user ID extraction with invalid user ID in token."""
        # Mock datetime to ensure token doesn't expire during test
        with patch("src.api_server.services.auth_service.datetime") as mock_datetime:
            fixed_time = datetime(2025, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = fixed_time

            # Create token with invalid user ID
            invalid_payload = {
                "sub": "invalid_user_id",
                "line_user_id": "test_line_user_123",
                "exp": int((fixed_time + timedelta(minutes=60)).timestamp()),
                "iat": int(fixed_time.timestamp()),
            }

            invalid_token = jwt.encode(
                invalid_payload,
                auth_service.jwt_secret,
                algorithm=auth_service.jwt_algorithm,
            )

            authorization = f"Bearer {invalid_token}"

            # Test user ID extraction with invalid user ID
            with pytest.raises(JWTError) as exc_info:
                await auth_service.get_current_user_id(authorization)

            assert exc_info.value.status_code == 401
            assert "Invalid user ID in token" in str(exc_info.value)


class TestAuthServiceExceptions:
    """Test cases for AuthService exception classes."""

    def test_authentication_error(self):
        """Test AuthenticationError exception."""
        error = AuthenticationError("Test error", 401)

        assert error.message == "Test error"
        assert error.status_code == 401
        assert str(error) == "Test error"

    def test_line_auth_error(self):
        """Test LineAuthError exception."""
        error = LineAuthError("LINE error", 401)

        assert error.message == "LINE error"
        assert error.status_code == 401
        assert isinstance(error, AuthenticationError)

    def test_jwt_error(self):
        """Test JWTError exception."""
        error = JWTError("JWT error", 401)

        assert error.message == "JWT error"
        assert error.status_code == 401
        assert isinstance(error, AuthenticationError)


class TestAuthServiceModels:
    """Test cases for AuthService data models."""

    def test_line_user_profile_model(self):
        """Test LineUserProfile model."""
        profile = LineUserProfile(
            userId="test_user_123",
            displayName="Test User",
            pictureUrl="https://example.com/profile.jpg",
            statusMessage="Hello!",
        )

        assert profile.userId == "test_user_123"
        assert profile.displayName == "Test User"
        assert profile.pictureUrl == "https://example.com/profile.jpg"
        assert profile.statusMessage == "Hello!"

    def test_line_user_profile_optional_fields(self):
        """Test LineUserProfile model with optional fields."""
        profile = LineUserProfile(userId="test_user_123", displayName="Test User")

        assert profile.userId == "test_user_123"
        assert profile.displayName == "Test User"
        assert profile.pictureUrl is None
        assert profile.statusMessage is None

    def test_line_token_info_model(self):
        """Test LineTokenInfo model."""
        token_info = LineTokenInfo(
            scope="profile", client_id="test_client_id", expires_in=3600
        )

        assert token_info.scope == "profile"
        assert token_info.client_id == "test_client_id"
        assert token_info.expires_in == 3600

    def test_jwt_payload_model(self):
        """Test JWTPayload model."""
        now = datetime.utcnow()
        payload = JWTPayload(
            sub="123",
            line_user_id="test_line_user_123",
            exp=int((now + timedelta(minutes=60)).timestamp()),
            iat=int(now.timestamp()),
        )

        assert payload.sub == "123"
        assert payload.line_user_id == "test_line_user_123"
        assert payload.exp > payload.iat
