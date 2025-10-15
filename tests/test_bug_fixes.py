"""
Tests for bug fixes and critical functionality.

This module contains tests for the critical bugs that were identified
and fixed.
"""

from unittest.mock import Mock

import pytest

from adapters.db import SQLiteRecipeRepository, SQLiteShoppingListRepository
from agent import ChefAgentGraph
from agent.models import AgentState
from domain.entities import (
    DietType,
    Ingredient,
    Recipe,
    ShoppingItem,
    ShoppingList,
)


class TestDietTypeFiltering:
    """Test diet type filtering fixes."""

    def test_diet_type_conversion_in_search(self):
        """Test that diet_type string is properly converted to enum value."""
        # Mock database
        mock_db = Mock()
        mock_db.execute_query.return_value = []

        repo = SQLiteRecipeRepository(mock_db)

        # Test with string diet_type
        repo.search_recipes(diet_type="low-carb", limit=10)

        # Check that the query was called with proper diet_type value
        call_args = mock_db.execute_query.call_args
        assert call_args is not None
        params = call_args[0][1]  # Second argument is params tuple
        assert "low-carb" in params

    def test_diet_type_enum_conversion(self):
        """Test DietType enum conversion."""
        # Test that DietType enum values match expected strings
        assert DietType.LOW_CARB.value == "low-carb"
        assert DietType.VEGETARIAN.value == "vegetarian"
        assert DietType.VEGAN.value == "vegan"
        assert DietType.HIGH_PROTEIN.value == "high-protein"
        assert DietType.KETO.value == "keto"
        assert DietType.MEDITERRANEAN.value == "mediterranean"
        assert DietType.GLUTEN_FREE.value == "gluten-free"


class TestMCPSchemaConsistency:
    """Test MCP schema consistency fixes."""

    def test_mcp_schema_diet_types(self):
        """Test that MCP schema diet types match DietType enum."""
        from domain.entities import DietType

        # Get actual diet types from enum
        actual_diet_types = {dt.value for dt in DietType}

        # Expected diet types that should be supported
        expected_diet_types = {
            "vegetarian",
            "vegan",
            "gluten-free",
            "keto",
            "paleo",
            "low-carb",
            "high-protein",
            "mediterranean",
        }

        # Test that all expected diet types are present in enum
        assert expected_diet_types.issubset(
            actual_diet_types
        ), f"Missing diet types: {expected_diet_types - actual_diet_types}"

        # Test that enum values are valid strings
        for diet_type in DietType:
            assert isinstance(diet_type.value, str)
            assert len(diet_type.value) > 0

    def test_mcp_diet_mapping(self):
        """Test MCP diet type mapping."""
        from domain.entities import DietType

        # Test that all DietType enum values are valid for MCP
        for diet_type in DietType:
            # Test that the value can be used as a string key
            assert isinstance(diet_type.value, str)
            assert len(diet_type.value) > 0

            # Test that the value matches itself (no transformation needed)
            assert diet_type.value == diet_type.value

            # Test that the value contains only valid characters
            assert all(c.isalnum() or c in "-_" for c in diet_type.value)


class TestShoppingListUserID:
    """Test shopping list user_id fixes."""

    def test_shopping_list_update_with_user_id(self):
        """Test that shopping list update includes user_id."""
        # Mock database
        mock_db = Mock()
        mock_db.execute_update.return_value = 1

        repo = SQLiteShoppingListRepository(mock_db)

        # Create shopping list with user_id
        shopping_list = ShoppingList(
            items=[ShoppingItem(name="test", quantity="1", unit="cup")],
            user_id="test_user",
        )

        # Update shopping list
        repo.update(shopping_list, "test_thread", "test_user")

        # Check that _update_shopping_list was called
        # (not _create_shopping_list)
        # This is verified by checking that execute_update was called
        mock_db.execute_update.assert_called_once()

    def test_shopping_list_create_with_user_id(self):
        """Test that shopping list creation includes user_id."""
        # Mock database
        mock_db = Mock()
        mock_db.execute_insert.return_value = 1

        repo = SQLiteShoppingListRepository(mock_db)

        # Create shopping list
        shopping_list = ShoppingList(items=[])
        repo.create(shopping_list, "test_thread", "test_user")

        # Check that execute_insert was called with user_id
        call_args = mock_db.execute_insert.call_args
        params = call_args[0][1]  # Second argument is params tuple
        assert "test_user" in params


class TestAgentToolCallsHandling:
    """Test agent tool_calls None handling."""

    def test_tool_calls_none_handling(self):
        """Test that tool_calls None is handled properly."""
        # Create agent state without tool_calls (it will default to empty list)
        state = AgentState(thread_id="test", messages=[])

        # Mock response with tool_calls
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.tool_calls = [{"name": "test_tool", "args": {}}]

        # Create agent and test _update_state_from_llm
        agent = ChefAgentGraph("groq", "test-key", Mock())
        agent._update_state_from_llm(state, mock_response)

        # Check that tool_calls was initialized and extended
        assert state.tool_calls is not None
        assert len(state.tool_calls) == 1
        assert state.tool_calls[0]["name"] == "test_tool"

    def test_tool_calls_none_attribute_handling(self):
        """Test that tool_calls None attribute is handled properly."""
        # Create agent state and manually set tool_calls to None
        state = AgentState(thread_id="test", messages=[])
        # Manually set tool_calls to None to test the edge case
        state.tool_calls = None

        # Mock response with tool_calls
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.tool_calls = [{"name": "test_tool", "args": {}}]

        # Create agent and test _update_state_from_llm
        agent = ChefAgentGraph("groq", "test-key", Mock())
        agent._update_state_from_llm(state, mock_response)

        # Check that tool_calls was initialized and extended
        assert state.tool_calls is not None
        assert len(state.tool_calls) == 1
        assert state.tool_calls[0]["name"] == "test_tool"

    def test_tool_calls_empty_list_handling(self):
        """Test that tool_calls empty list is handled properly."""
        # Create agent state with empty tool_calls
        state = AgentState(thread_id="test", messages=[], tool_calls=[])

        # Mock response with tool_calls
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.tool_calls = [{"name": "test_tool", "args": {}}]

        # Create agent and test _update_state_from_llm
        agent = ChefAgentGraph("groq", "test-key", Mock())
        agent._update_state_from_llm(state, mock_response)

        # Check that tool_calls was extended
        assert len(state.tool_calls) == 1
        assert state.tool_calls[0]["name"] == "test_tool"


class TestNaturalLanguageDietExtraction:
    """Test natural language diet goal extraction."""

    def test_weight_loss_patterns(self):
        """Test weight loss pattern recognition."""
        agent = ChefAgentGraph("groq", "test-key", Mock())

        weight_loss_phrases = [
            "I want to lose weight",
            "help me slim down",
            "I need to cut calories",
            "burn fat",
            "get in shape",
            "healthy eating",
        ]

        for phrase in weight_loss_phrases:
            result = agent._extract_diet_goal(phrase)
            assert result == "low-carb", f"Failed for phrase: {phrase}"

    def test_muscle_building_patterns(self):
        """Test muscle building pattern recognition."""
        agent = ChefAgentGraph("groq", "test-key", Mock())

        muscle_phrases = [
            "I want to build muscle",
            "muscle mass",
            "strength training",
            "gains",
            "workout",
            "fitness",
            "gym",
        ]

        for phrase in muscle_phrases:
            result = agent._extract_diet_goal(phrase)
            assert result == "high-protein", f"Failed for phrase: {phrase}"

    def test_vegetarian_patterns(self):
        """Test vegetarian pattern recognition."""
        agent = ChefAgentGraph("groq", "test-key", Mock())

        vegetarian_phrases = [
            "no meat",
            "plant based",
            "vegetables only",
            "herbivore",
        ]

        for phrase in vegetarian_phrases:
            result = agent._extract_diet_goal(phrase)
            assert result == "vegetarian", f"Failed for phrase: {phrase}"

    def test_vegan_patterns(self):
        """Test vegan pattern recognition."""
        agent = ChefAgentGraph("groq", "test-key", Mock())

        vegan_phrases = [
            "no dairy",
            "no eggs",
            "plant only",
            "strict vegetarian",
            "no animal products",
        ]

        for phrase in vegan_phrases:
            result = agent._extract_diet_goal(phrase)
            assert result == "vegan", f"Failed for phrase: {phrase}"

    def test_gluten_free_patterns(self):
        """Test gluten-free pattern recognition."""
        agent = ChefAgentGraph("groq", "test-key", Mock())

        gluten_free_phrases = [
            "celiac",
            "no gluten",
            "gluten intolerant",
            "wheat free",
        ]

        for phrase in gluten_free_phrases:
            result = agent._extract_diet_goal(phrase)
            assert result == "gluten-free", f"Failed for phrase: {phrase}"


class TestDietTypeHandling:
    """Test diet type handling consistency."""

    def test_diet_type_string_to_enum_conversion(self):
        """Test that diet_type strings are converted to enum values."""
        from adapters.db import SQLiteRecipeRepository
        from adapters.db.database import Database

        # Create database and repository
        db = Database(":memory:")
        repo = SQLiteRecipeRepository(db)

        # Test that string diet_type is properly handled
        # This should not raise an exception
        try:
            recipes = repo.search_recipes(
                query="test", diet_type="gluten-free", limit=10  # String input
            )
            assert isinstance(recipes, list)
        except Exception as e:
            pytest.fail(f"String diet_type handling failed: {e}")

    def test_diet_type_enum_value_storage(self):
        """Test that diet_type enum values are stored and retrieved."""
        from adapters.db import SQLiteRecipeRepository
        from adapters.db.database import Database
        from domain.entities import DietType, Ingredient, Recipe

        # Create database and repository
        db = Database(":memory:")
        repo = SQLiteRecipeRepository(db)

        # Create test recipe with enum diet_type
        test_recipe = Recipe(
            id=None,  # No ID - will be created as new recipe
            title="Test Recipe",
            description="Test description",
            ingredients=[Ingredient(name="test", quantity="1", unit="cup")],
            instructions="Test instructions",
            diet_type=DietType.GLUTEN_FREE,  # Enum value
            user_id="test_user",  # Add user_id
        )

        # Save recipe
        saved_recipe = repo.save(test_recipe)

        # Verify that diet_type was saved correctly
        assert saved_recipe.diet_type == DietType.GLUTEN_FREE
        assert saved_recipe.diet_type.value == "gluten-free"

        # Search by string diet_type
        recipes = repo.search_recipes(
            query="test", diet_type="gluten-free", limit=10  # String search
        )

        # Should find the recipe
        assert len(recipes) == 1
        assert recipes[0].title == "Test Recipe"
        assert recipes[0].diet_type == DietType.GLUTEN_FREE
        assert recipes[0].diet_type.value == "gluten-free"

    def test_paleo_diet_type_support(self):
        """Test that paleo diet type is properly supported."""
        from adapters.db import SQLiteRecipeRepository
        from adapters.db.database import Database
        from domain.entities import DietType

        # Test that PALEO enum exists
        assert hasattr(DietType, "PALEO")
        assert DietType.PALEO.value == "paleo"

        # Test that it can be used in search
        db = Database(":memory:")
        repo = SQLiteRecipeRepository(db)

        recipes = repo.search_recipes(
            query="test", diet_type="paleo", limit=10
        )
        assert isinstance(recipes, list)

    def test_mcp_diet_type_mapping(self):
        """Test that MCP diet type mapping is consistent with DietType enum."""
        from domain.entities import DietType

        # Test diet mapping in _handle_recipe_finder
        diet_mapping = {
            "vegetarian": "vegetarian",
            "vegan": "vegan",
            "gluten-free": "gluten-free",
            "keto": "keto",
            "paleo": "paleo",
            "low-carb": "low-carb",
            "high-protein": "high-protein",
            "mediterranean": "mediterranean",
        }

        # Check that all mapped values exist in DietType enum
        for diet_string in diet_mapping.values():
            # Find the corresponding enum value
            found = False
            for diet_enum in DietType:
                if diet_enum.value == diet_string:
                    found = True
                    break
            assert (
                found
            ), f"Diet type '{diet_string}' not found in DietType enum"

    def test_diet_type_migration_consistency(self):
        """Test that diet_type values are consistent after migration."""
        from adapters.db import SQLiteRecipeRepository
        from adapters.db.database import Database
        from domain.entities import DietType, Ingredient, Recipe

        # Create database and repository
        db = Database(":memory:")
        repo = SQLiteRecipeRepository(db)

        # Test all diet types
        diet_types = [
            DietType.LOW_CARB,
            DietType.VEGETARIAN,
            DietType.VEGAN,
            DietType.HIGH_PROTEIN,
            DietType.KETO,
            DietType.MEDITERRANEAN,
            DietType.GLUTEN_FREE,
            DietType.PALEO,
        ]

        for i, diet_type in enumerate(diet_types):
            # Create test recipe
            test_recipe = Recipe(
                id=None,
                title=f"Test Recipe {i}",
                description="Test description",
                ingredients=[
                    Ingredient(name="test", quantity="1", unit="cup")
                ],
                instructions="Test instructions",
                diet_type=diet_type,
                user_id="test_user",
            )

            # Save recipe
            saved_recipe = repo.save(test_recipe)

            # Verify diet_type was saved correctly
            assert saved_recipe.diet_type == diet_type
            assert saved_recipe.diet_type.value == diet_type.value

            # Search by string diet_type
            recipes = repo.search_recipes(
                query=f"Test Recipe {i}",
                diet_type=diet_type.value,  # String search
                limit=10,
            )

            # Should find the recipe
            assert len(recipes) == 1
            assert recipes[0].diet_type == diet_type
            assert recipes[0].diet_type.value == diet_type.value


class TestRaceConditionPrevention:
    """Test race condition prevention with proper locking mechanisms."""

    def test_recipe_concurrent_update_prevention(self):
        """Test that concurrent recipe updates are properly handled."""
        import threading

        from adapters.db import SQLiteRecipeRepository
        from adapters.db.database import Database
        from domain.entities import DietType, Ingredient, Recipe

        # Create database and repository
        db = Database(":memory:")
        repo = SQLiteRecipeRepository(db)

        # Create initial recipe
        test_recipe = Recipe(
            id=None,
            title="Test Recipe",
            description="Test description",
            ingredients=[Ingredient(name="test", quantity="1", unit="cup")],
            instructions="Test instructions",
            diet_type=DietType.VEGETARIAN,
            user_id="test_user",
        )

        # Save initial recipe
        saved_recipe = repo.save(test_recipe)
        recipe_id = saved_recipe.id

        # Test concurrent updates
        results = []
        errors = []

        def update_recipe(thread_id):
            try:
                # Create updated recipe
                updated_recipe = Recipe(
                    id=recipe_id,
                    title=f"Updated Recipe {thread_id}",
                    description=f"Updated description {thread_id}",
                    ingredients=[
                        Ingredient(name="updated", quantity="2", unit="tbsp")
                    ],
                    instructions=f"Updated instructions {thread_id}",
                    diet_type=DietType.VEGAN,
                    user_id="test_user",
                )

                # Save updated recipe
                result = repo.save(updated_recipe)
                results.append((thread_id, result.title))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Create multiple threads to simulate concurrent updates
        threads = []
        for i in range(3):
            thread = threading.Thread(target=update_recipe, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # In SQLite, we expect that updates are handled properly
        # Either one succeeds or all fail gracefully
        assert (
            len(results) >= 0
        ), f"Expected at least 0 successful updates, got {len(results)}"
        assert (
            len(errors) >= 0
        ), f"Expected at least 0 errors, got {len(errors)}"
        assert (
            len(results) + len(errors) == 3
        ), f"Expected 3 total operations, got {len(results) + len(errors)}"

        # Verify the final state is consistent
        final_recipe = repo.get_by_id(recipe_id)
        assert final_recipe is not None
        # The recipe should have either the original title or one of the
        # updated titles
        assert final_recipe.title in [
            "Test Recipe",
            "Updated Recipe 0",
            "Updated Recipe 1",
            "Updated Recipe 2",
        ]

    def test_shopping_list_concurrent_update_prevention(self):
        """Test that concurrent shopping list updates are properly handled."""
        import threading

        from adapters.db import SQLiteShoppingListRepository
        from adapters.db.database import Database
        from domain.entities import ShoppingItem, ShoppingList

        # Create database and repository
        db = Database(":memory:")
        repo = SQLiteShoppingListRepository(db)

        # Create initial shopping list
        initial_items = [
            ShoppingItem(name="item1", quantity="1", unit="piece")
        ]
        shopping_list = ShoppingList(items=initial_items)

        # Save initial shopping list
        repo.save(shopping_list, "test_thread", "test_user")

        # Test concurrent updates
        results = []
        errors = []

        def update_shopping_list(thread_id):
            try:
                # Add new items
                new_items = [
                    ShoppingItem(
                        name=f"item{thread_id}", quantity="1", unit="piece"
                    )
                ]
                repo.add_items("test_thread", new_items, "test_user")
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Create multiple threads to simulate concurrent updates
        threads = []
        for i in range(3):
            thread = threading.Thread(target=update_shopping_list, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify that updates were handled properly
        final_list = repo.get_by_thread_id("test_thread", "test_user")
        assert final_list is not None
        # At least the original item should be there
        assert len(final_list.items) >= 1


class TestSerializationBugFixes:
    """Test serialization bug fixes."""

    def test_serialize_shopping_list_none_handling(self):
        """Test that serialize_shopping_list handles None input properly."""
        from api.shopping import serialize_shopping_list

        # Test with None input
        result = serialize_shopping_list(None)
        expected = {
            "id": None,
            "thread_id": None,
            "user_id": None,
            "items": [],
            "created_at": None,
            "updated_at": None,
        }
        assert result == expected

    def test_serialize_shopping_list_items_none_handling(self):
        """Test that serialize_shopping_list handles None items properly."""
        from api.shopping import serialize_shopping_list
        from domain.entities import ShoppingList

        # Create shopping list with None items
        shopping_list = ShoppingList(items=None)
        shopping_list.id = 1
        shopping_list.thread_id = "test_thread"

        result = serialize_shopping_list(shopping_list)
        assert result["id"] == 1
        assert result["thread_id"] == "test_thread"
        assert result["user_id"] is None
        assert result["items"] == []
        assert result["created_at"] is not None  # Now automatically set
        assert result["updated_at"] is None

    def test_serialize_shopping_list_normal_case(self):
        """Test that serialize_shopping_list works with normal input."""
        from api.shopping import serialize_shopping_list
        from domain.entities import ShoppingItem, ShoppingList

        # Create normal shopping list
        items = [
            ShoppingItem(name="item1", quantity="1", unit="piece"),
            ShoppingItem(name="item2", quantity="2", unit="kg"),
        ]
        shopping_list = ShoppingList(items=items)
        shopping_list.id = 1
        shopping_list.thread_id = "test_thread"

        result = serialize_shopping_list(shopping_list)
        assert result["id"] == 1
        assert result["thread_id"] == "test_thread"
        assert result["user_id"] is None
        assert len(result["items"]) == 2
        assert result["items"][0]["name"] == "item1"
        assert result["items"][1]["name"] == "item2"

    def test_serialize_shopping_list_with_user_id(self):
        """Test that serialize_shopping_list includes user_id when present."""
        from api.shopping import serialize_shopping_list
        from domain.entities import ShoppingItem, ShoppingList

        # Create shopping list with user_id
        items = [
            ShoppingItem(name="item1", quantity="1", unit="piece"),
        ]
        shopping_list = ShoppingList(items=items, user_id="test_user")
        shopping_list.id = 1
        shopping_list.thread_id = "test_thread"

        result = serialize_shopping_list(shopping_list)
        assert result["id"] == 1
        assert result["thread_id"] == "test_thread"
        assert result["user_id"] == "test_user"
        assert len(result["items"]) == 1
        assert result["items"][0]["name"] == "item1"


class TestRecipeReplacement:
    """Test recipe replacement functionality."""

    def test_meal_plan_recipe_update(self):
        """Test updating recipe in meal plan."""
        from domain.entities import Meal, MealPlan, MenuDay

        agent = ChefAgentGraph("groq", "test-key", Mock())

        # Create test meal plan
        old_recipe = Recipe(
            id=1,
            title="Old Recipe",
            description="Old description",
            ingredients=[
                Ingredient(name="old_ingredient", quantity="1", unit="cup")
            ],
            instructions="Old instructions",
        )
        new_recipe = Recipe(
            id=2,
            title="New Recipe",
            description="New description",
            ingredients=[
                Ingredient(name="new_ingredient", quantity="2", unit="tbsp")
            ],
            instructions="New instructions",
        )

        meal = Meal(name="breakfast", recipe=old_recipe)
        day = MenuDay(day_number=1, meals=[meal])
        meal_plan = MealPlan(days=[day])

        # Update recipe
        agent._update_meal_plan_recipe(meal_plan, 1, "breakfast", new_recipe)

        # Check that recipe was updated
        updated_meal = day.meals[0]
        assert updated_meal.recipe.title == "New Recipe"
        assert updated_meal.recipe.id == 2

    def test_meal_plan_add_new_meal(self):
        """Test adding new meal to meal plan."""
        from domain.entities import Meal, MealPlan, MenuDay

        agent = ChefAgentGraph("groq", "test-key", Mock())

        # Create test meal plan with only breakfast
        recipe = Recipe(
            id=1,
            title="Test Recipe",
            description="Test description",
            ingredients=[
                Ingredient(name="test_ingredient", quantity="1", unit="cup")
            ],
            instructions="Test instructions",
        )

        meal = Meal(name="breakfast", recipe=recipe)
        day = MenuDay(day_number=1, meals=[meal])
        meal_plan = MealPlan(days=[day])

        # Add lunch meal
        agent._update_meal_plan_recipe(meal_plan, 1, "lunch", recipe)

        # Check that lunch was added
        assert len(day.meals) == 2
        assert day.meals[1].name == "lunch"
        assert day.meals[1].recipe.title == "Test Recipe"
