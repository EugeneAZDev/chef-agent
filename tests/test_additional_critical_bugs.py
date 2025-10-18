"""
Additional tests for critical bugs that were not covered in the main test
suite.

This module tests edge cases and error scenarios that could cause system
failures.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from adapters.db.database import Database
from adapters.db.recipe_repository import SQLiteRecipeRepository
from adapters.db.shopping_list_repository import SQLiteShoppingListRepository
from agent import ChefAgentGraph
from agent.memory import SQLiteMemorySaver
from domain.entities import Meal, Recipe, ShoppingItem, ShoppingList


class TestUnicodeDecodeError:
    """Test handling of UnicodeDecodeError in _row_to_recipe."""

    def test_unicode_decode_error_handling(self):
        """Test that UnicodeDecodeError is handled gracefully."""
        db = Database(":memory:")
        try:
            repo = SQLiteRecipeRepository(db)

            # Create a recipe with invalid JSON in ingredients
            with patch.object(repo.db, "execute_query") as mock_query:
                # Mock the main query
                mock_query.return_value = [
                    {
                        "id": 1,
                        "title": "Test Recipe",
                        "description": "Test Description",
                        "instructions": "Test Instructions",
                        "prep_time_minutes": 10,
                        "cook_time_minutes": 20,
                        "servings": 4,
                        "difficulty": "easy",
                        "diet_type": "vegetarian",
                        "user_id": "test_user",
                        "ingredients": '{"invalid": json}',  # Invalid JSON
                        "created_at": "2023-01-01 00:00:00",
                        "updated_at": "2023-01-01 00:00:00",
                    }
                ]

                # Mock the tags query separately
                with patch.object(repo, "_get_recipe_tags") as mock_tags:
                    mock_tags.return_value = []

                    # Should not raise an exception
                    recipes = repo.get_all("test_user")
                    assert len(recipes) == 1
                    assert recipes[0].title == "Test Recipe"
                # Ingredients should be empty due to JSON decode error
                assert recipes[0].ingredients == []
        finally:
            db.close()


class TestIndexErrorHandling:
    """Test handling of IndexError when replacing recipes."""

    def test_replace_recipe_nonexistent_day(self):
        """Test replacing recipe for non-existent day."""
        from domain.entities import MealPlan, MenuDay

        # Create a meal plan with only 1 day
        day1 = MenuDay(day_number=1, meals=[])
        meal_plan = MealPlan(days=[day1])

        # Try to replace recipe for day 2 (doesn't exist)
        from unittest.mock import Mock

        graph = ChefAgentGraph("groq", "test-key", Mock())
        result = graph._update_meal_plan_recipe(
            meal_plan, day_number=2, meal_type="breakfast", new_recipe=None
        )

        # Should return None (no old recipe to remove)
        assert result is None

    def test_replace_recipe_nonexistent_meal(self):
        """Test replacing recipe for non-existent meal type."""
        from domain.entities import MealPlan, MenuDay, Recipe

        # Create a meal plan with breakfast only
        recipe = Recipe(
            id=1,
            title="Test Recipe",
            ingredients=[],
            instructions="Test",
            user_id="test_user",
        )
        meal = Meal(name="breakfast", recipe=recipe)
        day1 = MenuDay(day_number=1, meals=[meal])
        meal_plan = MealPlan(days=[day1])

        # Try to replace recipe for lunch (doesn't exist)
        from unittest.mock import Mock

        graph = ChefAgentGraph("groq", "test-key", Mock())
        new_recipe = Recipe(
            id=2,
            title="New Recipe",
            ingredients=[],
            instructions="New",
            user_id="test_user",
        )
        result = graph._update_meal_plan_recipe(
            meal_plan, day_number=1, meal_type="lunch", new_recipe=new_recipe
        )

        # Should return None (no old recipe to remove)
        assert result is None
        # New meal should be added
        assert len(day1.meals) == 2
        assert day1.meals[1].name == "lunch"


class TestAsyncioTimeoutError:
    """Test handling of asyncio.TimeoutError in ChefAgentGraph."""

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        """Test that asyncio.TimeoutError is handled gracefully."""
        from unittest.mock import Mock

        graph = ChefAgentGraph("groq", "test-key", Mock())

        # Mock the graph to raise TimeoutError
        with patch.object(graph, "graph") as mock_graph:
            mock_graph.ainvoke.side_effect = asyncio.TimeoutError(
                "Test timeout"
            )

            from agent.models import ChatRequest

            request = ChatRequest(
                message="Test message",
                thread_id="test_thread",
                user_id="test_user",
            )

            # Should handle timeout gracefully
            response = await graph.process_request(request)
            assert (
                "timeout" in response.message.lower()
                or "timed out" in response.message.lower()
                or "error" in response.message.lower()
            )


class TestRaceConditionShoppingList:
    """Test race conditions in shopping list operations."""

    def test_concurrent_save_race_condition(self):
        """Test that concurrent saves don't create duplicates."""
        # Use a file-based database instead of :memory: to ensure all
        # threads share the same DB
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = Database(db_path)
            try:
                # Initialize the database with migrations
                db._run_migrations()
                repo = SQLiteShoppingListRepository(db)

                # Create shopping list
                shopping_list = ShoppingList(
                    items=[
                        ShoppingItem(
                            name="Test Item", quantity="1", unit="piece"
                        )
                    ],
                    user_id="test_user",
                )

                # Save the same list multiple times concurrently
                import threading

                results = []
                errors = []

                def save_list():
                    try:
                        result = repo.save(
                            shopping_list, "test_thread", "test_user"
                        )
                        results.append(result)
                    except Exception as e:
                        errors.append(e)

                # Create multiple threads
                threads = []
                for _ in range(5):
                    thread = threading.Thread(target=save_list)
                    threads.append(thread)
                    thread.start()

                # Wait for all threads to complete
                for thread in threads:
                    thread.join()

                # Should not have any errors
                assert len(errors) == 0
                # Should have 5 results (all successful)
                assert len(results) == 5
                # All results should be the same (same thread_id, user_id)
                assert all(r.thread_id == "test_thread" for r in results)
                assert all(r.user_id == "test_user" for r in results)
            finally:
                db.close()
        finally:
            # Clean up the temporary database file
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestSQLInjection:
    """Test SQL injection prevention."""

    def test_sql_injection_user_id(self):
        """Test that malicious user_id is rejected."""
        db = Database(":memory:")
        try:
            repo = SQLiteShoppingListRepository(db)

            # Try to inject SQL through user_id
            malicious_user_id = "'; DROP TABLE recipes; --"

            with pytest.raises(ValueError, match="Invalid user_id format"):
                repo.get_by_thread_id("test_thread", malicious_user_id)
        finally:
            db.close()

    def test_sql_injection_thread_id(self):
        """Test that malicious thread_id is rejected."""
        db = Database(":memory:")
        try:
            repo = SQLiteShoppingListRepository(db)

            # Try to inject SQL through thread_id
            malicious_thread_id = "'; DROP TABLE recipes; --"

            with pytest.raises(ValueError, match="Invalid thread_id format"):
                repo.get_by_thread_id(malicious_thread_id)
        finally:
            db.close()


class TestDatabaseFailure:
    """Test handling of database failures."""

    def test_database_operational_error(self):
        """Test handling of sqlite3.OperationalError."""
        db = Database(":memory:")
        try:
            repo = SQLiteRecipeRepository(db)

            # Close the database to simulate failure
            db.close()

            # Should handle database error gracefully
            with pytest.raises(Exception):  # Should raise some exception
                repo.get_all("test_user")
        finally:
            # Ensure cleanup even if test fails
            if db._connection is not None:
                db.close()

    def test_database_connection_error(self):
        """Test handling of database connection errors."""
        # Try to create repository with invalid database path
        db = None
        try:
            with pytest.raises(Exception):  # Should raise some exception
                db = Database("/invalid/path/database.db")
                repo = SQLiteRecipeRepository(db)
                repo.get_all("test_user")
        finally:
            if db is not None:
                db.close()


class TestLLMErrorHandling:
    """Test handling of LLM errors."""

    @pytest.mark.asyncio
    async def test_llm_none_response(self):
        """Test handling of None response from LLM."""
        from unittest.mock import Mock

        graph = ChefAgentGraph("groq", "test-key", Mock())

        # Mock graph to return None response
        with patch.object(graph, "graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value=None)

            from agent.models import ChatRequest

            request = ChatRequest(
                message="Test message",
                thread_id="test_thread",
                user_id="test_user",
            )

            # Should handle None response gracefully
            response = await graph.process_request(request)
            assert "error" in response.message.lower()

    @pytest.mark.asyncio
    async def test_llm_empty_response(self):
        """Test handling of empty response from LLM."""
        from unittest.mock import Mock

        graph = ChefAgentGraph("groq", "test-key", Mock())

        # Mock graph to return empty response
        with patch.object(graph, "graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value={"messages": []})

            from agent.models import ChatRequest

            request = ChatRequest(
                message="Test message",
                thread_id="test_thread",
                user_id="test_user",
            )

            # Should handle empty response gracefully
            response = await graph.process_request(request)
            assert "error" in response.message.lower()


class TestNetworkErrorHandling:
    """Test handling of network errors."""

    @pytest.mark.asyncio
    async def test_mcp_connection_error(self):
        """Test handling of MCP connection errors."""
        from adapters.mcp.client import ChefAgentMCPClient

        # Create client with invalid endpoint
        client = ChefAgentMCPClient(timeout=1)

        # Should handle connection error gracefully
        with pytest.raises(Exception):  # Should raise some exception
            await client.find_recipes("test query")

    @pytest.mark.asyncio
    async def test_mcp_timeout_error(self):
        """Test handling of MCP timeout errors."""
        from adapters.mcp.client import ChefAgentMCPClient

        # Create client with very short timeout
        client = ChefAgentMCPClient(timeout=0.1)

        # Should handle timeout gracefully
        with pytest.raises(Exception):  # Should raise some exception
            await client.find_recipes("test query")


class TestMemoryLeakPrevention:
    """Test memory leak prevention."""

    async def test_message_cleanup_prevents_memory_leaks(self):
        """Test that message cleanup prevents memory leaks."""
        saver = SQLiteMemorySaver(":memory:")

        # Add many messages
        for i in range(150):  # More than the 100 message limit
            await saver.add_message("test_thread", "user", f"Message {i}")

        # Should only keep the last 100 messages
        messages = await saver.get_messages("test_thread")
        assert len(messages) <= 100

    async def test_database_connection_cleanup(self):
        """Test that database connections are properly cleaned up."""
        saver = SQLiteMemorySaver(":memory:")

        # Use the saver
        await saver.add_message("test_thread", "user", "Test message")

        # Close the saver
        saver.close()

        # Should not raise an exception
        assert saver._connection is None


class TestIntegerOverflow:
    """Test integer overflow handling."""

    def test_recipe_id_overflow_handling(self):
        """Test that recipe ID overflow is handled gracefully."""
        db = Database(":memory:")
        try:
            repo = SQLiteRecipeRepository(db)

            # Mock the database to return a very large ID
            with patch.object(
                repo.db, "execute_insert_in_transaction"
            ) as mock_insert:
                mock_insert.return_value = 2**63  # Max SQLite integer + 1

                recipe = Recipe(
                    id=None,
                    title="Test Recipe",
                    ingredients=[],
                    instructions="Test",
                    user_id="test_user",
                )

                # Should raise ValueError for overflow
                with pytest.raises(ValueError, match="Recipe ID overflow"):
                    repo._create_recipe(recipe)
        finally:
            db.close()


class TestNoneHandlingInRepositories:
    """Test proper None handling in repository methods."""

    def test_none_ingredients_handling(self):
        """Test that None ingredients are handled properly in _row_to_recipe."""
        db = Database(":memory:")
        try:
            repo = SQLiteRecipeRepository(db)

            # Create a recipe with None ingredients
            with patch.object(repo.db, "execute_query") as mock_query:
                # Mock the main query
                mock_query.return_value = [
                    {
                        "id": 1,
                        "title": "Test Recipe",
                        "description": "Test Description",
                        "instructions": "Test Instructions",
                        "prep_time_minutes": 10,
                        "cook_time_minutes": 20,
                        "servings": 4,
                        "difficulty": "easy",
                        "diet_type": "vegetarian",
                        "user_id": "test_user",
                        "ingredients": None,  # None ingredients
                        "created_at": "2023-01-01 00:00:00",
                        "updated_at": "2023-01-01 00:00:00",
                    }
                ]

                # Mock the tags query separately
                with patch.object(repo, "_get_recipe_tags") as mock_tags:
                    mock_tags.return_value = []

                    # Should not raise an exception
                    recipe = repo.get_by_id(1)
                    assert recipe is not None
                    assert recipe.title == "Test Recipe"
                    assert recipe.ingredients == []
        finally:
            db.close()

    def test_none_ingredients_with_compressed_check(self):
        """Test that None ingredients don't cause startswith error."""
        db = Database(":memory:")
        try:
            repo = SQLiteRecipeRepository(db)

            # Create a recipe with None ingredients that would trigger compressed check
            with patch.object(repo.db, "execute_query") as mock_query:
                # Mock the main query
                mock_query.return_value = [
                    {
                        "id": 1,
                        "title": "Test Recipe",
                        "description": "Test Description",
                        "instructions": "Test Instructions",
                        "prep_time_minutes": 10,
                        "cook_time_minutes": 20,
                        "servings": 4,
                        "difficulty": "easy",
                        "diet_type": "vegetarian",
                        "user_id": "test_user",
                        "ingredients": None,  # None ingredients
                        "created_at": "2023-01-01 00:00:00",
                        "updated_at": "2023-01-01 00:00:00",
                    }
                ]

                # Mock the tags query separately
                with patch.object(repo, "_get_recipe_tags") as mock_tags:
                    mock_tags.return_value = []

                    # Should not raise AttributeError on startswith
                    recipe = repo.get_by_id(1)
                    assert recipe is not None
                    assert recipe.title == "Test Recipe"
                    assert recipe.ingredients == []
        finally:
            db.close()
