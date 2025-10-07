"""
Tests for database repositories.
"""

import os
import tempfile

from adapters.db import (
    Database,
    SQLiteRecipeRepository,
    SQLiteShoppingListRepository,
)
from domain.entities import (
    DietType,
    Ingredient,
    Recipe,
    ShoppingItem,
    ShoppingList,
)


class TestSQLiteRecipeRepository:
    """Test SQLiteRecipeRepository."""

    def setup_method(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        self.db = Database(self.temp_db.name)
        self.recipe_repo = SQLiteRecipeRepository(self.db)

    def teardown_method(self):
        """Clean up test database."""
        self.db.close()
        os.unlink(self.temp_db.name)

    def test_create_and_get_recipe(self):
        """Test creating and retrieving a recipe."""
        # Create test recipe
        ingredients = [
            Ingredient(name="flour", quantity="2", unit="cups"),
            Ingredient(name="eggs", quantity="2", unit="pieces"),
        ]

        recipe = Recipe(
            id=None,
            title="Test Pancakes",
            description="Delicious pancakes",
            ingredients=ingredients,
            instructions="Mix and cook",
            prep_time_minutes=10,
            cook_time_minutes=15,
            tags=["breakfast", "easy"],
        )

        # Save recipe
        saved_recipe = self.recipe_repo.save(recipe)

        # Verify recipe was saved
        assert saved_recipe.id is not None
        assert saved_recipe.title == "Test Pancakes"
        assert len(saved_recipe.ingredients) == 2
        assert "breakfast" in saved_recipe.tags

        # Retrieve recipe
        retrieved_recipe = self.recipe_repo.get_by_id(saved_recipe.id)
        assert retrieved_recipe is not None
        assert retrieved_recipe.title == "Test Pancakes"
        assert len(retrieved_recipe.ingredients) == 2
        assert retrieved_recipe.ingredients[0].name == "flour"

    def test_search_by_tags(self):
        """Test searching recipes by tags."""
        # Create test recipes
        recipe1 = Recipe(
            id=None,
            title="Veggie Salad",
            ingredients=[],
            instructions="Mix vegetables",
            tags=["vegetarian", "healthy"],
        )

        recipe2 = Recipe(
            id=None,
            title="Chicken Soup",
            ingredients=[],
            instructions="Cook chicken",
            tags=["meat", "soup"],
        )

        self.recipe_repo.save(recipe1)
        self.recipe_repo.save(recipe2)

        # Search by vegetarian tag
        vegetarian_recipes = self.recipe_repo.search_by_tags(["vegetarian"])
        assert len(vegetarian_recipes) == 1
        assert vegetarian_recipes[0].title == "Veggie Salad"

        # Search by multiple tags
        healthy_recipes = self.recipe_repo.search_by_tags(["healthy", "soup"])
        assert len(healthy_recipes) == 2

    def test_search_by_diet_type(self):
        """Test searching recipes by diet type."""
        recipe = Recipe(
            id=None,
            title="Low Carb Breakfast",
            ingredients=[],
            instructions="Low carb meal",
            tags=["low-carb"],
        )

        self.recipe_repo.save(recipe)

        # Search by diet type
        low_carb_recipes = self.recipe_repo.search_by_diet_type(
            DietType.LOW_CARB
        )
        assert len(low_carb_recipes) == 1
        assert low_carb_recipes[0].title == "Low Carb Breakfast"

    def test_search_by_keywords(self):
        """Test searching recipes by keywords."""
        recipe = Recipe(
            id=None,
            title="Chocolate Cake",
            description="Delicious chocolate dessert",
            ingredients=[],
            instructions="Bake cake",
        )

        self.recipe_repo.save(recipe)

        # Search by keyword
        results = self.recipe_repo.search_by_keywords(["chocolate"])
        assert len(results) == 1
        assert results[0].title == "Chocolate Cake"

    def test_delete_recipe(self):
        """Test deleting a recipe."""
        recipe = Recipe(
            id=None,
            title="Test Recipe",
            ingredients=[],
            instructions="Test instructions",
        )

        saved_recipe = self.recipe_repo.save(recipe)
        recipe_id = saved_recipe.id

        # Verify recipe exists
        assert self.recipe_repo.get_by_id(recipe_id) is not None

        # Delete recipe
        success = self.recipe_repo.delete(recipe_id)
        assert success is True

        # Verify recipe is deleted
        assert self.recipe_repo.get_by_id(recipe_id) is None


class TestSQLiteShoppingListRepository:
    """Test SQLiteShoppingListRepository."""

    def setup_method(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        self.db = Database(self.temp_db.name)
        self.shopping_repo = SQLiteShoppingListRepository(self.db)

    def teardown_method(self):
        """Clean up test database."""
        self.db.close()
        os.unlink(self.temp_db.name)

    def test_create_and_get_shopping_list(self):
        """Test creating and retrieving a shopping list."""
        # Create test shopping list
        items = [
            ShoppingItem(name="milk", quantity="1", unit="liter"),
            ShoppingItem(name="bread", quantity="2", unit="loaves"),
        ]

        shopping_list = ShoppingList(items=items)
        thread_id = "test_thread_123"

        # Save shopping list
        saved_list = self.shopping_repo.save(shopping_list, thread_id)

        # Verify list was saved
        assert saved_list.id is not None
        assert len(saved_list.items) == 2

        # Retrieve shopping list
        retrieved_list = self.shopping_repo.get_by_thread_id(thread_id)
        assert retrieved_list is not None
        assert len(retrieved_list.items) == 2
        assert retrieved_list.items[0].name == "milk"

    def test_add_items_to_existing_list(self):
        """Test adding items to an existing shopping list."""
        thread_id = "test_thread_456"

        # Create initial list
        initial_items = [ShoppingItem(name="milk", quantity="1", unit="liter")]
        initial_list = ShoppingList(items=initial_items)
        self.shopping_repo.save(initial_list, thread_id)

        # Add more items
        new_items = [
            ShoppingItem(name="bread", quantity="2", unit="loaves"),
            ShoppingItem(name="eggs", quantity="6", unit="pieces"),
        ]
        self.shopping_repo.add_items(thread_id, new_items)

        # Verify all items are present
        final_list = self.shopping_repo.get_by_thread_id(thread_id)
        assert len(final_list.items) == 3
        assert any(item.name == "milk" for item in final_list.items)
        assert any(item.name == "bread" for item in final_list.items)
        assert any(item.name == "eggs" for item in final_list.items)

    def test_clear_shopping_list(self):
        """Test clearing a shopping list."""
        thread_id = "test_thread_789"

        # Create list with items
        items = [
            ShoppingItem(name="milk", quantity="1", unit="liter"),
            ShoppingItem(name="bread", quantity="2", unit="loaves"),
        ]
        shopping_list = ShoppingList(items=items)
        self.shopping_repo.save(shopping_list, thread_id)

        # Verify list has items
        assert len(self.shopping_repo.get_by_thread_id(thread_id).items) == 2

        # Clear list
        self.shopping_repo.clear(thread_id)

        # Verify list is empty
        cleared_list = self.shopping_repo.get_by_thread_id(thread_id)
        assert len(cleared_list.items) == 0

    def test_delete_shopping_list(self):
        """Test deleting a shopping list."""
        thread_id = "test_thread_delete"

        # Create and save list
        items = [ShoppingItem(name="milk", quantity="1", unit="liter")]
        shopping_list = ShoppingList(items=items)
        saved_list = self.shopping_repo.save(shopping_list, thread_id)
        list_id = saved_list.id

        # Verify list exists
        assert self.shopping_repo.get_by_id(list_id) is not None

        # Delete list
        success = self.shopping_repo.delete(list_id)
        assert success is True

        # Verify list is deleted
        assert self.shopping_repo.get_by_id(list_id) is None
