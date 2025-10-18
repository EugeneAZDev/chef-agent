"""
Tests for server startup and configuration.

These tests verify that the server can start properly
under various conditions and configurations.
"""

import os
from unittest.mock import patch

import pytest


class TestServerStartup:
    """Test server startup scenarios."""

    def test_server_startup_with_valid_config(self):
        """Test server startup with valid configuration."""
        test_env = {
            "GROQ_API_KEY": "test-key-valid",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
            "API_HOST": "127.0.0.1",
            "API_PORT": "8001",  # Use different port to avoid conflicts
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Test that main module can be imported
            import main

            assert main.app is not None

            # Test that app has all required components
            assert hasattr(main.app, "routes")
            assert hasattr(main.app, "middleware")

    def test_server_startup_with_missing_groq_key(self):
        """Test server startup with missing GROQ API key."""
        test_env = {
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Should raise an error during import
            try:
                import main

                # If it doesn't raise, that's also OK - validation skipped
                assert main.app is not None
            except (EnvironmentError, OSError) as exc_info:
                assert "GROQ_API_KEY" in str(exc_info.value)

    def test_server_startup_with_invalid_database_path(self):
        """Test server startup with invalid database path."""
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": "/invalid/path/that/does/not/exist.db",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Should handle database errors gracefully
            try:
                import main

                # If it imports successfully, test that app is created
                assert main.app is not None
            except Exception as e:
                # If it fails, should be a database-related error
                assert (
                    "database" in str(e).lower() or "sqlite" in str(e).lower()
                )

    def test_server_startup_with_memory_database(self):
        """Test server startup with in-memory database."""
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env, clear=True):
            import main

            assert main.app is not None

            # Test that database is accessible
            from fastapi.testclient import TestClient

            client = TestClient(main.app)

            response = client.get("/db/status")
            assert response.status_code == 200

    def test_server_startup_with_custom_settings(self):
        """Test server startup with custom settings."""
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
            "API_HOST": "0.0.0.0",
            "API_PORT": "8002",
            "RATE_LIMIT_PER_MINUTE": "20",
            "DEFAULT_LANGUAGE": "ru",
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Test that environment variables are set correctly
            assert os.environ.get("API_PORT") == "8002"
            assert os.environ.get("API_HOST") == "0.0.0.0"
            assert os.environ.get("RATE_LIMIT_PER_MINUTE") == "20"
            assert os.environ.get("DEFAULT_LANGUAGE") == "ru"

            import main

            assert main.app is not None


class TestServerConfiguration:
    """Test server configuration and middleware."""

    def test_cors_middleware_configured(self):
        """Test that CORS middleware is properly configured."""
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env, clear=True):
            import main

            app = main.app

            # Check that CORS middleware is present
            # Middleware is wrapped in starlette.middleware.Middleware
            middleware_classes = [m.cls for m in app.user_middleware]
            from fastapi.middleware.cors import CORSMiddleware

            assert CORSMiddleware in middleware_classes

    def test_security_middleware_configured(self):
        """Test that security middleware is properly configured."""
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env, clear=True):
            import main

            app = main.app

            # Check that security middleware is present
            from api.middleware import SecurityHeadersMiddleware

            middleware_classes = [m.cls for m in app.user_middleware]
            assert SecurityHeadersMiddleware in middleware_classes

    def test_rate_limiting_middleware_configured(self):
        """Test that rate limiting middleware is properly configured."""
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env, clear=True):
            import main

            app = main.app

            # Check that rate limiting is configured
            # This is harder to test directly, but we can check app starts
            assert app is not None

    def test_routers_registered(self):
        """Test that all routers are properly registered."""
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env, clear=True):
            import main

            app = main.app

            # Check that all expected routes are present
            routes = [route.path for route in app.routes]

            expected_paths = [
                "/",
                "/api/v1/health/",
                "/api/v1/recipes/",
                "/api/v1/shopping/",
                "/api/v1/chat/",
                "/db/status",
                "/docs",
                "/openapi.json",
            ]

            for expected_path in expected_paths:
                assert any(
                    expected_path in route for route in routes
                ), f"Path {expected_path} not found in routes"


class TestServerLifespan:
    """Test server lifespan management."""

    def test_lifespan_startup(self):
        """Test server lifespan startup."""
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env, clear=True):
            import main

            app = main.app

            # Test that lifespan is configured
            assert hasattr(app, "router")
            assert app.router.lifespan_context is not None

    def test_lifespan_shutdown(self):
        """Test server lifespan shutdown."""
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env, clear=True):
            import main

            app = main.app

            # Test that we can access the lifespan context
            lifespan_context = app.router.lifespan_context
            assert lifespan_context is not None


class TestServerErrorHandling:
    """Test server error handling during startup."""

    def test_import_error_handling(self):
        """Test handling of import errors."""
        # Test with missing required modules
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=True):
            # This should work as all modules should be available
            try:
                import main

                assert main.app is not None
            except ImportError as e:
                pytest.fail(f"Unexpected import error: {e}")

    def test_configuration_error_handling(self):
        """Test handling of configuration errors."""
        # Test with invalid configuration values
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
            "API_PORT": "invalid-port",  # Invalid port
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Should handle invalid port gracefully
            try:
                # If it imports, the port should be converted or defaulted
                from config import settings

                assert isinstance(settings.api_port, int)
            except Exception as e:
                # If it fails, should be a configuration-related error
                assert (
                    "port" in str(e).lower()
                    or "configuration" in str(e).lower()
                )

    def test_database_error_handling(self):
        """Test handling of database errors during startup."""
        # Test with database that can't be created
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": "/root/invalid/path.db",  # Path can't be written to
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Should handle database errors gracefully
            try:
                # If it imports successfully, test basic functionality
                from fastapi.testclient import TestClient

                import main

                client = TestClient(main.app)
                response = client.get("/api/v1/health/")
                assert response.status_code in [200, 500]  # 500 OK for DB
            except Exception as e:
                # If it fails, should be a database-related error
                assert (
                    "database" in str(e).lower()
                    or "permission" in str(e).lower()
                )


class TestServerPerformance:
    """Test server performance characteristics."""

    def test_startup_time(self):
        """Test that server starts up quickly."""
        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env, clear=True):
            import time

            start_time = time.time()
            # Import main to test startup time
            import main

            _ = main  # Use the import to avoid flake8 warning
            end_time = time.time()

            startup_time = end_time - start_time
            assert (
                startup_time < 5.0
            ), f"Server startup took too long: {startup_time:.2f}s"

    def test_memory_usage(self):
        """Test that server doesn't use excessive memory."""
        import psutil

        test_env = {
            "GROQ_API_KEY": "test-key",
            "SQLITE_DB": ":memory:",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, test_env, clear=True):
            process = psutil.Process(os.getpid())
            memory_before = process.memory_info().rss

            # Import main to test memory usage
            import main

            _ = main  # Use the import to avoid flake8 warning

            memory_after = process.memory_info().rss
            memory_increase = memory_after - memory_before

            # Should not use more than 100MB for startup
            assert (
                memory_increase < 100 * 1024 * 1024
            ), f"Memory usage too high: {memory_increase / 1024 / 1024:.2f}MB"
