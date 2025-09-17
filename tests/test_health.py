"""Integration tests for health endpoints.

This module contains comprehensive integration tests for the health check endpoints,
including database connectivity checks and error handling.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Integration tests for health endpoints."""

    def test_health_check_success(self, client: TestClient):
        """Test successful health check."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "database" in data
        assert data["database"]["connected"] is True

    def test_health_check_database_error(self, client: TestClient):
        """Test health check with database connection error."""
        with patch("src.api_server.database.test_database_connection") as mock_test_db:
            mock_test_db.return_value = False

            response = client.get("/api/health")

            assert response.status_code == 503
            data = response.json()

            assert data["status"] == "unhealthy"
            assert data["database"]["connected"] is False
            assert "error" in data["database"]

    def test_health_check_response_format(self, client: TestClient):
        """Test health check response format."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        # Verify required fields
        required_fields = ["status", "timestamp", "database", "version"]
        for field in required_fields:
            assert field in data

        # Verify database info structure
        db_info = data["database"]
        assert "connected" in db_info
        assert isinstance(db_info["connected"], bool)

        if db_info["connected"]:
            assert "info" in db_info
            db_details = db_info["info"]
            assert "url" in db_details
            assert "pool_size" in db_details

    def test_health_check_headers(self, client: TestClient):
        """Test health check response headers."""
        response = client.get("/api/health")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_health_check_multiple_requests(self, client: TestClient):
        """Test multiple health check requests."""
        # Make multiple requests to ensure consistency
        for _ in range(3):
            response = client.get("/api/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"]["connected"] is True


class TestHealthEndpointPerformance:
    """Performance tests for health endpoints."""

    def test_health_check_response_time(self, client: TestClient, performance_timer):
        """Test health check response time."""
        performance_timer.start()
        response = client.get("/api/health")
        performance_timer.stop()

        assert response.status_code == 200

        # Health check should be fast (under 100ms)
        assert performance_timer.duration_ms < 100

    def test_health_check_concurrent_requests(self, client: TestClient):
        """Test health check with concurrent requests."""
        import concurrent.futures

        def make_request():
            return client.get("/api/health")

        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


class TestHealthEndpointEdgeCases:
    """Edge case tests for health endpoints."""

    def test_health_check_with_invalid_method(self, client: TestClient):
        """Test health check with invalid HTTP method."""
        response = client.post("/api/health")
        assert response.status_code == 405  # Method Not Allowed

        response = client.put("/api/health")
        assert response.status_code == 405

        response = client.delete("/api/health")
        assert response.status_code == 405

    def test_health_check_with_query_parameters(self, client: TestClient):
        """Test health check with query parameters (should be ignored)."""
        response = client.get("/api/health?param=value")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_check_with_headers(self, client: TestClient):
        """Test health check with custom headers."""
        headers = {
            "User-Agent": "Test Client",
            "Accept": "application/json",
            "Custom-Header": "test-value",
        }

        response = client.get("/api/health", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_check_case_sensitivity(self, client: TestClient):
        """Test health check URL case sensitivity."""
        # FastAPI routes are case-sensitive
        response = client.get("/api/HEALTH")
        assert response.status_code == 404

        response = client.get("/API/health")
        assert response.status_code == 404

        response = client.get("/api/Health")
        assert response.status_code == 404
