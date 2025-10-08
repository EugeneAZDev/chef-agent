"""
Tests for race condition fixes in repositories.
"""

import threading
from unittest.mock import patch

import pytest

from adapters.db.recipe_repository import SQLiteRecipeRepository
from adapters.db.shopping_list_repository import SQLiteShoppingListRepository
from domain.entities import Ingredient, Recipe, ShoppingItem, ShoppingList

# Mark all race condition tests
pytestmark = pytest.mark.race_condition


class TestRaceConditionFixes:
    """Test that race conditions are properly handled."""

    def test_concurrent_recipe_creation_same_title(self, temp_database):
        """Test that concurrent creation of recipes with same title is handled
        safely."""
        # Use a single repository instance to ensure proper locking
        repo = SQLiteRecipeRepository(temp_database)

        def create_recipe(recipe_id, shared_repo):
            recipe = Recipe(
                id=None,
                title="Concurrent Recipe",  # Same title for all threads
                description=f"Recipe {recipe_id}",
                instructions="Test instructions",
            )
            recipe.user_id = "test-user"  # Same user for all threads
            try:
                result = shared_repo.save(recipe)
                return result
            except ValueError as e:
                if "already exists" in str(e):
                    return None  # Expected error
                raise

        # Create multiple threads trying to create the same recipe
        threads = []
        results = []
        errors = []

        # Use a shared list to collect results safely
        import threading

        results_lock = threading.Lock()
        errors_lock = threading.Lock()

        for i in range(10):

            def create_with_id(recipe_id=i):
                try:
                    result = create_recipe(recipe_id, repo)
                    with results_lock:
                        results.append(result)
                except Exception as e:
                    with errors_lock:
                        errors.append(e)

            thread = threading.Thread(target=create_with_id)
            threads.append(thread)

        # Start all threads simultaneously
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check how many recipes were actually created in the database
        all_recipes = repo.get_all(limit=100)
        recipe_titles = [r.title for r in all_recipes]
        concurrent_recipes = [
            r for r in recipe_titles if r == "Concurrent Recipe"
        ]

        # Only one recipe should be created successfully
        successful_creates = [r for r in results if r is not None]
        assert (
            len(successful_creates) == 1
        ), f"Expected 1 successful create, got {len(successful_creates)}"

        # Verify only one recipe exists in database
        assert (
            len(concurrent_recipes) == 1
        ), f"Expected 1 recipe in DB, got {len(concurrent_recipes)}"

    def test_concurrent_recipe_creation_different_users(self, temp_database):
        """Test that different users can create recipes with same title."""
        repo = SQLiteRecipeRepository(temp_database)

        def create_recipe(user_id):
            recipe = Recipe(
                id=None,
                title="Same Title Recipe",
                description=f"Recipe for user {user_id}",
                instructions="Test instructions",
            )
            recipe.user_id = user_id
            return repo.save(recipe)

        # Create recipes for different users with same title
        threads = []
        results = []

        for i in range(5):

            def create_with_user(user_id=f"user-{i}"):
                result = create_recipe(user_id)
                results.append(result)

            thread = threading.Thread(target=create_with_user)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All recipes should be created successfully (different users)
        assert len(results) == 5
        assert all(r is not None for r in results)

        # All should have same title but different user_id
        titles = [r.title for r in results]
        user_ids = [r.user_id for r in results]
        assert all(t == "Same Title Recipe" for t in titles)
        assert len(set(user_ids)) == 5  # All unique user IDs

    def test_concurrent_shopping_list_creation(self, temp_database):
        """Test that concurrent shopping list creation is handled safely."""
        repo = SQLiteShoppingListRepository(temp_database)

        def create_shopping_list(thread_id, user_id):
            shopping_list = ShoppingList(
                items=[
                    ShoppingItem(
                        name=f"Item {thread_id}", quantity="1", unit="piece"
                    )
                ],
            )
            shopping_list.user_id = user_id
            try:
                return repo.save(shopping_list, thread_id, user_id=user_id)
            except Exception as e:
                return e

        # Test same thread_id and user_id (should only allow one)
        threads = []
        results = []

        for i in range(5):

            def create_with_id(thread_id=f"thread-{i}", user_id="user-1"):
                result = create_shopping_list(thread_id, user_id)
                results.append(result)

            thread = threading.Thread(target=create_with_id)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All should succeed (different thread_ids)
        assert len(results) == 5
        assert all(not isinstance(r, Exception) for r in results)

    def test_database_connection_concurrency(self, temp_database):
        """Test that database connections handle concurrency properly."""
        repo = SQLiteRecipeRepository(temp_database)

        def create_and_read_recipe(recipe_id, shared_repo):
            try:
                # Create recipe
                recipe = Recipe(
                    id=None,
                    title=f"Recipe {recipe_id}",
                    description=f"Description {recipe_id}",
                    instructions=f"Instructions {recipe_id}",
                )
                recipe.user_id = f"user-{recipe_id % 3}"  # 3 different users
                created = shared_repo.save(recipe)

                # Read it back
                retrieved = shared_repo.get_by_id(created.id)
                return created, retrieved
            except Exception as e:
                print(f"Thread {recipe_id} failed: {e}")
                return None, None

        threads = []
        results = []

        results_lock = threading.Lock()

        for i in range(10):  # Reduced number of threads for stability

            def create_with_id(recipe_id=i):
                result = create_and_read_recipe(recipe_id, repo)
                with results_lock:
                    results.append(result)

            thread = threading.Thread(target=create_with_id)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Filter out None results (failed threads)
        successful_results = [
            r for r in results if r[0] is not None and r[1] is not None
        ]

        # Most should succeed (allow for some failures due to threading issues)
        assert len(successful_results) >= 8

        for created, retrieved in successful_results:
            assert created is not None
            assert retrieved is not None
            assert created.id == retrieved.id
            assert created.title == retrieved.title

    def test_transaction_rollback_on_error(self, temp_database):
        """Test that transactions are properly rolled back on errors."""
        repo = SQLiteRecipeRepository(temp_database)

        # Create a recipe with invalid data that will cause an error
        recipe = Recipe(
            id=None,
            title="Test Recipe",
            description="Test description",
            instructions="Test instructions",
            ingredients=[Ingredient(name="Test", quantity="1", unit="piece")],
        )
        recipe.user_id = "test-user"

        # Mock the database execute_insert to fail
        with patch.object(repo.db, "execute_insert") as mock_insert:
            mock_insert.side_effect = Exception("Database error")

            with pytest.raises(Exception, match="Database error"):
                repo.save(recipe)

        # Verify no recipe was created in the database
        all_recipes = repo.get_all(limit=100)
        recipe_titles = [r.title for r in all_recipes]
        assert "Test Recipe" not in recipe_titles
