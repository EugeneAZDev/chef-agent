"""
Test step-by-step agent message processing.
"""

import asyncio

import pytest

from adapters.mcp.http_client import ChefAgentHTTPMCPClient
from agent.graph import ChefAgentGraph
from agent.models import AgentState, ChatRequest, ConversationState
from config import settings


class TestAgentStepByStep:
    """Test agent message processing step by step."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_client = ChefAgentHTTPMCPClient()
        self.agent = ChefAgentGraph(
            llm_provider="groq",
            api_key=settings.groq_api_key,
            mcp_client=self.mcp_client,
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        if hasattr(self, "mcp_client"):
            asyncio.run(self.mcp_client.close())

    def test_initial_state_creation(self):
        """Test that initial state is created correctly."""
        request = ChatRequest(
            thread_id="test_thread", message="vegetarian", user_id="test_user"
        )

        # Create initial state
        state = AgentState(
            thread_id=request.thread_id, user_request=request.message
        )
        state.add_message({"role": "user", "content": request.message})

        assert state.conversation_state == ConversationState.INITIAL
        assert state.diet_goal is None
        assert len(state.messages) == 1
        assert state.messages[0]["content"] == "vegetarian"

    @pytest.mark.asyncio
    async def test_handle_initial_state_with_diet(self):
        """Test that initial state handling works with diet goal."""
        request = ChatRequest(
            thread_id="test_thread", message="vegetarian", user_id="test_user"
        )

        # Create initial state
        state = AgentState(
            thread_id=request.thread_id, user_request=request.message
        )
        state.add_message({"role": "user", "content": request.message})

        # Test diet extraction
        diet_goal = self.agent._extract_diet_goal(request.message)
        assert diet_goal == "vegetarian"

        # Test initial state handling
        new_state = await self.agent._handle_initial_state(
            state, request.message
        )

        assert new_state.diet_goal == "vegetarian"
        assert (
            new_state.conversation_state == ConversationState.WAITING_FOR_DAYS
        )
        assert len(new_state.messages) == 2
        assert (
            "Great! I see you're interested in vegetarian meals"
            in new_state.messages[1]["content"]
        )

    @pytest.mark.asyncio
    async def test_handle_initial_state_without_diet(self):
        """Test that initial state handling works without diet goal."""
        request = ChatRequest(
            thread_id="test_thread", message="hello", user_id="test_user"
        )

        # Create initial state
        state = AgentState(
            thread_id=request.thread_id, user_request=request.message
        )
        state.add_message({"role": "user", "content": request.message})

        # Test diet extraction
        diet_goal = self.agent._extract_diet_goal(request.message)
        assert diet_goal is None

        # Test initial state handling
        new_state = await self.agent._handle_initial_state(
            state, request.message
        )

        assert new_state.diet_goal is None
        assert (
            new_state.conversation_state == ConversationState.WAITING_FOR_DIET
        )
        assert len(new_state.messages) == 2
        assert (
            "I'd be happy to help you plan your meals!"
            in new_state.messages[1]["content"]
        )

    @pytest.mark.asyncio
    async def test_planner_node_initial_state(self):
        """Test that planner node handles initial state correctly."""
        request = ChatRequest(
            thread_id="test_thread", message="vegetarian", user_id="test_user"
        )

        # Create initial state
        state = AgentState(
            thread_id=request.thread_id, user_request=request.message
        )
        state.add_message({"role": "user", "content": request.message})

        # Test planner node
        new_state = await self.agent._planner_node(state)

        assert new_state.diet_goal == "vegetarian"
        assert (
            new_state.conversation_state == ConversationState.WAITING_FOR_DAYS
        )
        assert len(new_state.messages) == 2

    @pytest.mark.asyncio
    async def test_full_process_request(self):
        """Test the full process_request method."""
        request = ChatRequest(
            thread_id="test_thread", message="vegetarian", user_id="test_user"
        )

        # Test full process
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

        print(f"Full process response: {response.message}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
