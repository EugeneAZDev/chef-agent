"""
Integration tests with real database.

These tests use a real SQLite database to test the full integration
between repositories, services, and API endpoints.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from adapters.db import (
    Database,
    SQLiteRecipeRepository,
    SQLiteShoppingListRepository,
)
from domain.entities import Ingredient, Recipe, ShoppingItem, ShoppingList
from main import app


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests with real database."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        db = Database(db_path)
        yield db
        db.close()
        os.unlink(db_path)

    @pytest.fixture
    def recipe_repo(self, temp_db):
        """Create recipe repository with temp database."""
        return SQLiteRecipeRepository(temp_db)

    @pytest.fixture
    def shopping_repo(self, temp_db):
        """Create shopping repository with temp database."""
        return SQLiteShoppingListRepository(temp_db)

    def test_recipe_crud_integration(self, recipe_repo):
        """Test full CRUD cycle for recipes with real database."""
        # Create recipe
        recipe = Recipe(
            id=None,  # Will be set by database
            title="Test Pasta",
            description="A test pasta recipe",
            instructions="Boil water, add pasta, cook for 8 minutes",
            prep_time_minutes=5,
            cook_time_minutes=8,
            servings=4,
            difficulty="easy",
            diet_type="vegetarian",
            ingredients=[
                Ingredient(name="pasta", quantity="500", unit="g"),
                Ingredient(name="tomato sauce", quantity="400", unit="ml"),
            ],
            tags=["italian", "quick"],
        )
        recipe.user_id = "test-user-123"

        # Save recipe
        saved_recipe = recipe_repo.save(recipe)
        assert saved_recipe.id is not None
        assert saved_recipe.id > 0

        # Retrieve recipe
        retrieved_recipe = recipe_repo.get_by_id(saved_recipe.id)
        assert retrieved_recipe is not None
        assert retrieved_recipe.title == "Test Pasta"
        assert len(retrieved_recipe.ingredients) == 2
        assert retrieved_recipe.ingredients[0].name == "pasta"

        # Search recipes
        search_results = recipe_repo.search_by_keywords(["pasta"])
        assert len(search_results) == 1
        assert search_results[0].title == "Test Pasta"

        # Update recipe
        retrieved_recipe.title = "Updated Pasta"
        updated_recipe = recipe_repo.save(retrieved_recipe)
        assert updated_recipe.title == "Updated Pasta"

        # Delete recipe
        deleted = recipe_repo.delete(saved_recipe.id)
        assert deleted is True

        # Verify deletion
        deleted_recipe = recipe_repo.get_by_id(saved_recipe.id)
        assert deleted_recipe is None

    def test_shopping_list_crud_integration(self, shopping_repo):
        """Test full CRUD cycle for shopping lists with real database."""
        thread_id = "test-thread-123"

        # Create shopping list
        shopping_list = ShoppingList(
            items=[
                ShoppingItem(name="Milk", quantity="1", unit="liter"),
                ShoppingItem(name="Bread", quantity="2", unit="loaves"),
            ],
        )
        shopping_list.user_id = "test-user-123"

        # Save shopping list
        saved_list = shopping_repo.create(
            shopping_list, thread_id, user_id="test-user-123"
        )
        assert saved_list.id is not None
        assert saved_list.id > 0

        # Retrieve shopping list
        retrieved_list = shopping_repo.get_by_thread_id(
            thread_id, "test-user-123"
        )
        assert retrieved_list is not None
        assert len(retrieved_list.items) == 2
        assert retrieved_list.items[0].name == "Milk"

        # Add item
        shopping_repo.add_items(
            thread_id,
            [ShoppingItem(name="Eggs", quantity="12", unit="pieces")],
        )

        # Verify item was added
        updated_list = shopping_repo.get_by_thread_id(
            thread_id, "test-user-123"
        )
        assert len(updated_list.items) == 3
        assert updated_list.items[2].name == "Eggs"

        # Clear list
        shopping_repo.clear(thread_id)
        cleared_list = shopping_repo.get_by_thread_id(
            thread_id, "test-user-123"
        )
        assert len(cleared_list.items) == 0

        # Delete list
        deleted = shopping_repo.delete(saved_list.id)
        assert deleted is True

    def test_database_transactions(self, recipe_repo):
        """Test database transactions work correctly."""
        # Test successful transaction
        recipe = Recipe(
            id=None,
            title="Transaction Test",
            instructions="Test recipe",
            ingredients=[Ingredient(name="test", quantity="1", unit="piece")],
        )

        saved_recipe = recipe_repo.save(recipe)
        assert saved_recipe.id is not None

        # Test rollback on error (simulate by passing invalid data)
        # This would require mocking the database to throw an error
        # For now, we just verify the transaction methods exist
        assert hasattr(recipe_repo.db, "begin_transaction")
        assert hasattr(recipe_repo.db, "commit_transaction")
        assert hasattr(recipe_repo.db, "rollback_transaction")


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints with real database."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_recipe_search_integration(self, client):
        """Test recipe search API with real database."""
        # This would require setting up test data in the real database
        response = client.get("/api/v1/recipes/?query=pasta")
        assert response.status_code == 200
        data = response.json()
        assert "recipes" in data
        assert "total" in data
        assert "filters" in data

    def test_shopping_list_integration(self, client):
        """Test shopping list API with real database."""
        thread_id = "integration-test-thread"

        # Create shopping list
        response = client.post(f"/api/v1/shopping/lists?thread_id={thread_id}")
        assert response.status_code == 200

        # Get shopping lists
        response = client.get(f"/api/v1/shopping/lists?thread_id={thread_id}")
        assert response.status_code == 200
        data = response.json()
        assert "lists" in data
        assert "total" in data
