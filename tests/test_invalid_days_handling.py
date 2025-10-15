"""
Test cases for invalid days input handling in agent conversation flow.
"""

from unittest.mock import AsyncMock

import pytest

from adapters.mcp.client import ChefAgentMCPClient
from agent import ChefAgentGraph
from agent.models import AgentState, ConversationState


class TestInvalidDaysInputHandling:
    """Test cases for handling invalid days input scenarios."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for testing."""
        return AsyncMock(spec=ChefAgentMCPClient)

    @pytest.fixture
    def chef_agent(self, mock_mcp_client):
        """Create ChefAgentGraph instance for testing."""
        return ChefAgentGraph(
            llm_provider="groq",
            api_key="test-key",
            mcp_client=mock_mcp_client,
            model="llama-3.1-8b-instant",
        )

    @pytest.mark.asyncio
    async def test_invalid_days_too_few(self, chef_agent):
        """Test handling of too few days (e.g., 2 days)."""
        # Create initial state waiting for days input
        initial_state = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "I want a vegetarian meal plan"},
                {
                    "role": "assistant",
                    "content": (
                        "Great! I can help you create a vegetarian meal plan. "
                        "How many days would you like me to plan for? "
                        "(between 3 and 7 days)"
                    ),
                },
            ],
            diet_goal="vegetarian",
            conversation_state=ConversationState.WAITING_FOR_DAYS,
            language="en",
        )

        # Test with "2 days" input
        result_state = await chef_agent._handle_days_input(
            initial_state, "2 days"
        )

        # Verify state remains in WAITING_FOR_DAYS
        assert result_state.conversation_state == (
            ConversationState.WAITING_FOR_DAYS
        )
        assert result_state.days_count is None  # Should not be set

        # Verify error message was added
        assert len(result_state.messages) == 3
        error_message = result_state.messages[-1]["content"]
        assert "I didn't catch" in error_message
        assert "between 3 and 7 days" in error_message
        assert "Please specify" in error_message

    @pytest.mark.asyncio
    async def test_invalid_days_too_many(self, chef_agent):
        """Test handling of too many days (e.g., 10 days)."""
        # Create initial state waiting for days input
        initial_state = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "I want a vegetarian meal plan"},
                {
                    "role": "assistant",
                    "content": (
                        "Great! I can help you create a vegetarian meal plan. "
                        "How many days would you like me to plan for? "
                        "(between 3 and 7 days)"
                    ),
                },
            ],
            diet_goal="vegetarian",
            conversation_state=ConversationState.WAITING_FOR_DAYS,
            language="en",
        )

        # Test with "10 days" input
        result_state = await chef_agent._handle_days_input(
            initial_state, "10 days"
        )

        # Verify state remains in WAITING_FOR_DAYS
        assert result_state.conversation_state == (
            ConversationState.WAITING_FOR_DAYS
        )
        assert result_state.days_count is None  # Should not be set

        # Verify error message was added
        assert len(result_state.messages) == 3
        error_message = result_state.messages[-1]["content"]
        assert "10 days" in error_message
        assert "3 to 7 days" in error_message
        assert "Please choose" in error_message

    @pytest.mark.asyncio
    async def test_invalid_days_no_number(self, chef_agent):
        """Test handling when no number is provided."""
        # Create initial state waiting for days input
        initial_state = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "I want a vegetarian meal plan"},
                {
                    "role": "assistant",
                    "content": (
                        "Great! I can help you create a vegetarian meal plan. "
                        "How many days would you like me to plan for? "
                        "(between 3 and 7 days)"
                    ),
                },
            ],
            diet_goal="vegetarian",
            conversation_state=ConversationState.WAITING_FOR_DAYS,
            language="en",
        )

        # Test with no number input
        result_state = await chef_agent._handle_days_input(
            initial_state, "I don't know"
        )

        # Verify state remains in WAITING_FOR_DAYS
        assert result_state.conversation_state == (
            ConversationState.WAITING_FOR_DAYS
        )
        assert result_state.days_count is None  # Should not be set

        # Verify error message was added
        assert len(result_state.messages) == 3
        error_message = result_state.messages[-1]["content"]
        assert "didn't catch the number" in error_message
        assert "between 3 and 7 days" in error_message

    @pytest.mark.asyncio
    async def test_valid_days_input(self, chef_agent):
        """Test handling of valid days input."""
        # Create initial state waiting for days input
        initial_state = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "I want a vegetarian meal plan"},
                {
                    "role": "assistant",
                    "content": (
                        "Great! I can help you create a vegetarian meal plan. "
                        "How many days would you like me to plan for? "
                        "(between 3 and 7 days)"
                    ),
                },
            ],
            diet_goal="vegetarian",
            conversation_state=ConversationState.WAITING_FOR_DAYS,
            language="en",
        )

        # Test with valid input "5 days"
        result_state = await chef_agent._handle_days_input(
            initial_state, "5 days"
        )

        # Verify state transitions to GENERATING_PLAN
        assert result_state.conversation_state == (
            ConversationState.GENERATING_PLAN
        )
        assert result_state.days_count == 5

        # Verify success message was added
        assert len(result_state.messages) == 3
        success_message = result_state.messages[-1]["content"]
        assert "5-day" in success_message
        assert "vegetarian meal plan" in success_message

        # Verify tool call was added for recipe search
        assert len(result_state.tool_calls) == 1
        assert result_state.tool_calls[0]["name"] == "search_recipes"

    @pytest.mark.asyncio
    async def test_retry_after_invalid_input(self, chef_agent):
        """Test that user can retry after invalid input."""
        # Create state after invalid input
        state_after_invalid = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "I want a vegetarian meal plan"},
                {
                    "role": "assistant",
                    "content": (
                        "Great! I can help you create a vegetarian meal plan. "
                        "How many days would you like me to plan for? "
                        "(between 3 and 7 days)"
                    ),
                },
                {"role": "user", "content": "2 days"},
                {
                    "role": "assistant",
                    "content": (
                        "I see you mentioned 2 days, but I can only plan for "
                        "3 "
                        "to 7 days. Please choose a number between 3 and 7 "
                        "days."
                    ),
                },
            ],
            diet_goal="vegetarian",
            conversation_state=ConversationState.WAITING_FOR_DAYS,
            language="en",
        )

        # Test retry with valid input
        result_state = await chef_agent._handle_days_input(
            state_after_invalid, "4 days"
        )

        # Verify state transitions to GENERATING_PLAN
        assert result_state.conversation_state == (
            ConversationState.GENERATING_PLAN
        )
        assert result_state.days_count == 4

        # Verify success message was added
        assert len(result_state.messages) == 5
        success_message = result_state.messages[-1]["content"]
        assert "4-day" in success_message
        assert "vegetarian meal plan" in success_message

    def test_extract_days_count_edge_cases(self, chef_agent):
        """Test _extract_days_count method with edge cases."""
        # Test valid numbers
        assert chef_agent._extract_days_count("3 days") == (3, True)
        assert chef_agent._extract_days_count("7 days") == (7, True)
        assert chef_agent._extract_days_count("I want 5 days") == (5, True)

        # Test invalid numbers - our new logic skips numbers < 3
        assert chef_agent._extract_days_count("2 days") == (None, False)
        assert chef_agent._extract_days_count("10 days") == (10, False)
        assert chef_agent._extract_days_count("1 day") == (None, False)
        assert chef_agent._extract_days_count("8 days") == (8, False)

        # Test no numbers
        assert chef_agent._extract_days_count("I don't know") == (None, False)
        assert chef_agent._extract_days_count("") == (None, False)
        assert chef_agent._extract_days_count("some text") == (None, False)

        # Test multiple numbers (should return first valid one)
        assert chef_agent._extract_days_count("2 and 5 days") == (5, True)
        assert chef_agent._extract_days_count("5 and 2 days") == (5, True)


class TestFallbackHandling:
    """Test cases for fallback recipe handling in agent."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for testing."""
        return AsyncMock(spec=ChefAgentMCPClient)

    @pytest.fixture
    def chef_agent(self, mock_mcp_client):
        """Create ChefAgentGraph instance for testing."""
        return ChefAgentGraph(
            llm_provider="groq",
            api_key="test-key",
            mcp_client=mock_mcp_client,
            model="llama-3.1-8b-instant",
        )

    @pytest.mark.asyncio
    async def test_fallback_notification_in_response(self, chef_agent):
        """Test that fallback notification is included in response."""
        from agent.models import AgentState, ConversationState
        from domain.entities import (
            DietType,
            Ingredient,
            Meal,
            MealPlan,
            MenuDay,
            Recipe,
        )

        # Create a meal plan with fallback used
        recipe = Recipe(
            id=1,
            title="Chicken Salad",
            ingredients=[
                Ingredient(name="chicken", quantity="200", unit="g"),
                Ingredient(name="lettuce", quantity="1", unit="head"),
            ],
            instructions="Mix chicken with lettuce",
            diet_type=DietType.HIGH_PROTEIN,
        )

        meal = Meal(name="lunch", recipe=recipe)
        menu_day = MenuDay(day_number=1)
        menu_day.add_meal(meal)

        meal_plan = MealPlan(days=[menu_day], diet_type=DietType.HIGH_PROTEIN)
        meal_plan.total_days = 3

        # Create state with fallback used
        state = AgentState(
            thread_id="test-123",
            messages=[],
            diet_goal="vegan",
            days_count=3,
            conversation_state=ConversationState.COMPLETED,
            menu_plan=meal_plan,
            fallback_used=True,
            language="en",
        )

        # Generate response
        response = chef_agent._generate_meal_plan_response(state)

        # Verify fallback notification is included
        assert "Note:" in response
        assert "couldn't find enough recipes specifically" in response
        assert "vegan diet" in response
        assert "general collection" in response
        assert "modify them to better fit" in response

    @pytest.mark.asyncio
    async def test_no_fallback_notification_when_not_used(self, chef_agent):
        """Test that no fallback notification when fallback not used."""
        from agent.models import AgentState, ConversationState
        from domain.entities import (
            DietType,
            Ingredient,
            Meal,
            MealPlan,
            MenuDay,
            Recipe,
        )

        # Create a meal plan without fallback
        recipe = Recipe(
            id=1,
            title="Vegan Salad",
            ingredients=[
                Ingredient(name="lettuce", quantity="1", unit="head"),
                Ingredient(name="tomato", quantity="2", unit="pieces"),
            ],
            instructions="Mix vegetables",
            diet_type=DietType.VEGAN,
        )

        meal = Meal(name="lunch", recipe=recipe)
        menu_day = MenuDay(day_number=1)
        menu_day.add_meal(meal)

        meal_plan = MealPlan(days=[menu_day], diet_type=DietType.VEGAN)
        meal_plan.total_days = 3

        # Create state without fallback
        state = AgentState(
            thread_id="test-123",
            messages=[],
            diet_goal="vegan",
            days_count=3,
            conversation_state=ConversationState.COMPLETED,
            menu_plan=meal_plan,
            fallback_used=False,
            language="en",
        )

        # Generate response
        response = chef_agent._generate_meal_plan_response(state)

        # Verify no fallback notification
        assert "Note:" not in response
        assert "couldn't find enough recipes" not in response
        assert "general collection" not in response


class TestEmptyRecipesHandling:
    """Test cases for handling empty recipe lists in agent."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for testing."""
        return AsyncMock(spec=ChefAgentMCPClient)

    @pytest.fixture
    def chef_agent(self, mock_mcp_client):
        """Create ChefAgentGraph instance for testing."""
        return ChefAgentGraph(
            llm_provider="groq",
            api_key="test-key",
            mcp_client=mock_mcp_client,
            model="llama-3.1-8b-instant",
        )

    @pytest.mark.asyncio
    async def test_empty_recipes_first_attempt(self, chef_agent):
        """Test handling of empty recipes on first attempt."""
        from agent.models import AgentState, ConversationState

        # Create state with empty recipes
        state = AgentState(
            thread_id="test-123",
            messages=[],
            diet_goal="vegan",
            days_count=3,
            conversation_state=ConversationState.GENERATING_PLAN,
            found_recipes=[],  # Empty recipes
            recipe_search_attempts=0,
            language="en",
        )

        # Handle plan generation
        result_state = await chef_agent._handle_plan_generation(state)

        # Should try broader search
        assert result_state.recipe_search_attempts == 1
        assert result_state.conversation_state == (
            ConversationState.GENERATING_PLAN
        )
        assert len(result_state.tool_calls) == 1
        assert result_state.tool_calls[0]["name"] == "search_recipes"
        assert result_state.tool_calls[0]["args"]["limit"] == 50

        # Should have error message
        assert len(result_state.messages) == 1
        error_message = result_state.messages[0]["content"]
        assert "couldn't find enough recipes" in error_message
        assert "broader search" in error_message

    @pytest.mark.asyncio
    async def test_empty_recipes_second_attempt(self, chef_agent):
        """Test handling of empty recipes on second attempt."""
        from agent.models import AgentState, ConversationState

        # Create state with empty recipes after first attempt
        state = AgentState(
            thread_id="test-123",
            messages=[],
            diet_goal="vegan",
            days_count=3,
            conversation_state=ConversationState.GENERATING_PLAN,
            found_recipes=[],  # Still empty
            recipe_search_attempts=1,  # Second attempt
            language="en",
        )

        # Handle plan generation
        result_state = await chef_agent._handle_plan_generation(state)

        # Should give up and complete conversation
        assert result_state.recipe_search_attempts == 2
        assert result_state.conversation_state == ConversationState.COMPLETED
        assert result_state.error == (
            "No recipes found after multiple search attempts"
        )
        assert len(result_state.tool_calls) == 0  # No more tool calls

        # Should have final error message
        assert len(result_state.messages) == 1
        error_message = result_state.messages[0]["content"]
        assert "I'm sorry" in error_message
        assert "couldn't find any recipes" in error_message
        assert "vegan meal plan" in error_message
        assert "try a different diet goal" in error_message

    @pytest.mark.asyncio
    async def test_successful_recipes_found(self, chef_agent):
        """Test successful plan generation when recipes are found."""
        from agent.models import AgentState, ConversationState
        from domain.entities import DietType, Ingredient, Recipe

        # Create state with recipes found
        recipes = [
            Recipe(
                id=1,
                title="Vegan Salad",
                ingredients=[
                    Ingredient(name="lettuce", quantity="1", unit="head"),
                ],
                instructions="Mix vegetables",
                diet_type=DietType.VEGAN,
            )
        ]

        state = AgentState(
            thread_id="test-123",
            messages=[],
            diet_goal="vegan",
            days_count=3,
            conversation_state=ConversationState.GENERATING_PLAN,
            found_recipes=recipes,
            recipe_search_attempts=0,
            language="en",
        )

        # Handle plan generation
        result_state = await chef_agent._handle_plan_generation(state)

        # Should complete successfully
        assert result_state.conversation_state == ConversationState.COMPLETED
        assert result_state.menu_plan is not None
        assert result_state.recipe_search_attempts == 0  # Not incremented
        assert len(result_state.tool_calls) == 1
        assert result_state.tool_calls[0]["name"] == "create_shopping_list"


class TestRecipeReplacementErrorHandling:
    """Test cases for handling recipe replacement errors in agent."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for testing."""
        return AsyncMock(spec=ChefAgentMCPClient)

    @pytest.fixture
    def chef_agent(self, mock_mcp_client):
        """Create ChefAgentGraph instance for testing."""
        return ChefAgentGraph(
            llm_provider="groq",
            api_key="test-key",
            mcp_client=mock_mcp_client,
            model="llama-3.1-8b-instant",
        )

    @pytest.mark.asyncio
    async def test_recipe_replacement_retry_state(self, chef_agent):
        """Test that agent enters retry state when recipe not found."""
        from agent.models import AgentState, ConversationState

        # Create state with recipe replacement context
        state = AgentState(
            thread_id="test-123",
            messages=[],
            diet_goal="vegan",
            days_count=3,
            conversation_state=(
                ConversationState.WAITING_FOR_RECIPE_REPLACEMENT
            ),
            recipe_replacement_context={
                "day_number": 1,
                "meal_type": "lunch",
                "diet_type": "vegan",
            },
            language="en",
        )

        # Handle recipe replacement input
        result_state = await chef_agent._handle_recipe_replacement_input(
            state, "vegan pasta"
        )

        # Should set up tool call for replacement
        assert len(result_state.tool_calls) == 1
        assert result_state.tool_calls[0]["name"] == (
            "replace_recipe_in_meal_plan"
        )
        assert result_state.tool_calls[0]["args"]["new_query"] == "vegan pasta"
        assert result_state.tool_calls[0]["args"]["day_number"] == 1
        assert result_state.tool_calls[0]["args"]["meal_type"] == "lunch"

    @pytest.mark.asyncio
    async def test_recipe_replacement_missing_context(self, chef_agent):
        """Test handling when recipe replacement context is missing."""
        from agent.models import AgentState, ConversationState

        # Create state without recipe replacement context
        state = AgentState(
            thread_id="test-123",
            messages=[],
            diet_goal="vegan",
            days_count=3,
            conversation_state=(
                ConversationState.WAITING_FOR_RECIPE_REPLACEMENT
            ),
            recipe_replacement_context=None,
            language="en",
        )

        # Handle recipe replacement input
        result_state = await chef_agent._handle_recipe_replacement_input(
            state, "vegan pasta"
        )

        # Should set error
        assert result_state.error == "Missing recipe replacement context"

    @pytest.mark.asyncio
    async def test_recipe_replacement_error_processing(self, chef_agent):
        """Test processing of recipe replacement error results."""
        from agent.models import AgentState, ConversationState

        # Create state
        state = AgentState(
            thread_id="test-123",
            messages=[],
            diet_goal="vegan",
            days_count=3,
            conversation_state=ConversationState.COMPLETED,
            language="en",
        )

        # Mock tool result with recipe not found error
        tool_result = {
            "success": False,
            "error": "No recipes found for query: nonexistent recipe",
            "error_type": "recipe_not_found",
            "day_number": 2,
            "meal_type": "dinner",
            "diet_type": "vegan",
            "query": "nonexistent recipe",
            "suggestions": [
                "Try a different search term",
                "Use more general keywords",
            ],
        }

        state.tool_results = [tool_result]

        # Process tool results
        response = await chef_agent._process_tool_results(state)

        # Should set up retry context and state
        assert (
            state.conversation_state
            == ConversationState.WAITING_FOR_RECIPE_REPLACEMENT
        )
        assert state.recipe_replacement_context is not None
        assert state.recipe_replacement_context["day_number"] == 2
        assert state.recipe_replacement_context["meal_type"] == "dinner"

        # Should include helpful message
        assert "couldn't find a recipe" in response
        assert "dinner recipe on day 2" in response
        assert "Suggestions:" in response
        assert "Try a different search term" in response

    @pytest.mark.asyncio
    async def test_recipe_replacement_success_processing(self, chef_agent):
        """Test processing of successful recipe replacement."""
        from agent.models import AgentState, ConversationState
        from domain.entities import DietType, Ingredient, Recipe

        # Create state with meal plan
        state = AgentState(
            thread_id="test-123",
            messages=[],
            diet_goal="vegan",
            days_count=3,
            conversation_state=ConversationState.COMPLETED,
            language="en",
        )

        # Mock successful tool result
        new_recipe = Recipe(
            id=1,
            title="Vegan Pasta",
            ingredients=[
                Ingredient(name="pasta", quantity="200", unit="g"),
            ],
            instructions="Cook pasta",
            diet_type=DietType.VEGAN,
        )

        tool_result = {
            "success": True,
            "new_recipe": new_recipe,
            "day_number": 1,
            "meal_type": "lunch",
            "message": "Found replacement recipe: Vegan Pasta",
        }

        state.tool_results = [tool_result]

        # Process tool results
        response = await chef_agent._process_tool_results(state)

        # Should include success message
        assert "replaced the lunch recipe for day 1" in response
        assert "Vegan Pasta" in response
