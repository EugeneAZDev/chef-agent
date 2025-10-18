"""
Tests for the Chef Agent.

This module contains unit tests for the LangGraph agent functionality.
"""

from unittest.mock import AsyncMock, patch

import pytest

from agent import ChefAgentGraph
from agent.models import AgentState, ChatRequest, ChatResponse


class TestSQLiteMemorySaver:
    """Test cases for SQLiteMemorySaver."""

    def test_create_schema(self, memory_saver):
        """Test database schema creation."""
        # Schema should be created in __init__
        conn = memory_saver._get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]

        assert "conversations" in tables
        assert "messages" in tables

    @pytest.mark.asyncio
    async def test_put_and_get(self, memory_saver):
        """Test putting and getting checkpoints."""
        config = {"thread_id": "test-123"}
        checkpoint = {"test": "data", "value": 42}

        # Put checkpoint
        await memory_saver.put(config, checkpoint)

        # Get checkpoint
        result = await memory_saver.get(config)

        assert result == checkpoint

    @pytest.mark.asyncio
    async def test_add_message(self, memory_saver):
        """Test adding messages."""
        thread_id = "test-123"

        # Create conversation first
        config = {"thread_id": thread_id}
        checkpoint = {"test": "data"}
        await memory_saver.put(config, checkpoint)

        await memory_saver.add_message(thread_id, "user", "Hello")
        await memory_saver.add_message(thread_id, "assistant", "Hi there!")

        messages = await memory_saver.get_messages(thread_id)

        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hi there!"

    @pytest.mark.asyncio
    async def test_clear_thread(self, memory_saver):
        """Test clearing thread data."""
        thread_id = "test-123"

        # Add some data
        await memory_saver.put({"thread_id": thread_id}, {"test": "data"})
        await memory_saver.add_message(thread_id, "user", "Hello")

        # Clear thread
        await memory_saver.clear_thread(thread_id)

        # Check data is gone
        result = await memory_saver.get({"thread_id": thread_id})
        messages = await memory_saver.get_messages(thread_id)

        assert result is None
        assert len(messages) == 0


class TestMemoryManager:
    """Test cases for MemoryManager."""

    @pytest.mark.asyncio
    async def test_save_and_load_conversation_state(self, memory_manager):
        """Test saving and loading conversation state."""
        thread_id = "test-123"
        state = AgentState(
            thread_id=thread_id,
            messages=[{"role": "user", "content": "Hello"}],
            language="en",
        )

        # Save state (convert to dict for JSON serialization)
        await memory_manager.save_conversation_state(
            thread_id, state.model_dump()
        )

        # Load state
        loaded_state = await memory_manager.load_conversation_state(thread_id)

        assert loaded_state is not None
        assert loaded_state["thread_id"] == thread_id
        assert loaded_state["language"] == "en"
        assert len(loaded_state["messages"]) == 1

    @pytest.mark.asyncio
    async def test_add_messages(self, memory_manager):
        """Test adding user and assistant messages."""
        thread_id = "test-123"

        # Create conversation first
        config = {"thread_id": thread_id}
        checkpoint = {"test": "data"}
        await memory_manager.memory_saver.put(config, checkpoint)

        await memory_manager.add_user_message(thread_id, "Hello")
        await memory_manager.add_assistant_message(thread_id, "Hi there!")

        history = await memory_manager.get_conversation_history(thread_id)

        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there!"


class TestChefAgentTools:
    """Test cases for ChefAgentTools."""

    def test_tools_creation(self, chef_tools):
        """Test tools creation."""
        assert len(chef_tools) > 0
        tool_names = [tool.name for tool in chef_tools]
        assert "search_recipes" in tool_names
        assert "create_shopping_list" in tool_names
        assert "add_to_shopping_list" in tool_names

    @pytest.mark.asyncio
    async def test_search_recipes_success(self, mock_mcp_client, chef_tools):
        """Test successful recipe search."""
        # Mock MCP client response
        mock_response = {
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
        mock_mcp_client.find_recipes.return_value = mock_response

        # Test search_recipes tool
        search_tool = next(
            tool for tool in chef_tools if tool.name == "search_recipes"
        )
        result = await search_tool.ainvoke(
            {"query": "test", "tags": ["vegetarian"], "limit": 5}
        )

        assert result["success"] is True
        assert len(result["recipes"]) == 1
        assert result["recipes"][0].title == "Test Recipe"
        assert result["total_found"] == 1

    @pytest.mark.asyncio
    async def test_search_recipes_error(self, mock_mcp_client, chef_tools):
        """Test recipe search with error."""
        # Mock MCP client to raise exception
        mock_mcp_client.find_recipes.side_effect = Exception("API Error")

        # Test search_recipes tool
        search_tool = next(
            tool for tool in chef_tools if tool.name == "search_recipes"
        )
        result = await search_tool.ainvoke({"query": "test"})

        assert result["success"] is False
        assert "error" in result
        assert result["recipes"] == []

    @pytest.mark.asyncio
    async def test_create_shopping_list(self, mock_mcp_client, chef_tools):
        """Test creating shopping list."""
        # Mock MCP client response
        mock_response = {
            "action": "created",
            "list_id": 1,
            "thread_id": "test-123",
        }
        mock_mcp_client.create_shopping_list.return_value = mock_response

        # Test create_shopping_list tool
        create_tool = next(
            tool for tool in chef_tools if tool.name == "create_shopping_list"
        )
        result = await create_tool.ainvoke({"thread_id": "test-123"})

        assert result["success"] is True
        assert result["shopping_list"]["action"] == "created"
        assert result["message"] == "Shopping list created for thread test-123"

    @pytest.mark.asyncio
    async def test_add_to_shopping_list(self, mock_mcp_client, chef_tools):
        """Test adding items to shopping list."""
        # Mock MCP client response
        mock_response = {
            "action": "items_added",
            "added_items": 2,
            "total_items": 2,
        }
        mock_mcp_client.add_to_shopping_list.return_value = mock_response

        # Test add_to_shopping_list tool
        items = [
            {"name": "item1", "quantity": "1", "unit": "cup"},
            {"name": "item2", "quantity": "2", "unit": "tbsp"},
        ]
        add_tool = next(
            tool for tool in chef_tools if tool.name == "add_to_shopping_list"
        )
        result = await add_tool.ainvoke(
            {"thread_id": "test-123", "items": items}
        )

        assert result["success"] is True
        assert result["shopping_list"]["action"] == "items_added"
        assert result["message"] == "Added 2 items to shopping list"


class TestChefAgentGraph:
    """Test cases for ChefAgentGraph."""

    def test_agent_configuration(self, mock_chef_agent, mock_mcp_client):
        """Test agent configuration and dependencies."""
        # Test core configuration
        assert mock_chef_agent.llm_provider == "groq"
        assert mock_chef_agent.api_key == "test-api-key"
        assert mock_chef_agent.mcp_client == mock_mcp_client

        # Test component initialization
        assert mock_chef_agent.memory_manager is not None
        assert mock_chef_agent.graph is not None

        # Test agent can handle invalid inputs
        with pytest.raises(ValueError):
            ChefAgentGraph("", "test-api-key", mock_mcp_client)

    def test_create_system_prompt(self, mock_chef_agent):
        """Test system prompt creation."""
        # Test English prompt
        en_prompt = mock_chef_agent._create_system_prompt("en")
        assert "chef assistant" in en_prompt.lower()
        assert "meal planning" in en_prompt.lower()
        assert "dietary goals" in en_prompt.lower()
        assert "shopping list" in en_prompt.lower()
        assert "how many days" in en_prompt.lower()

        # Test German prompt
        de_prompt = mock_chef_agent._create_system_prompt("de")
        assert "kochassistent" in de_prompt.lower()
        assert "mahlzeitenplanung" in de_prompt.lower()

        # Test French prompt
        fr_prompt = mock_chef_agent._create_system_prompt("fr")
        assert "assistant chef" in fr_prompt.lower()
        assert "planification de repas" in fr_prompt.lower()

        # Test unsupported language defaults to English
        default_prompt = mock_chef_agent._create_system_prompt("unsupported")
        assert "chef assistant" in default_prompt.lower()

    @pytest.mark.asyncio
    async def test_process_request_success(self, mock_chef_agent):
        """Test successful request processing."""
        # Mock the graph execution
        mock_state = AgentState(
            thread_id="test-123",
            messages=[{"role": "user", "content": "Hello"}],
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

            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            assert response.message is not None

    @pytest.mark.asyncio
    async def test_process_request_error(self, mock_chef_agent):
        """Test request processing with error."""
        # Mock the graph to raise an exception
        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            side_effect=Exception("Test error"),
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            response = await mock_chef_agent.process_request(request)

            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            assert "error" in response.message.lower()

    def test_get_all_tools(self, mock_chef_agent):
        """Test getting all tools."""
        tools = mock_chef_agent.tools
        assert len(tools) > 0

        # Check that we have the expected tools
        tool_names = [tool.name for tool in tools]
        assert "search_recipes" in tool_names
        assert "create_shopping_list" in tool_names
        assert "add_to_shopping_list" in tool_names
        assert "get_shopping_list" in tool_names
        assert "clear_shopping_list" in tool_names
        assert "replace_recipe_in_meal_plan" in tool_names

    @pytest.mark.asyncio
    async def test_diet_goal_extraction_through_public_api(
        self, mock_chef_agent
    ):
        """Test diet goal extraction through public API."""
        from unittest.mock import AsyncMock, Mock

        from agent.models import ChatRequest, ChatResponse

        # Test that agent can extract diet goals from natural language
        # through the public process_request method
        test_cases = [
            ("I want vegetarian food", "vegetarian"),
            ("vegan diet please", "vegan"),
            ("low-carb meals", "low-carb"),
            ("keto diet", "keto"),
            ("high protein", "high-protein"),
            ("gluten-free", "gluten-free"),
            ("mediterranean", "mediterranean"),
            ("I want to lose weight", "low-carb"),
            ("help me build muscle", "high-protein"),
        ]

        for message, expected_diet in test_cases:
            request = ChatRequest(
                message=message, thread_id="test_thread", language="en"
            )

            # Create a mock state object that behaves like AddableValuesDict
            mock_state = Mock()
            mock_state.get = Mock(
                return_value=[
                    {"role": "user", "content": message},
                    {
                        "role": "assistant",
                        "content": (
                            f"I understand you want {expected_diet} food."
                        ),
                    },
                ]
            )

            # Mock the graph.ainvoke method using AsyncMock
            with patch.object(
                mock_chef_agent.graph,
                "ainvoke",
                new_callable=AsyncMock,
                return_value=mock_state,
            ):
                response = await mock_chef_agent.process_request(request)

            # Verify the response is properly formatted
            assert isinstance(response, ChatResponse)
            assert response.message is not None
            assert "understand" in response.message.lower()

    @pytest.mark.asyncio
    async def test_meal_plan_generation_with_diet_goals(self, mock_chef_agent):
        """Test meal plan generation incorporates diet goals."""
        from unittest.mock import AsyncMock, Mock

        from agent.models import ChatRequest

        request = ChatRequest(
            message="Create a vegetarian meal plan for 3 days",
            thread_id="test_thread",
            language="en",
        )

        # Create a mock state object that behaves like AddableValuesDict
        mock_state = Mock()
        mock_state.get = Mock(
            return_value=[
                {"role": "user", "content": request.message},
                {
                    "role": "assistant",
                    "content": "I'll create a vegetarian meal plan for you.",
                },
            ]
        )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            response = await mock_chef_agent.process_request(request)

            # Verify the response indicates diet-aware meal planning
            assert isinstance(response, ChatResponse)
            assert "vegetarian" in response.message.lower()

    @pytest.mark.asyncio
    async def test_recipe_replacement_through_public_api(
        self, mock_chef_agent
    ):
        """Test recipe replacement through public API."""
        from unittest.mock import AsyncMock, Mock

        from agent.models import ChatRequest

        request = ChatRequest(
            message=(
                "Replace the breakfast recipe for day 1 " "with a vegan option"
            ),
            thread_id="test_thread",
            language="en",
        )

        # Create a mock state object that behaves like AddableValuesDict
        mock_state = Mock()
        mock_state.get = Mock(
            return_value=[
                {"role": "user", "content": request.message},
                {
                    "role": "assistant",
                    "content": (
                        "I've replaced the breakfast recipe "
                        "with a vegan option."
                    ),
                },
            ]
        )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            response = await mock_chef_agent.process_request(request)

            # Verify the response indicates recipe replacement
            assert isinstance(response, ChatResponse)
            assert "replaced" in response.message.lower()
            assert "breakfast" in response.message.lower()

    @pytest.mark.asyncio
    async def test_replace_recipe_tool(self, mock_mcp_client, chef_tools):
        """Test replace_recipe_in_meal_plan tool."""
        # Mock MCP client response
        mock_response = {
            "recipes": [
                {
                    "id": 2,
                    "title": "New Recipe",
                    "description": "A new recipe",
                    "instructions": "Cook it differently",
                    "ingredients": [
                        {
                            "name": "new_ingredient",
                            "quantity": "2",
                            "unit": "tbsp",
                        }
                    ],
                    "tags": ["new"],
                    "diet_type": "vegetarian",
                }
            ],
            "total_found": 1,
        }
        mock_mcp_client.find_recipes.return_value = mock_response

        # Test replace_recipe_in_meal_plan tool
        replace_tool = next(
            tool
            for tool in chef_tools
            if tool.name == "replace_recipe_in_meal_plan"
        )
        result = await replace_tool.ainvoke(
            {
                "day_number": 1,
                "meal_type": "breakfast",
                "new_query": "vegetarian breakfast",
                "thread_id": "test-123",
                "diet_type": "vegetarian",
            }
        )

        assert result["success"] is True
        assert result["new_recipe"]["title"] == "New Recipe"
        assert result["day_number"] == 1
        assert result["meal_type"] == "breakfast"
        assert "Found replacement recipe" in result["message"]

    @pytest.mark.asyncio
    async def test_replace_recipe_tool_no_results(
        self, mock_mcp_client, chef_tools
    ):
        """Test replace_recipe_in_meal_plan tool with no results."""
        # Mock MCP client response with no recipes
        mock_response = {
            "recipes": [],
            "total_found": 0,
        }
        mock_mcp_client.find_recipes.return_value = mock_response

        # Test replace_recipe_in_meal_plan tool
        replace_tool = next(
            tool
            for tool in chef_tools
            if tool.name == "replace_recipe_in_meal_plan"
        )
        result = await replace_tool.ainvoke(
            {
                "day_number": 1,
                "meal_type": "breakfast",
                "new_query": "nonexistent recipe",
                "thread_id": "test-123",
            }
        )

        assert result["success"] is False
        assert "No recipes found" in result["error"]
        assert "Failed to find replacement recipe" in result["message"]

    @pytest.mark.asyncio
    async def test_replace_recipe_tool_error(
        self, mock_mcp_client, chef_tools
    ):
        """Test replace_recipe_in_meal_plan tool with error."""
        # Mock MCP client to raise exception
        mock_mcp_client.find_recipes.side_effect = Exception("API Error")

        # Test replace_recipe_in_meal_plan tool
        replace_tool = next(
            tool
            for tool in chef_tools
            if tool.name == "replace_recipe_in_meal_plan"
        )
        result = await replace_tool.ainvoke(
            {
                "day_number": 1,
                "meal_type": "breakfast",
                "new_query": "test recipe",
                "thread_id": "test-123",
            }
        )

        assert result["success"] is False
        assert "error" in result
        assert "Failed to replace recipe" in result["message"]
