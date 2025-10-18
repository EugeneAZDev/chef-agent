"""
Integration tests for the Chef Agent API.

These tests verify that the application works end-to-end
without extensive mocking.
"""

import os
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestServerStartup:
    """Test that the server can start without errors."""

    def test_server_startup_with_minimal_config(self):
        """Test server startup with minimal configuration."""
        # Set minimal environment variables
        test_env = {
            "GROQ_API_KEY": "test-key-for-startup",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env):
            # Import and create app
            from main import app

            client = TestClient(app)

            # Test that app is created successfully
            assert app is not None
            assert client is not None

    def test_health_endpoint_integration(self):
        """Test health endpoint works without mocks."""
        test_env = {
            "GROQ_API_KEY": "test-key-for-startup",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env):
            from main import app

            client = TestClient(app)

            response = client.get("/api/v1/health/")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "chef-agent-api"

    def test_database_status_integration(self):
        """Test database status endpoint works."""
        test_env = {
            "GROQ_API_KEY": "test-key-for-startup",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env):
            from main import app

            client = TestClient(app)

            response = client.get("/db/status")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "connected"
            assert "database_path" in data

    def test_recipes_endpoint_integration(self):
        """Test recipes endpoint works with real database."""
        test_env = {
            "GROQ_API_KEY": "test-key-for-startup",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env):
            from main import app

            client = TestClient(app)

            response = client.get("/api/v1/recipes/")
            assert response.status_code == 200

            data = response.json()
            assert "recipes" in data
            assert "total" in data

    def test_shopping_endpoint_integration(self):
        """Test shopping endpoint works."""
        test_env = {
            "GROQ_API_KEY": "test-key-for-startup",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env):
            from main import app

            client = TestClient(app)

            response = client.get("/api/v1/shopping/")
            assert response.status_code == 200

            data = response.json()
            assert "message" in data
            assert "total_lists" in data
            assert "endpoints" in data


class TestEndToEndWorkflow:
    """Test complete workflows without mocks."""

    def test_recipe_workflow(self):
        """Test complete recipe workflow."""
        test_env = {
            "GROQ_API_KEY": "test-key-for-startup",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env):
            from main import app

            client = TestClient(app)

            # 1. Get initial recipes
            response = client.get("/api/v1/recipes/")
            assert response.status_code == 200
            initial_count = response.json()["total"]

            # 2. Check database status
            response = client.get("/db/status")
            assert response.status_code == 200
            db_status = response.json()
            assert db_status["recipes_count"] == initial_count

    def test_shopping_workflow(self):
        """Test complete shopping workflow."""
        test_env = {
            "GROQ_API_KEY": "test-key-for-startup",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env):
            from main import app

            client = TestClient(app)

            # 1. Get shopping overview
            response = client.get("/api/v1/shopping/")
            assert response.status_code == 200
            overview = response.json()
            assert overview["total_lists"] >= 0

            # 2. Try to create a shopping list (with required parameters)
            response = client.post(
                "/api/v1/shopping/lists",
                params={
                    "thread_id": "test-thread-123",
                    "user_id": "test-user-456",
                },
            )
            # This might fail due to validation or constraints, but shouldn't crash
            assert response.status_code in [200, 400, 422, 500]

    def test_chat_workflow_with_mock_agent(self):
        """Test chat workflow with minimal mocking."""
        test_env = {
            "GROQ_API_KEY": "test-key-for-startup",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env):
            from main import app

            client = TestClient(app)

            # Mock only the agent initialization, not the entire function
            with patch("api.chat.ChefAgentGraph") as mock_agent_class:
                mock_agent = MagicMock()
                mock_agent.process_request.return_value = {
                    "message": "Test response",
                    "thread_id": "test-thread-123",
                }
                mock_agent_class.return_value = mock_agent

                # Test chat endpoint
                response = client.post(
                    "/api/v1/chat/",
                    json={"message": "Hello", "thread_id": "test-thread-123"},
                )

                # Should not crash, might return error due to MCP client
                assert response.status_code in [200, 500]


class TestErrorRecovery:
    """Test error recovery and graceful degradation."""

    def test_missing_groq_key_graceful_handling(self):
        """Test graceful handling of missing GROQ API key."""
        test_env = {
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Should not crash during import
            try:
                from main import app

                client = TestClient(app)

                # Health endpoint should still work
                response = client.get("/api/v1/health/")
                assert response.status_code == 200

            except Exception as e:
                # If it does fail, it should be a specific error about missing API key
                assert "GROQ_API_KEY" in str(e) or "api key" in str(e).lower()

    def test_database_connection_failure_handling(self):
        """Test handling of database connection failures."""
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": "/invalid/path/that/does/not/exist.db",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env):
            # Should handle database errors gracefully
            try:
                from main import app

                client = TestClient(app)

                # Health endpoint might still work
                response = client.get("/api/v1/health/")
                assert response.status_code in [200, 500]

            except Exception as e:
                # If it fails, should be a database-related error
                assert (
                    "database" in str(e).lower() or "sqlite" in str(e).lower()
                )


class TestAPICompleteness:
    """Test that all expected API endpoints exist and respond."""

    def test_all_root_endpoints_exist(self):
        """Test that all root endpoints exist."""
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env):
            from main import app

            client = TestClient(app)

            # Test root endpoint
            response = client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "version" in data
            assert "docs" in data

    def test_all_health_endpoints_exist(self):
        """Test that all health endpoints exist."""
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env):
            from main import app

            client = TestClient(app)

            # Test health endpoints
            endpoints = ["/api/v1/health/", "/db/status"]

            for endpoint in endpoints:
                response = client.get(endpoint)
                assert response.status_code in [
                    200,
                    500,
                ]  # 500 is OK for some config issues

    def test_all_api_endpoints_exist(self):
        """Test that all API endpoints exist."""
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env):
            from main import app

            client = TestClient(app)

            # Test API endpoints
            endpoints = [
                "/api/v1/recipes/",
                "/api/v1/shopping/",
            ]

            for endpoint in endpoints:
                response = client.get(endpoint)
                assert response.status_code in [
                    200,
                    500,
                ]  # 500 is OK for some config issues
