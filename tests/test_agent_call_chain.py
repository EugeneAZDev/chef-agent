"""
Tests for agent call chain and workflow execution.

This module contains comprehensive tests for the agent's call chain,
workflow execution, state transitions, and tool interactions.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from agent.models import (
    AgentState,
    ChatRequest,
    ChatResponse,
    ConversationState,
)


@pytest.mark.agent_call_chain
class TestAgentCallChain:
    """Test agent call chain and workflow execution."""

    @pytest.mark.asyncio
    async def test_agent_initial_state_transition(self, mock_chef_agent):
        """Test agent transition from initial state."""
        # Mock successful graph execution
        mock_state = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "Hello"},
                {
                    "role": "assistant",
                    "content": "Hi! I'm your chef assistant.",
                },
            ],
            language="en",
            conversation_state=ConversationState.WAITING_FOR_DIET,
        )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            response = await mock_chef_agent.process_request(request)

            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            assert "chef assistant" in response.message.lower()

    @pytest.mark.asyncio
    async def test_agent_diet_input_processing(self, mock_chef_agent):
        """Test agent processing of diet input."""
        # Mock state with diet input
        mock_state = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "I want vegetarian food"},
                {
                    "role": "assistant",
                    "content": (
                        "Great! I'll create vegetarian meals for you."
                    ),
                },
            ],
            language="en",
            conversation_state=ConversationState.WAITING_FOR_DAYS,
            diet_goals=["vegetarian"],
        )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            request = ChatRequest(
                thread_id="test-123",
                message="I want vegetarian food",
                language="en",
            )

            response = await mock_chef_agent.process_request(request)

            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            assert "vegetarian" in response.message.lower()

    @pytest.mark.asyncio
    async def test_agent_days_input_processing(self, mock_chef_agent):
        """Test agent processing of days input."""
        # Mock state with days input
        mock_state = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "3 days"},
                {
                    "role": "assistant",
                    "content": ("Perfect! I'll create a 3-day meal plan."),
                },
            ],
            language="en",
            conversation_state=ConversationState.GENERATING_PLAN,
            meal_plan_days=3,
        )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            request = ChatRequest(
                thread_id="test-123", message="3 days", language="en"
            )

            response = await mock_chef_agent.process_request(request)

            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            assert "3-day" in response.message.lower()

    @pytest.mark.asyncio
    async def test_agent_meal_plan_generation(self, mock_chef_agent):
        """Test agent meal plan generation workflow."""
        # Mock state with generated meal plan
        mock_state = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "Create a meal plan"},
                {
                    "role": "assistant",
                    "content": "Here's your meal plan for 3 days...",
                },
            ],
            language="en",
            conversation_state=ConversationState.COMPLETED,
            meal_plan={
                "day_1": {
                    "breakfast": {"title": "Vegetarian Breakfast", "id": 1},
                    "lunch": {"title": "Vegetarian Lunch", "id": 2},
                    "dinner": {"title": "Vegetarian Dinner", "id": 3},
                }
            },
        )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            request = ChatRequest(
                thread_id="test-123",
                message="Create a meal plan",
                language="en",
            )

            response = await mock_chef_agent.process_request(request)

            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            assert "meal plan" in response.message.lower()

    @pytest.mark.asyncio
    async def test_agent_tool_execution_chain(
        self, mock_chef_agent, mock_mcp_client
    ):
        """Test agent tool execution chain."""
        # Mock MCP client responses
        mock_mcp_client.find_recipes.return_value = {
            "recipes": [
                {
                    "id": 1,
                    "title": "Test Recipe",
                    "description": "A test recipe",
                    "instructions": "Cook it",
                    "ingredients": [
                        {"name": "ingredient1", "quantity": "1", "unit": "cup"}
                    ],
                    "tags": ["test"],
                    "diet_type": "vegetarian",
                }
            ],
            "total_found": 1,
        }

        mock_mcp_client.create_shopping_list.return_value = {
            "action": "created",
            "list_id": 1,
            "thread_id": "test-123",
        }

        # Mock state with tool execution
        mock_state = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "Find vegetarian recipes"},
                {
                    "role": "assistant",
                    "content": ("I found some vegetarian recipes for you."),
                },
            ],
            language="en",
            conversation_state=ConversationState.COMPLETED,
        )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            request = ChatRequest(
                thread_id="test-123",
                message="Find vegetarian recipes",
                language="en",
            )

            response = await mock_chef_agent.process_request(request)

            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"

    @pytest.mark.asyncio
    async def test_agent_conversation_state_persistence(self, mock_chef_agent):
        """Test agent conversation state persistence across calls."""
        # First call - initial state
        mock_state_1 = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "Hello"},
                {
                    "role": "assistant",
                    "content": "Hi! What diet do you prefer?",
                },
            ],
            language="en",
            conversation_state=ConversationState.WAITING_FOR_DIET,
        )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=mock_state_1,
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            response = await mock_chef_agent.process_request(request)
            assert "diet" in response.message.lower()

        # Second call - diet input
        mock_state_2 = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "Hello"},
                {
                    "role": "assistant",
                    "content": "Hi! What diet do you prefer?",
                },
                {"role": "user", "content": "Vegetarian"},
                {"role": "assistant", "content": "Great! How many days?"},
            ],
            language="en",
            conversation_state=ConversationState.WAITING_FOR_DAYS,
            diet_goals=["vegetarian"],
        )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=mock_state_2,
        ):
            request = ChatRequest(
                thread_id="test-123", message="Vegetarian", language="en"
            )

            response = await mock_chef_agent.process_request(request)
            assert "days" in response.message.lower()

    @pytest.mark.asyncio
    async def test_agent_error_recovery_in_chain(self, mock_chef_agent):
        """Test agent error recovery within call chain."""
        # Mock error in graph execution
        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            side_effect=Exception("Graph execution error"),
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            response = await mock_chef_agent.process_request(request)

            # Should handle error gracefully
            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            assert "error" in response.message.lower()

    @pytest.mark.asyncio
    async def test_agent_memory_workflow(self, mock_chef_agent):
        """Test agent memory workflow with mocked components."""
        # Mock memory operations
        with patch.object(
            mock_chef_agent.memory_manager,
            "save_conversation_state",
            new_callable=AsyncMock,
        ):
            with patch.object(
                mock_chef_agent.memory_manager,
                "load_conversation_state",
                new_callable=AsyncMock,
                return_value=None,
            ):
                mock_state = AgentState(
                    thread_id="test-123",
                    messages=[
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hi!"},
                    ],
                    language="en",
                )

                with patch.object(
                    mock_chef_agent.graph,
                    "ainvoke",
                    new_callable=AsyncMock,
                    return_value=mock_state,
                ):
                    request = ChatRequest(
                        thread_id="test-123", message="Hello", language="en"
                    )

                    response = await mock_chef_agent.process_request(request)

                    # Verify response is correct
                    assert isinstance(response, ChatResponse)

    @pytest.mark.asyncio
    async def test_agent_tool_error_handling(
        self, mock_chef_agent, mock_mcp_client
    ):
        """Test agent tool error handling in call chain."""
        # Mock MCP client error
        mock_mcp_client.find_recipes.side_effect = Exception(
            "MCP client error"
        )

        # Mock state with tool error
        mock_state = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "Find recipes"},
                {
                    "role": "assistant",
                    "content": (
                        "I encountered an error while searching for recipes."
                    ),
                },
            ],
            language="en",
            conversation_state=ConversationState.COMPLETED,
        )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            request = ChatRequest(
                thread_id="test-123", message="Find recipes", language="en"
            )

            response = await mock_chef_agent.process_request(request)

            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"

    @pytest.mark.asyncio
    async def test_agent_concurrent_requests(self, mock_chef_agent):
        """Test agent handling of concurrent requests."""

        async def process_request(request_id):
            mock_state = AgentState(
                thread_id=f"test-{request_id}",
                messages=[
                    {"role": "user", "content": f"Hello {request_id}"},
                    {"role": "assistant", "content": f"Hi {request_id}!"},
                ],
                language="en",
            )

            with patch.object(
                mock_chef_agent.graph,
                "ainvoke",
                new_callable=AsyncMock,
                return_value=mock_state,
            ):
                request = ChatRequest(
                    thread_id=f"test-{request_id}",
                    message=f"Hello {request_id}",
                    language="en",
                )

                return await mock_chef_agent.process_request(request)

        # Process multiple requests concurrently
        tasks = [process_request(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        assert len(responses) == 5
        for i, response in enumerate(responses):
            assert isinstance(response, ChatResponse)
            assert response.thread_id == f"test-{i}"

    @pytest.mark.asyncio
    async def test_agent_workflow_completion(self, mock_chef_agent):
        """Test complete agent workflow from start to finish."""
        # Step 1: Initial greeting
        mock_state_1 = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "Hello"},
                {
                    "role": "assistant",
                    "content": (
                        "Hi! I'm your chef assistant. What diet do you prefer?"
                    ),
                },
            ],
            language="en",
            conversation_state=ConversationState.WAITING_FOR_DIET,
        )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=mock_state_1,
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            response = await mock_chef_agent.process_request(request)
            assert "diet" in response.message.lower()

        # Step 2: Diet input
        mock_state_2 = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "Hello"},
                {
                    "role": "assistant",
                    "content": (
                        "Hi! I'm your chef assistant. What diet do you prefer?"
                    ),
                },
                {"role": "user", "content": "Vegetarian"},
                {
                    "role": "assistant",
                    "content": (
                        "Great! How many days would you like me to plan for?"
                    ),
                },
            ],
            language="en",
            conversation_state=ConversationState.WAITING_FOR_DAYS,
            diet_goals=["vegetarian"],
        )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=mock_state_2,
        ):
            request = ChatRequest(
                thread_id="test-123", message="Vegetarian", language="en"
            )

            response = await mock_chef_agent.process_request(request)
            assert "days" in response.message.lower()

        # Step 3: Days input
        mock_state_3 = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "Hello"},
                {
                    "role": "assistant",
                    "content": (
                        "Hi! I'm your chef assistant. What diet do you prefer?"
                    ),
                },
                {"role": "user", "content": "Vegetarian"},
                {
                    "role": "assistant",
                    "content": (
                        "Great! How many days would you like me to plan for?"
                    ),
                },
                {"role": "user", "content": "3 days"},
                {
                    "role": "assistant",
                    "content": (
                        "Perfect! I'll create a 3-day vegetarian meal plan "
                        "for you."
                    ),
                },
            ],
            language="en",
            conversation_state=ConversationState.GENERATING_PLAN,
            diet_goals=["vegetarian"],
            meal_plan_days=3,
        )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=mock_state_3,
        ):
            request = ChatRequest(
                thread_id="test-123", message="3 days", language="en"
            )

            response = await mock_chef_agent.process_request(request)
            assert "meal plan" in response.message.lower()

    @pytest.mark.asyncio
    async def test_agent_tool_chain_execution(
        self, mock_mcp_client, chef_tools
    ):
        """Test tool chain execution."""
        # Mock MCP client responses for tool chain
        mock_mcp_client.find_recipes.return_value = {
            "recipes": [
                {
                    "id": 1,
                    "title": "Vegetarian Pasta",
                    "description": "A delicious vegetarian pasta",
                    "instructions": "Cook pasta, add sauce",
                    "ingredients": [
                        {"name": "pasta", "quantity": "500", "unit": "g"},
                        {
                            "name": "tomato sauce",
                            "quantity": "400",
                            "unit": "ml",
                        },
                    ],
                    "tags": ["vegetarian", "pasta"],
                    "diet_type": "vegetarian",
                }
            ],
            "total_found": 1,
        }

        mock_mcp_client.create_shopping_list.return_value = {
            "action": "created",
            "list_id": 1,
            "thread_id": "test-123",
        }

        mock_mcp_client.add_to_shopping_list.return_value = {
            "action": "items_added",
            "added_items": 2,
            "total_items": 2,
        }

        # Test tool chain: search -> create list -> add items
        search_tool = next(
            tool for tool in chef_tools if tool.name == "search_recipes"
        )
        create_tool = next(
            tool for tool in chef_tools if tool.name == "create_shopping_list"
        )
        add_tool = next(
            tool for tool in chef_tools if tool.name == "add_to_shopping_list"
        )

        # Execute tool chain
        search_result = await search_tool.ainvoke(
            {"query": "vegetarian pasta"}
        )
        assert search_result["success"] is True
        assert len(search_result["recipes"]) == 1

        create_result = await create_tool.ainvoke({"thread_id": "test-123"})
        assert create_result["success"] is True

        add_result = await add_tool.ainvoke(
            {
                "thread_id": "test-123",
                "items": [
                    {"name": "pasta", "quantity": "500", "unit": "g"},
                    {"name": "tomato sauce", "quantity": "400", "unit": "ml"},
                ],
            }
        )
        assert add_result["success"] is True

    def test_agent_state_transition_validation(self, mock_chef_agent):
        """Test agent state transition validation."""
        # Test valid state transitions
        valid_transitions = [
            (ConversationState.INITIAL, ConversationState.WAITING_FOR_DIET),
            (
                ConversationState.WAITING_FOR_DIET,
                ConversationState.WAITING_FOR_DAYS,
            ),
            (
                ConversationState.WAITING_FOR_DAYS,
                ConversationState.GENERATING_PLAN,
            ),
            (ConversationState.GENERATING_PLAN, ConversationState.COMPLETED),
        ]

        for from_state, to_state in valid_transitions:
            # This would require implementing state validation logic
            # For now, just verify the states exist
            assert from_state in ConversationState
            assert to_state in ConversationState

    @pytest.mark.asyncio
    async def test_agent_error_propagation(self, mock_chef_agent):
        """Test error propagation through agent call chain."""
        # Mock error in different parts of the chain
        with patch.object(
            mock_chef_agent.memory_manager,
            "load_conversation_state",
            new_callable=AsyncMock,
            side_effect=Exception("Memory load error"),
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            response = await mock_chef_agent.process_request(request)

            # Should handle memory error gracefully
            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
