"""
Test agent state after each node.
"""

import asyncio

import pytest

from adapters.mcp.http_client import ChefAgentHTTPMCPClient
from agent.graph import ChefAgentGraph
from agent.models import AgentState, ChatRequest, ConversationState
from config import settings


class TestAgentStateFlow:
    """Test agent state flow through nodes."""

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

    @pytest.mark.asyncio
    async def test_state_after_planner_node(self):
        """Test state after planner node."""
        request = ChatRequest(
            thread_id="test_thread", message="vegetarian", user_id="test_user"
        )

        # Create initial state
        initial_state = AgentState(
            thread_id=request.thread_id,
            messages=[{"role": "user", "content": request.message}],
            language=request.language,
        )

        # Test planner node
        state_after_planner = await self.agent._planner_node(initial_state)

        print(f"State after planner: {state_after_planner.conversation_state}")
        print(f"Diet goal: {state_after_planner.diet_goal}")
        print(f"Messages count: {len(state_after_planner.messages)}")
        print(f"Last message: {state_after_planner.messages[-1]['content']}")

        assert state_after_planner.diet_goal == "vegetarian"
        assert (
            state_after_planner.conversation_state
            == ConversationState.WAITING_FOR_DAYS
        )
        assert len(state_after_planner.messages) == 2

    @pytest.mark.asyncio
    async def test_state_after_tools_node(self):
        """Test state after tools node."""
        request = ChatRequest(
            thread_id="test_thread", message="vegetarian", user_id="test_user"
        )

        # Create initial state
        initial_state = AgentState(
            thread_id=request.thread_id,
            messages=[{"role": "user", "content": request.message}],
            language=request.language,
        )

        # Test planner node
        state_after_planner = await self.agent._planner_node(initial_state)

        # Test tools node
        state_after_tools = await self.agent._tools_node(state_after_planner)

        print(f"State after tools: {state_after_tools.conversation_state}")
        print(f"Tool calls: {len(state_after_tools.tool_calls)}")
        print(f"Tool results: {len(state_after_tools.tool_results)}")

        # Tools node should not change conversation state
        assert (
            state_after_tools.conversation_state
            == ConversationState.WAITING_FOR_DAYS
        )

    @pytest.mark.asyncio
    async def test_state_after_responder_node(self):
        """Test state after responder node."""
        request = ChatRequest(
            thread_id="test_thread", message="vegetarian", user_id="test_user"
        )

        # Create initial state
        initial_state = AgentState(
            thread_id=request.thread_id,
            messages=[{"role": "user", "content": request.message}],
            language=request.language,
        )

        # Test planner node
        state_after_planner = await self.agent._planner_node(initial_state)

        # Test tools node
        state_after_tools = await self.agent._tools_node(state_after_planner)

        # Test responder node
        state_after_responder = await self.agent._responder_node(
            state_after_tools
        )

        print(
            f"State after responder: {state_after_responder.conversation_state}"
        )
        print(f"Messages count: {len(state_after_responder.messages)}")
        print(f"Last message: {state_after_responder.messages[-1]['content']}")

        # Should have 3 messages now (user + planner + responder)
        assert len(state_after_responder.messages) == 3

        # Last message should not be generic
        last_message = state_after_responder.messages[-1]["content"]
        generic_message = (
            "I'm here to help you plan your meals! Please tell me about "
            "your dietary goals"
        )
        assert (
            generic_message not in last_message
        ), f"Responder returned generic message: {last_message}"

    @pytest.mark.asyncio
    async def test_full_graph_execution(self):
        """Test full graph execution."""
        request = ChatRequest(
            thread_id="test_thread", message="vegetarian", user_id="test_user"
        )

        # Create initial state
        initial_state = AgentState(
            thread_id=request.thread_id,
            messages=[{"role": "user", "content": request.message}],
            language=request.language,
        )

        # Test full graph execution
        config = {
            "thread_id": request.thread_id,
            "recursion_limit": 10,
        }

        final_state = await self.agent.graph.ainvoke(
            initial_state, config=config
        )

        print(f"Final state type: {type(final_state)}")
        print(f"Final state: {final_state}")

        # Extract messages
        if final_state is None:
            messages = []
        elif hasattr(final_state, "get"):
            messages = final_state.get("messages", [])
        else:
            messages = getattr(final_state, "messages", [])

        print(f"Final messages count: {len(messages)}")
        if messages:
            print(f"Last message: {messages[-1]['content']}")

        # Should have at least 2 messages (user + response)
        assert len(messages) >= 2

        # Last message should not be generic
        last_message = messages[-1]["content"]
        generic_message = (
            "I'm here to help you plan your meals! Please tell me about "
            "your dietary goals"
        )
        assert (
            generic_message not in last_message
        ), f"Graph returned generic message: {last_message}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
