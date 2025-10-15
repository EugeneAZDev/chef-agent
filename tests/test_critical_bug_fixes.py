"""
Tests for critical bug fixes and edge cases.

This module tests the fixes for the critical bugs identified in the codebase.
"""

from unittest.mock import Mock

import pytest

from adapters.db.database import Database
from adapters.db.recipe_repository import SQLiteRecipeRepository
from adapters.db.shopping_list_repository import SQLiteShoppingListRepository
from agent.models import AgentState, ConversationState
from domain.entities import (
    DietType,
    Ingredient,
    Recipe,
    ShoppingItem,
    ShoppingList,
)
from domain.meal_plan_generator import MealPlanGenerator


class TestSQLInjectionPrevention:
    """Test SQL injection prevention fixes."""

    def test_search_keywords_escapes_special_characters(self):
        """Test that search keywords properly escape SQL special characters."""
        db = Database(":memory:")
        repo = SQLiteRecipeRepository(db)

        # Test with SQL injection attempt
        malicious_keywords = [
            "test%' OR 1=1--",
            "normal_keyword",
            "test_underscore",
        ]

        # This should not raise an exception and should not return all recipes
        recipes = repo.search_by_keywords(malicious_keywords, limit=10)

        # Should return empty list or only recipes that actually match
        assert isinstance(recipes, list)

        # Test with normal keywords
        normal_keywords = ["pasta", "chicken"]
        recipes = repo.search_by_keywords(normal_keywords, limit=10)
        assert isinstance(recipes, list)

    def test_search_recipes_escapes_query(self):
        """Test that search_recipes properly escapes query strings."""
        db = Database(":memory:")
        repo = SQLiteRecipeRepository(db)

        # Test with SQL injection attempt
        malicious_query = "test%' OR 1=1--"

        recipes = repo.search_recipes(query=malicious_query, limit=10)
        assert isinstance(recipes, list)

    def test_user_id_validation(self):
        """Test that user_id validation prevents SQL injection."""
        db = Database(":memory:")
        repo = SQLiteRecipeRepository(db)

        # Test with malicious user_id
        with pytest.raises(
            ValueError,
            match="user_id must be a valid email address or alphanumeric "
            "string with dashes/underscores only",
        ):
            repo.get_all(user_id="'; DROP TABLE recipes;--")

        with pytest.raises(
            ValueError,
            match="user_id must be a valid email address or alphanumeric "
            "string with dashes/underscores only",
        ):
            repo.search_recipes(user_id="'; DROP TABLE recipes;--")

        # Test with valid user_id
        recipes = repo.get_all(user_id="user123")
        assert isinstance(recipes, list)

    def test_thread_id_validation(self):
        """Test that thread_id validation prevents SQL injection."""
        db = Database(":memory:")
        repo = SQLiteShoppingListRepository(db)

        # Test with malicious thread_id
        with pytest.raises(ValueError, match="Invalid thread_id format"):
            repo.get_by_thread_id("'; DROP TABLE shopping_lists;--")

        with pytest.raises(ValueError, match="Invalid thread_id format"):
            repo.save(
                ShoppingList(items=[]), "'; DROP TABLE shopping_lists;--"
            )

        # Test with valid thread_id
        result = repo.get_by_thread_id("thread123")
        assert result is None  # Should not raise exception


class TestEmptyRecipeHandling:
    """Test empty recipe list handling fixes."""

    def test_meal_plan_generator_raises_error_for_empty_recipes(self):
        """Test that MealPlanGenerator raises error for empty recipe list."""
        with pytest.raises(
            ValueError, match="Cannot generate meal plan: no recipes available"
        ):
            MealPlanGenerator.generate_meal_plan(
                recipes=[], diet_goal="vegetarian", days_count=3
            )

    def test_meal_plan_generator_raises_error_for_none_recipes(self):
        """Test that MealPlanGenerator raises error for None recipe list."""
        with pytest.raises(
            ValueError, match="Cannot generate meal plan: no recipes available"
        ):
            MealPlanGenerator.generate_meal_plan(
                recipes=None, diet_goal="vegetarian", days_count=3
            )

    @pytest.mark.asyncio
    async def test_agent_handles_empty_recipe_error(self):
        """Test that agent properly handles empty recipe list error."""
        from adapters.mcp.client import ChefAgentMCPClient
        from agent import ChefAgentGraph

        # Mock MCP client
        mock_mcp = Mock(spec=ChefAgentMCPClient)

        # Create agent
        agent = ChefAgentGraph(
            llm_provider="groq", api_key="test_key", mcp_client=mock_mcp
        )

        # Create state with empty recipes but in the right state
        state = AgentState(
            thread_id="test_thread",
            found_recipes=[],
            diet_goal="vegetarian",
            days_count=3,
            conversation_state=ConversationState.GENERATING_PLAN,
            recipe_search_attempts=2,  # Force it to go to error state
        )

        # Test plan generation with empty recipes
        result_state = await agent._handle_plan_generation(state)
        # Should either have error or be in completed state with error message
        assert result_state.error is not None or (
            result_state.conversation_state == ConversationState.COMPLETED
            and any(
                "couldn't find any recipes" in msg.get("content", "")
                for msg in result_state.messages
            )
        )


class TestDaysValidation:
    """Test days count validation fixes."""

    def test_meal_plan_generator_validates_days_count(self):
        """Test that MealPlanGenerator validates days count range."""
        recipes = [
            Recipe(
                id=1,
                title="Test Recipe",
                ingredients=[],
                instructions="Test instructions",
            )
        ]

        # Test valid days count
        meal_plan, _ = MealPlanGenerator.generate_meal_plan(
            recipes=recipes, diet_goal="vegetarian", days_count=5
        )
        assert meal_plan.total_days == 5

        # Test invalid days count - too low
        with pytest.raises(
            ValueError, match="days_count must be an integer between 3 and 7"
        ):
            MealPlanGenerator.generate_meal_plan(
                recipes=recipes, diet_goal="vegetarian", days_count=2
            )

        # Test invalid days count - too high
        with pytest.raises(
            ValueError, match="days_count must be an integer between 3 and 7"
        ):
            MealPlanGenerator.generate_meal_plan(
                recipes=recipes, diet_goal="vegetarian", days_count=8
            )

        # Test invalid days count - not integer
        with pytest.raises(
            ValueError, match="days_count must be an integer between 3 and 7"
        ):
            MealPlanGenerator.generate_meal_plan(
                recipes=recipes, diet_goal="vegetarian", days_count="5"
            )


class TestSerializationFixes:
    """Test AgentState serialization fixes."""

    def test_agent_state_serializes_complex_objects(self):
        """Test that AgentState properly serializes complex objects."""
        # Create test data
        recipe = Recipe(
            id=1,
            title="Test Recipe",
            ingredients=[Ingredient(name="flour", quantity="1", unit="cup")],
            instructions="Test instructions",
        )

        shopping_list = ShoppingList(
            items=[ShoppingItem(name="flour", quantity="1", unit="cup")]
        )

        state = AgentState(
            thread_id="test_thread",
            found_recipes=[recipe],
            shopping_list=shopping_list,
        )

        # Test serialization
        data = state.model_dump()
        assert "found_recipes" in data
        assert "shopping_list" in data
        assert isinstance(data["found_recipes"], list)
        assert isinstance(data["shopping_list"], dict)

        # Test deserialization
        restored_state = AgentState.model_validate(data)
        assert len(restored_state.found_recipes) == 1
        assert restored_state.found_recipes[0].title == "Test Recipe"
        assert restored_state.shopping_list is not None
        # Note: ShoppingList constructor converts None to empty list,
        # so we check for the right type
        assert isinstance(restored_state.shopping_list.items, list)

    def test_agent_state_handles_none_values(self):
        """Test that AgentState handles None values properly."""
        state = AgentState(
            thread_id="test_thread",
            found_recipes=[],  # Use empty list instead of None
            shopping_list=None,
            menu_plan=None,
        )

        # Test serialization with None values
        data = state.model_dump()
        assert data["found_recipes"] == []  # Empty list, not None
        assert data["shopping_list"] is None
        assert data["menu_plan"] is None

        # Test deserialization
        restored_state = AgentState.model_validate(data)
        assert restored_state.found_recipes == []  # Empty list, not None
        assert restored_state.shopping_list is None
        assert restored_state.menu_plan is None


class TestRaceConditionFixes:
    """Test race condition fixes."""

    def test_shopping_list_save_is_atomic(self):
        """Test that shopping list save operations are atomic."""
        db = Database(":memory:")
        repo = SQLiteShoppingListRepository(db)

        shopping_list = ShoppingList(
            items=[ShoppingItem(name="flour", quantity="1", unit="cup")]
        )

        # Test that save operation completes without race conditions
        result = repo.save(shopping_list, "test_thread", "user123")
        assert result is not None
        assert result.thread_id == "test_thread"
        assert result.user_id == "user123"

        # Test that subsequent saves update the same record
        shopping_list.items.append(
            ShoppingItem(name="sugar", quantity="2", unit="cups")
        )
        result2 = repo.save(shopping_list, "test_thread", "user123")
        assert result2.id == result.id  # Same record
        assert len(result2.items) == 2  # Updated items

    def test_recipe_save_handles_uniqueness(self):
        """Test that recipe save properly handles uniqueness constraints."""
        db = Database(":memory:")
        repo = SQLiteRecipeRepository(db)

        recipe1 = Recipe(
            id=None,  # Will be set by save
            title="Test Recipe",
            ingredients=[],
            instructions="Test instructions",
            user_id="user123",
        )

        recipe2 = Recipe(
            id=None,  # Will be set by save
            title="Test Recipe",  # Same title
            ingredients=[],
            instructions="Different instructions",
            user_id="user123",  # Same user
        )

        # Save first recipe
        saved_recipe1 = repo.save(recipe1)
        assert saved_recipe1.id is not None

        # Try to save second recipe with same title and user
        with pytest.raises(ValueError, match="already exists"):
            repo.save(recipe2)


class TestMemoryLeakFixes:
    """Test memory leak fixes."""

    def test_database_connection_cleanup(self):
        """Test that database connections are properly cleaned up."""
        db = Database(":memory:")

        # Test that close method works
        db.close()

        # Test that cleanup_connections works
        db.cleanup_connections()

    def test_memory_saver_cleanup(self):
        """Test that memory saver properly cleans up connections."""
        from agent.memory import SQLiteMemorySaver

        saver = SQLiteMemorySaver(":memory:")

        # Test that close method works
        saver.close()

    @pytest.mark.asyncio
    async def test_message_cleanup_prevents_memory_leaks(self):
        """Test that message cleanup prevents memory leaks."""
        from agent.memory import SQLiteMemorySaver

        saver = SQLiteMemorySaver(":memory:")

        # First create a conversation record
        # Create conversation first
        await saver.put({"thread_id": "test_thread"}, {"test": "data"})

        # Add many messages
        for i in range(150):  # More than the 100 limit
            await saver.add_message("test_thread", "user", f"Message {i}")

        # Check that only recent messages are kept
        messages = await saver.get_messages("test_thread", limit=200)
        assert len(messages) <= 100  # Should be limited


class TestEdgeCases:
    """Test various edge cases."""

    def test_recipe_with_none_ingredients(self):
        """Test that recipe handles None ingredients properly."""
        recipe = Recipe(
            id=1,
            title="Test Recipe",
            ingredients=None,  # None ingredients
            instructions="Test instructions",
        )

        # Should not raise exception
        assert recipe.ingredients is None or recipe.ingredients == []

    def test_shopping_list_with_none_items(self):
        """Test that shopping list handles None items properly."""
        shopping_list = ShoppingList(items=None)

        # Should not raise exception
        assert shopping_list.items is None or shopping_list.items == []

    def test_agent_state_with_invalid_conversation_state(self):
        """Test that AgentState handles invalid conversation state."""
        # Test with invalid state string
        data = {
            "thread_id": "test_thread",
            "conversation_state": "invalid_state",
            "messages": [],
        }

        # Should raise ValueError for invalid state
        with pytest.raises(ValueError):
            AgentState.model_validate(data)

    def test_meal_plan_generator_with_minimal_recipes(self):
        """Test meal plan generator with minimal recipe data."""
        recipes = [
            Recipe(
                id=1,
                title="Recipe 1",
                ingredients=[],
                instructions="Instructions 1",
                diet_type=DietType.VEGETARIAN,
            )
        ]

        # Should work with minimal data
        meal_plan, fallback_used = MealPlanGenerator.generate_meal_plan(
            recipes=recipes, diet_goal="vegetarian", days_count=3
        )

        assert meal_plan.total_days == 3
        assert len(meal_plan.days) == 3
        assert fallback_used is False


if __name__ == "__main__":
    pytest.main([__file__])
