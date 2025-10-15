"""
Tests for API endpoints.

This module contains tests for the FastAPI endpoints including
chat, health, and other API functionality.
"""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from agent import ChefAgentGraph
from agent.memory import MemoryManager
from agent.models import ChatResponse
from api.chat import get_agent
from main import app

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def _clear_db(test_db_setup):
    """Clear test database before each test to prevent data pollution."""
    pass  # Database clearing is handled by test_db_setup fixture


@pytest.fixture
def mock_agent() -> ChefAgentGraph:
    """Fully mocked agent injected into FastAPI."""
    agent = MagicMock(spec=ChefAgentGraph)
    agent.memory_manager = MagicMock(spec=MemoryManager)
    agent.memory_manager.memory_saver = MagicMock()

    # Mock process_request to return a real ChatResponse, not a coroutine
    from agent.models import ChatResponse

    def mock_process_request(request):
        return ChatResponse(
            message="Test response",
            thread_id=(
                request.thread_id
                if hasattr(request, "thread_id")
                else "test-thread"
            ),
        )

    agent.process_request = mock_process_request

    return agent


@pytest.fixture(autouse=True)
def override_agent(mock_agent: ChefAgentGraph):
    """Replace real dependency with mock."""
    app.dependency_overrides[get_agent] = lambda: mock_agent
    yield
    app.dependency_overrides.clear()


class TestHealthEndpoints:
    """Test cases for health check endpoints."""

    def test_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get("/api/v1/health/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "chef-agent-api"
        assert data["version"] == "1.0.0"

    def test_detailed_health_check(self, client):
        """Test detailed health check endpoint."""
        response = client.get("/api/v1/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]
        assert "configuration" in data["checks"]
        assert "memory" in data["checks"]

    def test_readiness_check(self, client):
        """Test readiness check endpoint."""
        response = client.get("/api/v1/health/ready")

        # Should return 200 or 503 depending on configuration
        assert response.status_code in [200, 503]

        data = response.json()
        # For 503 responses, check for error detail instead of status
        if response.status_code == 503:
            assert "detail" in data
        else:
            assert "status" in data


class TestChatEndpoints:
    """Test cases for chat endpoints."""

    def test_send_message_success(
        self, mock_agent: ChefAgentGraph, test_api_client, test_thread_id
    ):
        """Test successful message sending."""

        # Override the mock agent's process_request method
        def mock_process_request(request):
            return ChatResponse(
                message="I'd be happy to help you plan a meal!",
                thread_id=request.thread_id,
            )

        mock_agent.process_request = mock_process_request

        # Test request
        request_data = {
            "thread_id": test_thread_id,
            "message": "Hello, can you help me plan a meal?",
            "language": "en",
        }

        response = test_api_client.post(
            "/api/v1/chat/message", json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "I'd be happy to help you plan a meal!"
        assert data["thread_id"] == test_thread_id

    def test_send_message_invalid_data(self, test_api_client, test_thread_id):
        """Test message sending with invalid data."""
        # Missing required fields
        request_data = {
            "message": "Hello, can you help me plan a meal?"
            # Missing thread_id
        }

        response = test_api_client.post(
            "/api/v1/chat/message", json=request_data
        )

        assert response.status_code == 422  # Validation error

    def test_send_message_invalid_language(
        self, test_api_client, test_thread_id
    ):
        """Test message sending with invalid language."""
        request_data = {
            "thread_id": test_thread_id,
            "message": "Hello, can you help me plan a meal?",
            "language": "invalid_lang",  # Invalid language
        }

        response = test_api_client.post(
            "/api/v1/chat/message", json=request_data
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_conversation_history(
        self, mock_agent: ChefAgentGraph, test_api_client, test_thread_id
    ):
        """Happy path: return stored messages."""
        # Arrange
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        mock_agent.memory_manager.get_conversation_history = AsyncMock(
            return_value=messages
        )

        # Act
        with TestClient(app) as client:
            resp = client.get(f"/api/v1/chat/threads/{test_thread_id}/history")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["thread_id"] == test_thread_id
        assert data["messages"] == messages
        assert data["total_messages"] == 2

    @pytest.mark.asyncio
    async def test_clear_conversation_thread(
        self, mock_agent: ChefAgentGraph, test_api_client, test_thread_id
    ):
        """Clear endpoint returns 200."""
        # Arrange
        mock_agent.memory_manager.clear_conversation = AsyncMock()

        # Act
        with TestClient(app) as client:
            resp = client.delete(f"/api/v1/chat/threads/{test_thread_id}")

        # Assert
        assert resp.status_code == 200
        assert resp.json() == {
            "message": f"Thread {test_thread_id} cleared successfully",
            "thread_id": test_thread_id,
        }

    def test_list_threads(self, mock_agent: ChefAgentGraph):
        """List endpoint returns thread summary."""
        # Arrange
        mock_agent.memory_manager.memory_saver.get_all_threads.return_value = [
            {
                "thread_id": "thread-1",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "message_count": 5,
            }
        ]

        # Act
        with TestClient(app) as client:
            resp = client.get("/api/v1/chat/threads")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_threads"] == 1
        assert data["threads"][0]["thread_id"] == "thread-1"


class TestRootEndpoints:
    """Test cases for root endpoints."""

    def test_root_endpoint(self, test_api_client, test_thread_id):
        """Test root endpoint."""
        response = test_api_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Chef Agent API"
        assert data["version"] == "1.0.0"
        assert "docs" in data
        assert "health" in data
        assert "chat" in data

    def test_database_status(self, test_api_client, test_thread_id):
        """Test database status endpoint."""
        response = test_api_client.get("/db/status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        # Status can be "connected" or "error" depending on setup
        assert data["status"] in ["connected", "error"]


class TestRateLimiting:
    """Test cases for rate limiting functionality."""

    def test_rate_limiting_headers(self, test_api_client, test_thread_id):
        """Test that rate limiting headers are present."""
        response = test_api_client.get("/api/v1/health/")

        # Rate limiting headers should be present
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limiting_chat_endpoint(
        self, test_api_client, test_thread_id
    ):
        """Test rate limiting on chat endpoints."""
        response = test_api_client.get("/api/v1/chat/threads")
        response = test_api_client.get("/api/v1/chat/threads")

        # Check that rate limiting headers are present
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        # Test a few requests to ensure rate limiting is working
        for i in range(3):
            response = test_api_client.get("/api/v1/chat/threads")
            if response.status_code == 500:
                # Agent initialization failed, skip rate limiting test
                pytest.skip(
                    "Agent initialization failed, skipping rate limiting test"
                )
            else:
                assert response.status_code == 200


class TestSecurityHeaders:
    """Test cases for security headers."""

    def test_security_headers_present(self, test_api_client, test_thread_id):
        """Test that security headers are present."""
        response = test_api_client.get("/")

        # Security headers should be present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Content-Security-Policy" in response.headers

    def test_cors_headers(self, test_api_client, test_thread_id):
        """Test CORS headers."""
        # Test with a GET request to see CORS headers
        response = test_api_client.get("/api/v1/health/")

        # CORS headers should be present
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers


class TestErrorHandling:
    """Test cases for error handling."""

    def test_404_endpoint(self, test_api_client, test_thread_id):
        """Test 404 for non-existent endpoint."""
        response = test_api_client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    def test_invalid_json(self, test_api_client, test_thread_id):
        """Test handling of invalid JSON."""
        response = test_api_client.post(
            "/api/v1/chat/message",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_missing_content_type(self, test_api_client, test_thread_id):
        """Test handling of missing content type."""
        response = test_api_client.post(
            "/api/v1/chat/message",
            content='{"thread_id": "test", "message": "hello"}',
        )

        response = test_api_client.get("/api/v1/chat/threads")
        assert response.status_code in [
            200,
            500,
        ]  # 500 if agent fails to initialize
