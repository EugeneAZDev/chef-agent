"""
Test real agent message processing.
"""

import pytest

from agent import ChefAgentGraph
from agent.models import ChatRequest
from config import settings


class TestAgentMessageProcessing:
    """Test real agent message processing."""

    def setup_method(self):
        """Set up test fixtures."""
        # Set test database path
        import adapters.db.database

        adapters.db.database.DEFAULT_DB_PATH = "test_chef_agent.db"

        # Clear database before each test
        from adapters.db.database import Database

        db = Database()
        db.execute_update("DELETE FROM shopping_lists")
        db.execute_update("DELETE FROM recipe_ingredients")
        db.execute_update("DELETE FROM recipe_tags")
        db.execute_update("DELETE FROM recipes")

        # Use fallback mode (no MCP client) for testing
        self.agent = ChefAgentGraph(
            llm_provider="groq",
            api_key=settings.groq_api_key,
            mcp_client=None,  # Use fallback mode
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        # No cleanup needed for fallback mode
        pass

    @pytest.mark.asyncio
    async def test_agent_process_request_vegetarian(self):
        """Test that agent processes vegetarian request correctly."""
        request = ChatRequest(
            thread_id="test_thread_vegetarian",
            message="vegetarian",
            user_id="test_user",
        )

        response = await self.agent.process_request(request)

        assert response is not None
        assert hasattr(response, "message")
        assert response.message is not None

        # Should not return generic message
        generic_message = (
            "I'm here to help you plan your meals! Please tell me about "
            "your dietary goals"
        )
        assert (
            generic_message not in response.message
        ), f"Agent returned generic message: {response.message}"

        print(f"Agent response: {response.message}")

    @pytest.mark.asyncio
    async def test_agent_process_request_traditional(self):
        """Test that agent processes traditional request correctly."""
        request = ChatRequest(
            thread_id="test_thread_traditional",
            message="traditional ukrainian cooking",
            user_id="test_user",
        )

        response = await self.agent.process_request(request)

        assert response is not None
        assert hasattr(response, "message")
        assert response.message is not None

        # Should not return generic message
        generic_message = (
            "I'm here to help you plan your meals! Please tell me about "
            "your dietary goals"
        )
        assert (
            generic_message not in response.message
        ), f"Agent returned generic message: {response.message}"

        print(f"Agent response: {response.message}")

    @pytest.mark.asyncio
    async def test_agent_process_request_with_days(self):
        """Test that agent processes request with days correctly."""
        request = ChatRequest(
            thread_id="test_thread_days",
            message="vegetarian for 3 days",
            user_id="test_user",
        )

        response = await self.agent.process_request(request)

        assert response is not None
        assert hasattr(response, "message")
        assert response.message is not None

        # Should not return generic message
        generic_message = (
            "I'm here to help you plan your meals! Please tell me about "
            "your dietary goals"
        )
        assert (
            generic_message not in response.message
        ), f"Agent returned generic message: {response.message}"

        print(f"Agent response: {response.message}")

    @pytest.mark.asyncio
    async def test_agent_state_transitions(self):
        """Test that agent state transitions work correctly."""
        thread_id = "test_thread_transitions"

        # First message - should set diet goal
        request1 = ChatRequest(
            thread_id=thread_id, message="vegetarian", user_id="test_user"
        )

        response1 = await self.agent.process_request(request1)
        print(f"First response: {response1.message}")

        # Second message - should ask for days or create meal plan
        request2 = ChatRequest(
            thread_id=thread_id, message="3 days", user_id="test_user"
        )

        response2 = await self.agent.process_request(request2)
        print(f"Second response: {response2.message}")

        # Should not return generic message on second call
        generic_message = (
            "I'm here to help you plan your meals! Please tell me about "
            "your dietary goals"
        )
        assert generic_message not in response2.message, (
            f"Agent returned generic message on second call: "
            f"{response2.message}"
        )

    @pytest.mark.asyncio
    async def test_agent_creates_meal_plan(self):
        """Test that agent creates meal plan when given complete information."""
        request = ChatRequest(
            thread_id="test_thread_meal_plan",
            message="vegetarian for 3 days",
            user_id="test_user",
        )

        response = await self.agent.process_request(request)

        assert response is not None
        assert hasattr(response, "message")

        # Check if agent created meal plan or shopping list
        has_meal_plan = (
            hasattr(response, "menu_plan") and response.menu_plan is not None
        )
        has_shopping_list = (
            hasattr(response, "shopping_list")
            and response.shopping_list is not None
        )

        print(f"Response: {response.message}")
        print(f"Has meal plan: {has_meal_plan}")
        print(f"Has shopping list: {has_shopping_list}")

        # At least one should be created
        assert (
            has_meal_plan or has_shopping_list
        ), "Agent should create either meal plan or shopping list"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
