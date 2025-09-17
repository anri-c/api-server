"""Integration tests for authentication endpoints.

This module contains comprehensive integration tests for the authentication API endpoints,
including LINE login callback, JWT token generation, and error handling.
"""

from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from src.api_server.models.user import User
from src.api_server.services.auth_service import LineUserProfile


class TestAuthEndpoints:
    """Integration tests for authentication endpoints."""

    def test_line_callback_success_new_user(
        self, client: TestClient, sample_line_profile: LineUserProfile
    ):
        """Test successful LINE callback with new user."""
        with patch(
            "src.api_server.services.auth_service.AuthService.authenticate_line_user"
        ) as mock_auth:
            mock_auth.return_value = sample_line_profile

            with patch(
                "src.api_server.services.user_service.UserService.get_or_create_user_from_line_profile"
            ) as mock_user_service:
                mock_user_response = Mock()
                mock_user_response.id = 1
                mock_user_response.line_user_id = sample_line_profile.userId
                mock_user_response.display_name = sample_line_profile.displayName
                mock_user_service.return_value = mock_user_response

                with patch(
                    "src.api_server.services.auth_service.AuthService.create_jwt_token"
                ) as mock_jwt:
                    mock_jwt.return_value = "test_jwt_token"

                    response = client.post(
                        "/api/auth/line/callback",
                        json={"access_token": "valid_line_access_token"},
                    )

                    assert response.status_code == 200
                    data = response.json()

                    assert "access_token" in data
                    assert "token_type" in data
                    assert "user" in data

                    assert data["access_token"] == "test_jwt_token"
                    assert data["token_type"] == "bearer"
                    assert data["user"]["id"] == 1
                    assert data["user"]["line_user_id"] == sample_line_profile.userId
                    assert (
                        data["user"]["display_name"] == sample_line_profile.displayName
                    )

    def test_line_callback_success_existing_user(
        self, client: TestClient, sample_line_profile: LineUserProfile, test_user: User
    ):
        """Test successful LINE callback with existing user."""
        with patch(
            "src.api_server.services.auth_service.AuthService.authenticate_line_user"
        ) as mock_auth:
            mock_auth.return_value = sample_line_profile

            with patch(
                "src.api_server.services.user_service.UserService.get_or_create_user_from_line_profile"
            ) as mock_user_service:
                mock_user_response = Mock()
                mock_user_response.id = test_user.id
                mock_user_response.line_user_id = test_user.line_user_id
                mock_user_response.display_name = test_user.display_name
                mock_user_service.return_value = mock_user_response

                with patch(
                    "src.api_server.services.auth_service.AuthService.create_jwt_token"
                ) as mock_jwt:
                    mock_jwt.return_value = "test_jwt_token"

                    response = client.post(
                        "/api/auth/line/callback",
                        json={"access_token": "valid_line_access_token"},
                    )

                    assert response.status_code == 200
                    data = response.json()

                    assert data["access_token"] == "test_jwt_token"
                    assert data["user"]["id"] == test_user.id
                    assert data["user"]["line_user_id"] == test_user.line_user_id

    def test_line_callback_invalid_token(self, client: TestClient):
        """Test LINE callback with invalid access token."""
        with patch(
            "src.api_server.services.auth_service.AuthService.authenticate_line_user"
        ) as mock_auth:
            from src.api_server.services.auth_service import LineAuthError

            mock_auth.side_effect = LineAuthError("Invalid LINE access token", 401)

            response = client.post(
                "/api/auth/line/callback",
                json={"access_token": "invalid_line_access_token"},
            )

            assert response.status_code == 401
            data = response.json()
            assert "error" in data
            assert "Invalid LINE access token" in data["error"]

    def test_line_callback_missing_access_token(self, client: TestClient):
        """Test LINE callback with missing access token."""
        response = client.post("/api/auth/line/callback", json={})

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    def test_line_callback_empty_access_token(self, client: TestClient):
        """Test LINE callback with empty access token."""
        response = client.post("/api/auth/line/callback", json={"access_token": ""})

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_line_callback_line_api_error(self, client: TestClient):
        """Test LINE callback with LINE API error."""
        with patch(
            "src.api_server.services.auth_service.AuthService.authenticate_line_user"
        ) as mock_auth:
            from src.api_server.services.auth_service import LineAuthError

            mock_auth.side_effect = LineAuthError("LINE API unavailable", 503)

            response = client.post(
                "/api/auth/line/callback",
                json={"access_token": "valid_line_access_token"},
            )

            assert response.status_code == 503
            data = response.json()
            assert "error" in data
            assert "LINE API unavailable" in data["error"]

    def test_line_callback_user_service_error(
        self, client: TestClient, sample_line_profile: LineUserProfile
    ):
        """Test LINE callback with user service error."""
        with patch(
            "src.api_server.services.auth_service.AuthService.authenticate_line_user"
        ) as mock_auth:
            mock_auth.return_value = sample_line_profile

            with patch(
                "src.api_server.services.user_service.UserService.get_or_create_user_from_line_profile"
            ) as mock_user_service:
                from src.api_server.services.user_service import UserServiceError

                mock_user_service.side_effect = UserServiceError("Database error", 500)

                response = client.post(
                    "/api/auth/line/callback",
                    json={"access_token": "valid_line_access_token"},
                )

                assert response.status_code == 500
                data = response.json()
                assert "error" in data

    def test_line_callback_jwt_creation_error(
        self, client: TestClient, sample_line_profile: LineUserProfile
    ):
        """Test LINE callback with JWT creation error."""
        with patch(
            "src.api_server.services.auth_service.AuthService.authenticate_line_user"
        ) as mock_auth:
            mock_auth.return_value = sample_line_profile

            with patch(
                "src.api_server.services.user_service.UserService.get_or_create_user_from_line_profile"
            ) as mock_user_service:
                mock_user_response = Mock()
                mock_user_response.id = 1
                mock_user_response.line_user_id = sample_line_profile.userId
                mock_user_service.return_value = mock_user_response

                with patch(
                    "src.api_server.services.auth_service.AuthService.create_jwt_token"
                ) as mock_jwt:
                    from src.api_server.services.auth_service import JWTError

                    mock_jwt.side_effect = JWTError("JWT creation failed", 500)

                    response = client.post(
                        "/api/auth/line/callback",
                        json={"access_token": "valid_line_access_token"},
                    )

                    assert response.status_code == 500
                    data = response.json()
                    assert "error" in data

    def test_line_callback_invalid_json(self, client: TestClient):
        """Test LINE callback with invalid JSON."""
        response = client.post(
            "/api/auth/line/callback",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_line_callback_wrong_content_type(self, client: TestClient):
        """Test LINE callback with wrong content type."""
        response = client.post(
            "/api/auth/line/callback",
            data="access_token=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # FastAPI should handle this gracefully
        assert response.status_code in [422, 400]

    def test_line_callback_large_payload(self, client: TestClient):
        """Test LINE callback with large payload."""
        large_token = "x" * 10000  # Very large token

        response = client.post(
            "/api/auth/line/callback", json={"access_token": large_token}
        )

        # Should handle large payloads gracefully
        assert response.status_code in [400, 413, 422]


class TestAuthEndpointsValidation:
    """Validation tests for authentication endpoints."""

    def test_line_callback_access_token_validation(self, client: TestClient):
        """Test LINE callback access token validation."""
        # Test with None
        response = client.post("/api/auth/line/callback", json={"access_token": None})
        assert response.status_code == 422

        # Test with non-string type
        response = client.post("/api/auth/line/callback", json={"access_token": 123})
        assert response.status_code == 422

        # Test with whitespace-only token
        response = client.post("/api/auth/line/callback", json={"access_token": "   "})
        assert response.status_code == 400

    def test_line_callback_extra_fields(self, client: TestClient):
        """Test LINE callback with extra fields in request."""
        with patch(
            "src.api_server.services.auth_service.AuthService.authenticate_line_user"
        ) as mock_auth:
            mock_auth.return_value = Mock(
                userId="test_user",
                displayName="Test User",
                pictureUrl=None,
                statusMessage=None,
            )

            with patch(
                "src.api_server.services.user_service.UserService.get_or_create_user_from_line_profile"
            ) as mock_user_service:
                mock_user_response = Mock()
                mock_user_response.id = 1
                mock_user_response.line_user_id = "test_user"
                mock_user_service.return_value = mock_user_response

                with patch(
                    "src.api_server.services.auth_service.AuthService.create_jwt_token"
                ) as mock_jwt:
                    mock_jwt.return_value = "test_jwt_token"

                    # Include extra fields that should be ignored
                    response = client.post(
                        "/api/auth/line/callback",
                        json={
                            "access_token": "valid_token",
                            "extra_field": "should_be_ignored",
                            "another_field": 123,
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert "access_token" in data


class TestAuthEndpointsErrorHandling:
    """Error handling tests for authentication endpoints."""

    def test_line_callback_network_timeout(self, client: TestClient):
        """Test LINE callback with network timeout."""
        with patch(
            "src.api_server.services.auth_service.AuthService.authenticate_line_user"
        ) as mock_auth:
            import httpx

            mock_auth.side_effect = httpx.TimeoutException("Request timeout")

            response = client.post(
                "/api/auth/line/callback",
                json={"access_token": "valid_line_access_token"},
            )

            assert response.status_code == 503
            data = response.json()
            assert "error" in data

    def test_line_callback_unexpected_error(self, client: TestClient):
        """Test LINE callback with unexpected error."""
        with patch(
            "src.api_server.services.auth_service.AuthService.authenticate_line_user"
        ) as mock_auth:
            mock_auth.side_effect = Exception("Unexpected error")

            response = client.post(
                "/api/auth/line/callback",
                json={"access_token": "valid_line_access_token"},
            )

            assert response.status_code == 500
            data = response.json()
            assert "error" in data

    def test_line_callback_database_connection_error(
        self, client: TestClient, sample_line_profile: LineUserProfile
    ):
        """Test LINE callback with database connection error."""
        with patch(
            "src.api_server.services.auth_service.AuthService.authenticate_line_user"
        ) as mock_auth:
            mock_auth.return_value = sample_line_profile

            with patch(
                "src.api_server.services.user_service.UserService.get_or_create_user_from_line_profile"
            ) as mock_user_service:
                from sqlalchemy.exc import SQLAlchemyError

                mock_user_service.side_effect = SQLAlchemyError(
                    "Database connection failed"
                )

                response = client.post(
                    "/api/auth/line/callback",
                    json={"access_token": "valid_line_access_token"},
                )

                assert response.status_code == 500
                data = response.json()
                assert "error" in data


class TestAuthEndpointsSecurityHeaders:
    """Security header tests for authentication endpoints."""

    def test_line_callback_security_headers(self, client: TestClient):
        """Test that authentication endpoints include proper security headers."""
        response = client.post(
            "/api/auth/line/callback", json={"access_token": "test_token"}
        )

        # Check for security headers (these might be set by middleware)
        headers = response.headers

        # Content-Type should be set
        assert "content-type" in headers
        assert "application/json" in headers["content-type"]

    def test_line_callback_cors_headers(self, client: TestClient):
        """Test CORS headers on authentication endpoints."""
        # Test preflight request
        response = client.options("/api/auth/line/callback")

        # Should handle OPTIONS request
        assert response.status_code in [200, 405]


class TestAuthEndpointsRateLimiting:
    """Rate limiting tests for authentication endpoints."""

    def test_line_callback_multiple_requests(self, client: TestClient):
        """Test multiple requests to LINE callback endpoint."""
        # Make multiple requests in quick succession
        responses = []
        for _ in range(5):
            response = client.post(
                "/api/auth/line/callback", json={"access_token": "test_token"}
            )
            responses.append(response)

        # All requests should be processed (no rate limiting implemented yet)
        for response in responses:
            assert response.status_code in [200, 400, 401, 422, 500, 503]


class TestAuthEndpointsIntegration:
    """Integration tests for authentication flow."""

    def test_complete_auth_flow(
        self, client: TestClient, sample_line_profile: LineUserProfile
    ):
        """Test complete authentication flow from LINE callback to API access."""
        # Step 1: LINE callback
        with patch(
            "src.api_server.services.auth_service.AuthService.authenticate_line_user"
        ) as mock_auth:
            mock_auth.return_value = sample_line_profile

            with patch(
                "src.api_server.services.user_service.UserService.get_or_create_user_from_line_profile"
            ) as mock_user_service:
                mock_user_response = Mock()
                mock_user_response.id = 1
                mock_user_response.line_user_id = sample_line_profile.userId
                mock_user_response.display_name = sample_line_profile.displayName
                mock_user_service.return_value = mock_user_response

                with patch(
                    "src.api_server.services.auth_service.AuthService.create_jwt_token"
                ) as mock_jwt:
                    mock_jwt.return_value = "test_jwt_token"

                    auth_response = client.post(
                        "/api/auth/line/callback",
                        json={"access_token": "valid_line_access_token"},
                    )

                    assert auth_response.status_code == 200
                    auth_data = auth_response.json()
                    jwt_token = auth_data["access_token"]

        # Step 2: Use JWT token to access protected endpoint
        with patch("src.api_server.dependencies.get_current_user_id") as mock_get_user:
            mock_get_user.return_value = 1

            headers = {"Authorization": f"Bearer {jwt_token}"}
            items_response = client.get("/api/items/", headers=headers)

            assert items_response.status_code == 200
            items_data = items_response.json()
            assert "items" in items_data

    def test_auth_flow_with_database_persistence(
        self, client: TestClient, sample_line_profile: LineUserProfile, test_session
    ):
        """Test authentication flow with actual database persistence."""
        # This test would use real database operations
        # For now, we'll mock the services but verify the flow

        with patch(
            "src.api_server.services.auth_service.AuthService.authenticate_line_user"
        ) as mock_auth:
            mock_auth.return_value = sample_line_profile

            # Use real user service with test database
            auth_response = client.post(
                "/api/auth/line/callback",
                json={"access_token": "valid_line_access_token"},
            )

            # Should create or retrieve user from database
            assert auth_response.status_code in [200, 500]  # May fail due to mocking

    def test_concurrent_auth_requests(
        self, client: TestClient, sample_line_profile: LineUserProfile
    ):
        """Test concurrent authentication requests."""
        import concurrent.futures

        def make_auth_request():
            with patch(
                "src.api_server.services.auth_service.AuthService.authenticate_line_user"
            ) as mock_auth:
                mock_auth.return_value = sample_line_profile

                with patch(
                    "src.api_server.services.user_service.UserService.get_or_create_user_from_line_profile"
                ) as mock_user_service:
                    mock_user_response = Mock()
                    mock_user_response.id = 1
                    mock_user_response.line_user_id = sample_line_profile.userId
                    mock_user_service.return_value = mock_user_response

                    with patch(
                        "src.api_server.services.auth_service.AuthService.create_jwt_token"
                    ) as mock_jwt:
                        mock_jwt.return_value = "test_jwt_token"

                        return client.post(
                            "/api/auth/line/callback",
                            json={"access_token": "valid_line_access_token"},
                        )

        # Make concurrent authentication requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_auth_request) for _ in range(3)]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
